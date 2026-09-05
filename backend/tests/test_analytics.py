"""Analytics unit tests: returns, z-score, volume, baseline, classification."""

from __future__ import annotations

import pytest

from app.analytics import anomaly, returns, volume
from app.analytics.baseline import Baseline, compute_baseline
from app.analytics.change_detector import ChangeEvidence, classify_change
from app.analytics.significance import (
    REASON_PRICE_MOVE,
    REASON_UNUSUAL_RETURN,
    REASON_UNUSUAL_VOLUME,
    Classification,
    classify_volume,
)
from app.analytics.thresholds import SignificanceThresholds
from app.domain.entities import MarketSnapshot
from app.domain.enums import BaselineStatus, DataStatus, SignificanceTier as Tier
from tests.fakes import build_instrument

THRESHOLDS = SignificanceThresholds.defaults()


class TestReturns:
    def test_percent_return_3820_to_3945(self):
        assert returns.percent_return(3820.0, 3945.0) == pytest.approx(3.27225, abs=1e-3)

    def test_percent_return_rejects_non_positive_previous(self):
        with pytest.raises(ValueError):
            returns.percent_return(0, 10)


class TestZScore:
    def test_z_2_77_for_return_over_std(self):
        # (3.27225 - 0.0) / 1.1813 ~= 2.77
        assert anomaly.z_score(3.27225, 0.0, 1.1813) == pytest.approx(2.77, abs=1e-2)

    def test_z_none_when_std_zero(self):
        assert anomaly.z_score(1.0, 0.0, 0.0) is None

    def test_z_none_when_input_missing(self):
        assert anomaly.z_score(None, 0.0, 1.0) is None


class TestVolume:
    def test_volume_ratio_2_4(self):
        assert volume.volume_ratio(240_000.0, 100_000.0) == pytest.approx(2.4)

    def test_volume_ratio_none_on_zero_avg(self):
        assert volume.volume_ratio(1000.0, 0.0) is None


class TestBaseline:
    def test_insufficient_returns_is_unavailable(self):
        b = compute_baseline([1.0, 2.0, 3.0], min_returns=20, limited_returns=5)
        assert b.status is BaselineStatus.UNAVAILABLE
        assert b.mean is None and b.std is None

    def test_limited_returns_has_stats(self):
        b = compute_baseline([1.0] * 6, min_returns=20, limited_returns=5)
        assert b.status is BaselineStatus.LIMITED
        assert b.mean == pytest.approx(1.0)

    def test_sufficient_returns(self):
        b = compute_baseline(list(range(1, 26)), min_returns=20, limited_returns=5)
        assert b.status is BaselineStatus.SUFFICIENT
        assert b.sample_size == 25


def make_signal(previous_price, current_price, current_volume, baseline, corporate=(), historical_volumes=(), reference_price=None):
    from datetime import datetime, timezone

    instrument = build_instrument()
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t1 = datetime(2024, 1, 2, tzinfo=timezone.utc)

    def snap(price, t, iid):
        return MarketSnapshot(
            instrument_id=iid,
            observed_at=t,
            received_at=t,
            price=price,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=current_volume,
            currency="INR",
            source="fake",
            data_status=DataStatus.LIVE,
            id=iid,
        )

    previous = snap(previous_price, t0, 1)
    current = MarketSnapshot(**{
        **snap(current_price, t1, 2).__dict__,
        "volume": current_volume,
    })
    evidence = ChangeEvidence(
        previous=previous,
        current=current,
        historical_returns=[],
        historical_volumes=list(historical_volumes),
        corporate_events=list(corporate),
        reference_price=reference_price,
    )
    return classify_change(
        evidence,
        thresholds=THRESHOLDS,
        baseline_calculator=lambda _rets: baseline,
    )


class TestChangeDetector:
    def test_session_open_reference_wins_over_previous_poll(self):
        signal = make_signal(
            previous_price=101.0,  # a five-minute polling observation
            current_price=103.0,
            reference_price=100.0,  # current session open
            current_volume=1_000.0,
            baseline=Baseline(
                status=BaselineStatus.SUFFICIENT, mean=0.0, std=2.0, sample_size=20
            ),
        )
        # Daily historical returns are compared to the same session interval,
        # not to an arbitrary polling cadence.
        assert signal.previous_price == 100.0
        assert signal.return_pct == pytest.approx(3.0)

    def test_3820_3945_with_z_2_77_and_volume_2_4_classified_significant(self):
        # return 3.27%, z = 2.77 (SIGNIFICANT), volume ratio 2.4 (NOTABLE).
        signal = make_signal(
            previous_price=3820.0,
            current_price=3945.0,
            current_volume=24_000.0,  # avg historical 10_000 -> ratio 2.4
            baseline=Baseline(
                status=BaselineStatus.SUFFICIENT,
                mean=0.0,
                std=1.1813,  # -> z ~ 2.77
                sample_size=20,
            ),
            historical_volumes=[10_000.0, 10_000.0],
        )
        assert signal.return_pct == pytest.approx(3.27225, abs=1e-3)
        assert signal.z_score == pytest.approx(2.77, abs=1e-2)
        assert signal.volume_ratio == pytest.approx(2.4, abs=1e-3)
        assert signal.significance is Tier.SIGNIFICANT
        assert REASON_UNUSUAL_RETURN in signal.reason_codes
        # Volume was notable and thus included among the reasons.
        assert REASON_UNUSUAL_VOLUME in signal.reason_codes

    def test_critical_when_return_above_critical_threshold(self):
        signal = make_signal(
            previous_price=100.0,
            current_price=112.0,  # +12% >= critical 7%
            current_volume=1000.0,
            baseline=Baseline(
                status=BaselineStatus.SUFFICIENT, mean=0.0, std=2.0, sample_size=20
            ),
        )
        assert signal.significance is Tier.CRITICAL
        assert REASON_PRICE_MOVE in signal.reason_codes

    def test_insufficient_baseline_keeps_z_none_not_fabricated(self):
        signal = make_signal(
            previous_price=100.0,
            current_price=103.0,  # +3% but no baseline
            current_volume=1000.0,
            baseline=Baseline(status=BaselineStatus.UNAVAILABLE, mean=None, std=None, sample_size=0),
        )
        assert signal.z_score is None
        assert signal.baseline_mean is None
        assert signal.baseline_std is None

    def test_flat_returns_and_normal_volume_is_normal(self):
        signal = make_signal(
            previous_price=100.0,
            current_price=100.5,  # +0.5%
            current_volume=1000.0,
            baseline=Baseline(status=BaselineStatus.SUFFICIENT, mean=0.0, std=2.0, sample_size=20),
        )
        assert signal.significance is Tier.NORMAL

    def test_volume_alone_reaches_significant_but_not_critical(self):
        cls = classify_volume(
            volume_ratio=4.0, thresholds=THRESHOLDS
        )
        assert cls.tier is Tier.SIGNIFICANT
        assert cls.tier is not Tier.CRITICAL
        assert REASON_UNUSUAL_VOLUME in cls.reason_codes

    def test_corporate_event_merger_is_critical_visibility(self):
        from app.domain.entities import CorporateEvent
        from app.domain.enums import CorporateEventStatus, CorporateEventType
        from datetime import datetime, timezone

        event = CorporateEvent(
            instrument_id="TCS",
            event_type=CorporateEventType.MERGER_ACQUISITION,
            event_time=datetime.now(timezone.utc),
            description="Acquisition announced",
            source="fake",
            status=CorporateEventStatus.CONFIRMED,
        )
        signal = make_signal(
            previous_price=100.0,
            current_price=100.1,
            current_volume=1000.0,
            baseline=Baseline(
                status=BaselineStatus.SUFFICIENT, mean=0.0, std=2.0, sample_size=20
            ),
            corporate=[event],
        )
        assert signal.significance is Tier.CRITICAL
        assert "MERGER_ACQUISITION_EVENT" in signal.reason_codes

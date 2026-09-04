"""Encapsulated, configurable significance thresholds.

Keeps all magic numbers out of the classifier and lets operators tune them via
environment configuration without changing code.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignificanceThresholds:
    return_notable: float
    return_significant: float
    return_critical: float
    z_notable: float
    z_significant: float
    z_critical: float
    volume_notable: float
    volume_significant: float

    @classmethod
    def from_settings(cls, s) -> "SignificanceThresholds":
        return cls(
            return_notable=s.PRICE_NOTABLE_THRESHOLD,
            return_significant=s.PRICE_SIGNIFICANT_THRESHOLD,
            return_critical=s.PRICE_CRITICAL_THRESHOLD,
            z_notable=s.PRICE_NOTABLE_Z,
            z_significant=s.PRICE_SIGNIFICANT_Z,
            z_critical=s.PRICE_CRITICAL_Z,
            volume_notable=s.VOLUME_NOTABLE_RATIO,
            volume_significant=s.VOLUME_SIGNIFICANT_RATIO,
        )

    @classmethod
    def defaults(cls) -> "SignificanceThresholds":
        return cls(
            return_notable=2.0,
            return_significant=4.0,
            return_critical=7.0,
            z_notable=1.5,
            z_significant=2.0,
            z_critical=3.0,
            volume_notable=2.0,
            volume_significant=3.0,
        )

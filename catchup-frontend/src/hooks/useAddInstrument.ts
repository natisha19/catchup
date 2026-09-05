import { useCallback, useState } from "react";
import type { WatchlistApi } from "../api/watchlistApi";
import type { Instrument } from "../domain/types";
import type { AddFailed } from "../components/search/SearchBox";

/**
 * Shared add-to-watchlist flow (pending / succeeded / failed-with-retry state).
 * Used by the Explore hero search and the AddInstrumentModal so both surfaces
 * behave identically against the same WatchlistApi.
 */
export function useAddInstrument(api: WatchlistApi, onAdded?: () => void) {
  const [addingId, setAddingId] = useState<string | null>(null);
  const [added, setAdded] = useState<string[]>([]);
  const [failed, setFailed] = useState<AddFailed | null>(null);

  const addByType = useCallback(
    async (kind: "id" | "symbol", ref: { instrumentId: string; symbol: string }) => {
      const key = kind === "id" ? ref.instrumentId : ref.symbol;
      setAddingId(key);
      setFailed(null);
      try {
        await api.addInstrument(kind === "id" ? ref.instrumentId : "", ref.symbol);
        setAdded((a) => [...a, key]);
        onAdded?.();
      } catch {
        setFailed(kind === "id" ? { kind, instrument: { instrumentId: ref.instrumentId, symbol: ref.symbol } as Instrument } : { kind, symbol: ref.symbol });
      } finally {
        setAddingId((a) => (a === key ? null : a));
      }
    },
    [api, onAdded],
  );

  const addInstrument = useCallback(
    (inst: Instrument) => void addByType("id", { instrumentId: inst.instrumentId, symbol: inst.symbol }),
    [addByType],
  );

  const addBySymbol = useCallback(
    (symbol: string) => void addByType("symbol", { instrumentId: "", symbol }),
    [addByType],
  );

  const retry = useCallback(() => {
    if (!failed) return;
    if (failed.kind === "id") {
      void addByType("id", { instrumentId: failed.instrument.instrumentId, symbol: failed.instrument.symbol });
    } else {
      void addByType("symbol", { instrumentId: "", symbol: failed.symbol });
    }
  }, [failed, addByType]);

  const reset = useCallback(() => {
    setAddingId(null);
    setAdded([]);
    setFailed(null);
  }, []);

  return { addingId, added, failed, addInstrument, addBySymbol, retry, reset };
}
import type { MarketStatus } from "./types";

let cachedMarketStatus: MarketStatus | null | undefined;

export function rememberMarketStatus(status?: MarketStatus | null): void {
  if (status) cachedMarketStatus = status;
}

export function getMarketStatus(): MarketStatus | undefined {
  return cachedMarketStatus ?? undefined;
}
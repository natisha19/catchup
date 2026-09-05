// Barrel for API interface contracts.
// Implementation classes live in their own files; the app depends on
// these interfaces only (dependency inversion).

export type { CatchupApi } from "./catchupApi";
export type { ExploreApi } from "./exploreApi";
export type { WatchlistApi, InstrumentApi, InstrumentSearchResult } from "./watchlistApi";
export { apiConfig, ApiError, httpJson } from "./clients";

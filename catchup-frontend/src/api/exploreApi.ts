import type { Explore } from "../domain/types";

export interface ExploreApi {
  /** Discovery feed. `sector` (optional) scopes the backend query, not a client-side filter. */
  getExplore(limit?: number, sector?: string): Promise<Explore>;
}
import type { ExploreApi } from "../api/exploreApi";
import type { Explore, ExploreItem } from "../domain/types";
import * as data from "./mockData";

export class MockExploreApi implements ExploreApi {
  async getExplore(_limit?: number, sector?: string): Promise<Explore> {
    if (!sector) return data.delay(data.explore);

    // Mirror the backend contract: the sector scopes the query. Sections whose
    // instruments have no data in that sector come back empty, while the
    // sectors breadcrumbs still list the full discovery universe.
    const scope = (rows: ExploreItem[]) =>
      rows.filter((row) => row.instrument.sector === sector);
    return data.delay({
      movers: scope(data.explore.movers),
      dippers: scope(data.explore.dippers),
      unusual: scope(data.explore.unusual),
      sectors: data.explore.sectors,
    });
  }
}

export const mockExploreApi = new MockExploreApi();
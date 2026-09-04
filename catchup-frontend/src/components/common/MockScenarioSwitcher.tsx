// src/components/common/MockScenarioSwitcher.tsx
import { setMockScenario, type MockScenario } from "../../mocks/mockCatchupApi";

const scenarios: MockScenario[] = ["default", "firstVisit", "marketClosed", "noChanges", "apiDown"];

/** Dev/demo only. Never imported in production code paths. */
export function MockScenarioSwitcher() {
  if (import.meta.env.PROD) return null;
  return (
    <select
      aria-label="Demo scenario"
      defaultValue="default"
      onChange={(e) => { setMockScenario(e.target.value as MockScenario); location.reload(); }}
      className="fixed bottom-2 right-2 z-50 rounded border border-line bg-white px-2 py-1 text-xs"
    >
      {scenarios.map((s) => <option key={s} value={s}>{s}</option>)}
    </select>
  );
}

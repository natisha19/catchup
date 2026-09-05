// src/components/common/MockScenarioSwitcher.tsx
import { setMockScenario, type MockScenario } from "../../mocks/mockCatchupApi";
import { apiConfig } from "../../api/clients";

const scenarios: MockScenario[] = ["default", "firstVisit", "marketClosed", "noChanges", "apiDown"];

/**
 * Dev-only: lets you preview feed scenarios in local mock mode. Never ships in
 * a production build, and never renders in http (real data) mode either —
 * it only exists to exercise the mock API layer during development.
 */
export function MockScenarioSwitcher() {
  if (import.meta.env.PROD) return null;
  if (apiConfig.mode === "http") return null;
  return (
    <select
      aria-label="Demo scenario"
      defaultValue="default"
      onChange={(e) => { setMockScenario(e.target.value as MockScenario); location.reload(); }}
      className="fixed bottom-2 right-2 z-50 rounded border border-line bg-card px-2 py-1 text-xs text-ink"
    >
      {scenarios.map((s) => <option key={s} value={s}>{s}</option>)}
    </select>
  );
}

import { RouterProvider } from "react-router-dom";
import { ApiProvider } from "./providers/ApiProvider";
import { routes } from "./routes";
import { MockScenarioSwitcher } from "../components/common/MockScenarioSwitcher";

export default function App() {
  return (
    <ApiProvider>
      <RouterProvider router={routes} />
      <MockScenarioSwitcher />
    </ApiProvider>
  );
}

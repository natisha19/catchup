import { createBrowserRouter } from "react-router-dom";
import { CatchupPage } from "../pages/CatchupPage";
import { StockDetailPage } from "../pages/StockDetailPage";
import { WatchlistPage } from "../pages/WatchlistPage";
import { AppShell } from "../components/layout/AppShell";

export const routes = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <CatchupPage /> },
      { path: "/stock/:instrumentId", element: <StockDetailPage /> },
      { path: "/watchlist", element: <WatchlistPage /> },
    ],
  },
]);

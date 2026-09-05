import { createBrowserRouter } from "react-router-dom";
import { ExplorePage } from "../pages/ExplorePage";
import { StockDetailPage } from "../pages/StockDetailPage";
import { WatchlistPage } from "../pages/WatchlistPage";
import { AppShell } from "../components/layout/AppShell";

export const routes = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <ExplorePage /> },
      { path: "/stock/:instrumentId", element: <StockDetailPage /> },
      { path: "/watchlist", element: <WatchlistPage /> },
    ],
  },
]);

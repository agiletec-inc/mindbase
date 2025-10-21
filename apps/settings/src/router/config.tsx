import type { RouteObject } from "react-router-dom";
import NotFound from "../pages/NotFound";
import Home from "../pages/home/page";
import SettingsPage from "../pages/settings/page";

const routes: RouteObject[] = [
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/settings",
    element: <SettingsPage />,
  },
  {
    path: "*",
    element: <NotFound />,
  },
];

export default routes;
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useIsAuthenticated } from "@/stores/auth";

export function ProtectedRoute() {
  const isAuth = useIsAuthenticated();
  const location = useLocation();
  if (!isAuth) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}

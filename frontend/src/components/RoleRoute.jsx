import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

function RoleRoute({ allowedRoles }) {
  const { user } = useAuth();

  if (!user || !allowedRoles.includes(user.role)) {
    return <Navigate to="/inicio" replace />;
  }

  return <Outlet />;
}

export default RoleRoute;

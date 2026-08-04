import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

function PasswordChangeRoute() {
  const { user } = useAuth();

  if (user?.must_change_password) {
    return <Navigate to="/cambiar-contrasena" replace />;
  }

  return <Outlet />;
}

export default PasswordChangeRoute;

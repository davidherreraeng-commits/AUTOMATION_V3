import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import PasswordChangeRoute from "./components/PasswordChangeRoute";
import PrivateRoute from "./components/PrivateRoute";
import RoleRoute from "./components/RoleRoute";
import ChangePassword from "./pages/ChangePassword";
import Configuracion from "./pages/Configuracion";
import Errores from "./pages/Errores";
import Historial from "./pages/Historial";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Usuarios from "./pages/Usuarios";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<PrivateRoute />}>
        <Route path="/cambiar-contrasena" element={<ChangePassword />} />

        <Route element={<PasswordChangeRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/inicio" element={<Home />} />
            <Route path="/historial" element={<Historial />} />
            <Route path="/errores" element={<Errores />} />

            <Route element={<RoleRoute allowedRoles={["SUPERUSER"]} />}>
              <Route path="/usuarios" element={<Usuarios />} />
              <Route path="/configuracion" element={<Configuracion />} />
              <Route
                path="/crear-usuario"
                element={<Navigate to="/usuarios" replace />}
              />
            </Route>
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/inicio" replace />} />
      <Route path="*" element={<Navigate to="/inicio" replace />} />
    </Routes>
  );
}

export default App;

import LogoutIcon from "@mui/icons-material/Logout";
import {
  AppBar,
  Box,
  Button,
  Toolbar,
  Typography,
} from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

function Navbar() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <AppBar
      position="sticky"
      elevation={1}
      sx={{ backgroundColor: "#005026" }}
    >
      <Toolbar sx={{ gap: 2 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" fontWeight={700}>
            Sistema de Automatización RPA
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.9 }}>
            {user?.dependency ?? "Sin dependencia asignada"}
          </Typography>
        </Box>

        <Box sx={{ textAlign: "right", display: { xs: "none", sm: "block" } }}>
          <Typography variant="body2" fontWeight={600}>
            {user?.username}
          </Typography>
          <Typography variant="caption">
            {user?.role === "SUPERUSER" ? "Superusuario" : "Operador"}
          </Typography>
        </Box>

        <Button
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
        >
          Salir
        </Button>
      </Toolbar>
    </AppBar>
  );
}

export default Navbar;

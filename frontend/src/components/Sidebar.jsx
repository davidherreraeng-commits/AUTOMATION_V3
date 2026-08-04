import HomeIcon from "@mui/icons-material/Home";
import HistoryIcon from "@mui/icons-material/History";
import ManageAccountsIcon from "@mui/icons-material/ManageAccounts";
import ReportProblemIcon from "@mui/icons-material/ReportProblem";
import SettingsIcon from "@mui/icons-material/Settings";
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
} from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import poliLogo from "../assets/logo-poli.png";

const drawerWidth = 240;

function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const options = [
    { text: "Inicio", path: "/inicio", icon: <HomeIcon /> },
    { text: "Historial", path: "/historial", icon: <HistoryIcon /> },
    { text: "Errores", path: "/errores", icon: <ReportProblemIcon /> },
  ];

  if (user?.role === "SUPERUSER") {
    options.splice(
      1,
      0,
      {
        text: "Usuarios",
        path: "/usuarios",
        icon: <ManageAccountsIcon />,
      },
      {
        text: "Configuración",
        path: "/configuracion",
        icon: <SettingsIcon />,
      },
    );
  }

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        display: { xs: "none", md: "block" },
        [`& .MuiDrawer-paper`]: {
          width: drawerWidth,
          boxSizing: "border-box",
          backgroundColor: "#00441f",
          color: "white",
        },
      }}
    >
      <Box p={2} textAlign="center">
        <img
          src={poliLogo}
          alt="Politécnico Colombiano Jaime Isaza Cadavid"
          style={{ width: 100, marginBottom: 12 }}
        />
        <Box sx={{ fontSize: 13, opacity: 0.9 }}>
          {user?.dependency}
        </Box>
      </Box>

      <List>
        {options.map((option) => (
          <ListItem key={option.path} disablePadding>
            <ListItemButton
              onClick={() => navigate(option.path)}
              selected={location.pathname === option.path}
              sx={{
                "&.Mui-selected": { backgroundColor: "#005d2d" },
                "&:hover": { backgroundColor: "#006837" },
                color: "white",
              }}
            >
              <ListItemIcon sx={{ color: "white" }}>
                {option.icon}
              </ListItemIcon>
              <ListItemText primary={option.text} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Drawer>
  );
}

export default Sidebar;

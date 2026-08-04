import { Box } from "@mui/material";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

function AppLayout() {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh", backgroundColor: "#f5f7f6" }}>
      <Sidebar />

      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <Navbar />
        <Box
          component="main"
          sx={{
            p: { xs: 2, md: 3 },
            maxWidth: 1600,
            mx: "auto",
          }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}

export default AppLayout;

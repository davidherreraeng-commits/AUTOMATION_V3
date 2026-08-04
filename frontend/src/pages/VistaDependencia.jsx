import React from "react";
import { Button, Typography, Box, Stack, Paper } from "@mui/material";
import { useNavigate } from "react-router-dom";

function VistaDependencia() {
  const navigate = useNavigate();

  const seleccionarDependencia = (dep) => {
    localStorage.setItem("dependenciaSeleccionada", dep);
    navigate("/inicio");
  };

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      minHeight="100vh"
      bgcolor="#f4f4f8"
    >
      <Paper elevation={4} sx={{ p: 6, borderRadius: 4, textAlign: "center" }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Selecciona la dependencia
        </Typography>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={4}
          mt={4}
          justifyContent="center"
        >
          <Button
            variant="contained"
            size="large"
            sx={{
              backgroundColor: "#005026",
              "&:hover": { backgroundColor: "#00441f" },
              color: "#fff",
              fontWeight: "bold",
            }}
            onClick={() => seleccionarDependencia("Adquisiciones")}
          >
            ADQUISICIONES
          </Button>
          <Button
            variant="contained"
            size="large"
            sx={{
              backgroundColor: "#FFC600",
              "&:hover": { backgroundColor: "#e6b800" },
              color: "#000",
              fontWeight: "bold",
            }}
            onClick={() => seleccionarDependencia("Proyectos")}
          >
            PROYECTOS
          </Button>
        </Stack>
      </Paper>
    </Box>
  );
}

export default VistaDependencia;
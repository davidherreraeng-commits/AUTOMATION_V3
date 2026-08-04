import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Alert,
  Avatar,
  Box,
  Button,
  IconButton,
  InputAdornment,
  Paper,
  TextField,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import poliLogo from "../assets/logo-poli.png";

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, isAuthenticated, loading, login } = useAuth();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!loading && isAuthenticated) {
    return (
      <Navigate
        to={user?.must_change_password ? "/cambiar-contrasena" : "/inicio"}
        replace
      />
    );
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const authenticatedUser = await login({ username, password });
      const destination = authenticatedUser.must_change_password
        ? "/cambiar-contrasena"
        : location.state?.from ?? "/inicio";
      navigate(destination, { replace: true });
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No fue posible iniciar sesión. Verifique los datos e inténtelo nuevamente.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        p: 2,
        background:
          "linear-gradient(135deg, #e7f2eb 0%, #f7faf8 55%, #fff7d6 100%)",
      }}
    >
      <Paper
        component="section"
        elevation={7}
        sx={{
          width: "100%",
          maxWidth: 420,
          p: { xs: 3, sm: 5 },
          borderRadius: 4,
        }}
      >
        <Box sx={{ textAlign: "center", mb: 3 }}>
          <img
            src={poliLogo}
            alt="Politécnico Colombiano Jaime Isaza Cadavid"
            style={{ width: 96, marginBottom: 12 }}
          />
          <Avatar sx={{ mx: "auto", mb: 1.5, bgcolor: "#005026" }}>
            <LockOutlinedIcon />
          </Avatar>
          <Typography variant="h5" fontWeight={800}>
            Automatización de contratos
          </Typography>
          <Typography variant="body2" color="text.secondary" mt={0.75}>
            Ingrese con la cuenta asignada por la institución.
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} noValidate>
          <TextField
            label="Usuario"
            autoComplete="username"
            fullWidth
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={submitting}
            margin="normal"
          />

          <TextField
            label="Contraseña"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            fullWidth
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={submitting}
            margin="normal"
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label={
                        showPassword
                          ? "Ocultar contraseña"
                          : "Mostrar contraseña"
                      }
                      onClick={() => setShowPassword((value) => !value)}
                      edge="end"
                    >
                      {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />

          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            disabled={submitting || !username.trim() || !password}
            sx={{
              mt: 3,
              py: 1.25,
              backgroundColor: "#005026",
              fontWeight: 800,
              "&:hover": { backgroundColor: "#00441f" },
            }}
          >
            {submitting ? "Ingresando…" : "Ingresar"}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}

export default Login;

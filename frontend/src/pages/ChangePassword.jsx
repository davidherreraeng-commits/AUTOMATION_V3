import LockResetIcon from "@mui/icons-material/LockReset";
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
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";

function PasswordField({ label, value, onChange, autoComplete, disabled }) {
  const [visible, setVisible] = useState(false);

  return (
    <TextField
      fullWidth
      required
      label={label}
      type={visible ? "text" : "password"}
      value={value}
      onChange={onChange}
      autoComplete={autoComplete}
      disabled={disabled}
      margin="normal"
      inputProps={{ minLength: 8, maxLength: 128 }}
      slotProps={{
        input: {
          endAdornment: (
            <InputAdornment position="end">
              <IconButton
                aria-label={visible ? "Ocultar contraseña" : "Mostrar contraseña"}
                onClick={() => setVisible((current) => !current)}
                edge="end"
              >
                {visible ? <VisibilityOffIcon /> : <VisibilityIcon />}
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
    />
  );
}

function ChangePassword() {
  const navigate = useNavigate();
  const { user, changePassword, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (newPassword !== confirmation) {
      setError("La nueva contraseña y su confirmación no coinciden.");
      return;
    }

    setSubmitting(true);
    try {
      await changePassword({ currentPassword, newPassword });
      navigate("/inicio", { replace: true });
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "No fue posible cambiar la contraseña.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
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
        elevation={6}
        sx={{ width: "100%", maxWidth: 460, p: { xs: 3, sm: 5 }, borderRadius: 4 }}
      >
        <Box textAlign="center" mb={2}>
          <Avatar sx={{ mx: "auto", mb: 1.5, bgcolor: "#005026" }}>
            <LockResetIcon />
          </Avatar>
          <Typography variant="h5" fontWeight={800}>
            Cambiar contraseña
          </Typography>
          <Typography color="text.secondary" mt={1}>
            {user?.must_change_password
              ? "Debe definir una contraseña personal antes de continuar."
              : "Actualice la contraseña de su cuenta."}
          </Typography>
        </Box>

        {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

        <Box component="form" onSubmit={handleSubmit}>
          <PasswordField
            label="Contraseña actual"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            autoComplete="current-password"
            disabled={submitting}
          />
          <PasswordField
            label="Nueva contraseña"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            autoComplete="new-password"
            disabled={submitting}
          />
          <PasswordField
            label="Confirmar nueva contraseña"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            autoComplete="new-password"
            disabled={submitting}
          />

          <Button
            type="submit"
            fullWidth
            variant="contained"
            disabled={
              submitting ||
              !currentPassword ||
              newPassword.length < 8 ||
              !confirmation
            }
            sx={{ mt: 2, py: 1.2, bgcolor: "#005026", fontWeight: 800 }}
          >
            {submitting ? "Actualizando…" : "Guardar contraseña"}
          </Button>
          <Button
            fullWidth
            color="inherit"
            onClick={handleLogout}
            disabled={submitting}
            sx={{ mt: 1 }}
          >
            Cerrar sesión
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}

export default ChangePassword;

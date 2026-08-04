import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import VerifiedUserOutlinedIcon from "@mui/icons-material/VerifiedUserOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import api from "../api/axiosConfig";
import { useAuth } from "../auth/useAuth";

const emptyStatus = {
  dependency: "",
  configured: false,
  portal_username: null,
  updated_at: null,
  last_tested_at: null,
  last_test_success: null,
  last_test_code: null,
};

function formatDate(value) {
  if (!value) return "Sin registro";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getTestChip(status) {
  if (!status.configured) {
    return { label: "Sin configurar", color: "default" };
  }
  if (status.last_test_success === true) {
    return { label: "Credenciales verificadas", color: "success" };
  }
  if (status.last_test_success === false) {
    return { label: "Última prueba fallida", color: "error" };
  }
  return { label: "Pendientes de verificación", color: "warning" };
}

function Configuracion() {
  const { user } = useAuth();
  const [status, setStatus] = useState(emptyStatus);
  const [portalUsername, setPortalUsername] = useState("");
  const [portalPassword, setPortalPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    severity: "success",
    message: "",
  });

  const testChip = useMemo(() => getTestChip(status), [status]);

  const showMessage = (severity, message) => {
    setSnackbar({ open: true, severity, message });
  };

  const loadStatus = async () => {
    setLoading(true);
    try {
      const response = await api.get("/portal-credentials");
      setStatus(response.data);
      setPortalUsername(response.data.portal_username ?? "");
    } catch (error) {
      const detail = error.response?.data?.detail;
      showMessage(
        "error",
        typeof detail === "string"
          ? detail
          : "No fue posible consultar la configuración del portal.",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  const saveCredentials = async () => {
    setSaving(true);
    try {
      const response = await api.put("/portal-credentials", {
        portal_username: portalUsername.trim(),
        portal_password: portalPassword,
      });
      setStatus(response.data);
      setPortalUsername(response.data.portal_username ?? "");
      setPortalPassword("");
      showMessage(
        "success",
        "Credenciales cifradas y guardadas para la dependencia.",
      );
    } catch (error) {
      const detail = error.response?.data?.detail;
      showMessage(
        "error",
        typeof detail === "string"
          ? detail
          : "No fue posible guardar las credenciales.",
      );
    } finally {
      setSaving(false);
    }
  };

  const testCredentials = async () => {
    setTesting(true);
    try {
      const response = await api.post("/portal-credentials/test");
      setStatus(response.data.status);
      showMessage(
        response.data.success ? "success" : "error",
        response.data.message,
      );
    } catch (error) {
      const detail = error.response?.data?.detail;
      showMessage(
        "error",
        typeof detail === "string"
          ? detail
          : "No fue posible probar las credenciales guardadas.",
      );
    } finally {
      setTesting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 900 }}>
      <Paper elevation={2} sx={{ p: { xs: 3, md: 4 }, borderRadius: 3 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }} justifyContent="space-between">
          <Box>
            <Typography variant="h5" fontWeight="bold" color="#005026">
              Credenciales de Gestión Transparente
            </Typography>
            <Typography color="text.secondary" mt={0.5}>
              La automatización utilizará estas credenciales para la dependencia {user?.dependency}.
            </Typography>
          </Box>
          <Chip label={testChip.label} color={testChip.color} variant="outlined" />
        </Stack>

        <Alert severity="info" sx={{ mt: 3 }}>
          La contraseña se almacena cifrada y nunca se devuelve al navegador. Estas credenciales son distintas de la cuenta usada para entrar a la herramienta.
        </Alert>

        <Divider sx={{ my: 3 }} />

        {loading ? (
          <Stack alignItems="center" py={5}><CircularProgress /></Stack>
        ) : (
          <Stack spacing={3}>
            <TextField label="Dependencia" value={user?.dependency ?? ""} disabled fullWidth />
            <TextField
              label="Usuario de Gestión Transparente"
              value={portalUsername}
              onChange={(event) => setPortalUsername(event.target.value)}
              autoComplete="off"
              fullWidth
            />
            <TextField
              label="Contraseña de Gestión Transparente"
              type="password"
              autoComplete="new-password"
              value={portalPassword}
              onChange={(event) => setPortalPassword(event.target.value)}
              helperText={status.configured ? "Ingrese la contraseña nuevamente solo cuando vaya a actualizar las credenciales." : "La contraseña es obligatoria para guardar la configuración."}
              fullWidth
            />

            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <Button
                variant="contained"
                startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <SaveOutlinedIcon />}
                onClick={saveCredentials}
                disabled={saving || testing || !portalUsername.trim() || !portalPassword}
                sx={{ backgroundColor: "#005026", "&:hover": { backgroundColor: "#00441f" } }}
              >
                {saving ? "Guardando…" : "Guardar credenciales"}
              </Button>
              <Button
                variant="outlined"
                startIcon={testing ? <CircularProgress size={18} /> : <VerifiedUserOutlinedIcon />}
                onClick={testCredentials}
                disabled={saving || testing || !status.configured}
                color="success"
              >
                {testing ? "Comprobando…" : "Probar credenciales guardadas"}
              </Button>
            </Stack>

            <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, backgroundColor: "#fafafa" }}>
              <Stack direction="row" spacing={1} alignItems="center" mb={1.5}>
                <LockOutlinedIcon color="action" />
                <Typography fontWeight="bold">Estado de la configuración</Typography>
              </Stack>
              <Typography variant="body2">Usuario configurado: <strong>{status.portal_username ?? "No configurado"}</strong></Typography>
              <Typography variant="body2">Última actualización: <strong>{formatDate(status.updated_at)}</strong></Typography>
              <Typography variant="body2">Última comprobación: <strong>{formatDate(status.last_tested_at)}</strong></Typography>
            </Paper>
          </Stack>
        )}
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((current) => ({ ...current, open: false }))}
      >
        <Alert severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Configuracion;

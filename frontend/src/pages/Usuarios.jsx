import BlockIcon from "@mui/icons-material/Block";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import LockResetIcon from "@mui/icons-material/LockReset";
import PersonAddIcon from "@mui/icons-material/PersonAdd";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import api from "../api/axiosConfig";
import { useAuth } from "../auth/useAuth";

const initialForm = {
  username: "",
  temporaryPassword: "",
  confirmPassword: "",
  role: "OPERATOR",
};

function formatDate(value) {
  if (!value) return "Sin registro";
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function roleLabel(role) {
  return role === "SUPERUSER" ? "Superusuario" : "Operador";
}

function getErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  return fallback;
}

function Usuarios() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(initialForm);
  const [notice, setNotice] = useState(null);
  const [resetTarget, setResetTarget] = useState(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetConfirmation, setResetConfirmation] = useState("");
  const [resetting, setResetting] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/users");
      setUsers(response.data.items ?? []);
    } catch (error) {
      setNotice({
        severity: "error",
        text: getErrorMessage(error, "No fue posible consultar los usuarios."),
      });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const activeCount = useMemo(
    () => users.filter((item) => item.is_active).length,
    [users],
  );

  const updateForm = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleCreate = async (event) => {
    event.preventDefault();

    if (form.temporaryPassword !== form.confirmPassword) {
      setNotice({
        severity: "error",
        text: "La contraseña temporal y su confirmación no coinciden.",
      });
      return;
    }

    setSubmitting(true);
    try {
      const response = await api.post("/users", {
        username: form.username,
        temporary_password: form.temporaryPassword,
        role: form.role,
      });
      setUsers((current) =>
        [...current, response.data].sort((a, b) =>
          a.username.localeCompare(b.username, "es", { sensitivity: "base" }),
        ),
      );
      setForm(initialForm);
      setNotice({
        severity: "success",
        text: "Usuario creado. Deberá cambiar la contraseña temporal al ingresar.",
      });
    } catch (error) {
      setNotice({
        severity: "error",
        text: getErrorMessage(error, "No fue posible crear el usuario."),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (target) => {
    const nextState = !target.is_active;
    try {
      const response = await api.patch(`/users/${target.id}/status`, {
        is_active: nextState,
      });
      setUsers((current) =>
        current.map((item) => (item.id === target.id ? response.data : item)),
      );
      setNotice({
        severity: "success",
        text: nextState
          ? `El usuario ${target.username} fue activado.`
          : `El usuario ${target.username} fue desactivado.`,
      });
    } catch (error) {
      setNotice({
        severity: "error",
        text: getErrorMessage(error, "No fue posible cambiar el estado del usuario."),
      });
    }
  };

  const openResetDialog = (target) => {
    setResetTarget(target);
    setResetPassword("");
    setResetConfirmation("");
  };

  const closeResetDialog = () => {
    if (!resetting) {
      setResetTarget(null);
      setResetPassword("");
      setResetConfirmation("");
    }
  };

  const handleResetPassword = async () => {
    if (resetPassword !== resetConfirmation) {
      setNotice({
        severity: "error",
        text: "La contraseña temporal y su confirmación no coinciden.",
      });
      return;
    }

    setResetting(true);
    try {
      const response = await api.post(
        `/users/${resetTarget.id}/reset-password`,
        { temporary_password: resetPassword },
      );
      setUsers((current) =>
        current.map((item) =>
          item.id === resetTarget.id ? response.data : item,
        ),
      );
      setNotice({
        severity: "success",
        text: `Contraseña temporal restablecida para ${resetTarget.username}.`,
      });
      closeResetDialog();
      setResetTarget(null);
    } catch (error) {
      setNotice({
        severity: "error",
        text: getErrorMessage(error, "No fue posible restablecer la contraseña."),
      });
    } finally {
      setResetting(false);
    }
  };

  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        gap={2}
        mb={3}
      >
        <Box>
          <Typography variant="h4" fontWeight={800} color="#00441f">
            Gestión de usuarios
          </Typography>
          <Typography color="text.secondary">
            Administre las cuentas autorizadas para {currentUser?.dependency}.
          </Typography>
        </Box>
        <Button
          startIcon={<RefreshIcon />}
          onClick={loadUsers}
          disabled={loading}
          variant="outlined"
        >
          Actualizar
        </Button>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "360px minmax(0, 1fr)" },
          gap: 3,
          alignItems: "start",
        }}
      >
        <Paper elevation={2} sx={{ p: 3, borderRadius: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center" mb={1}>
            <PersonAddIcon color="success" />
            <Typography variant="h6" fontWeight={800}>
              Crear usuario
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" mb={2}>
            La dependencia se asigna automáticamente según su sesión.
          </Typography>

          <Box component="form" onSubmit={handleCreate}>
            <TextField
              fullWidth
              required
              label="Usuario"
              value={form.username}
              onChange={updateForm("username")}
              margin="normal"
              helperText="Letras, números, punto, guion o guion bajo."
              inputProps={{ minLength: 3, maxLength: 80 }}
              disabled={submitting}
            />
            <TextField
              fullWidth
              label="Dependencia"
              value={currentUser?.dependency ?? ""}
              margin="normal"
              disabled
            />
            <TextField
              select
              fullWidth
              label="Rol"
              value={form.role}
              onChange={updateForm("role")}
              margin="normal"
              disabled={submitting}
            >
              <MenuItem value="OPERATOR">Operador</MenuItem>
              <MenuItem value="SUPERUSER">Superusuario</MenuItem>
            </TextField>
            <TextField
              fullWidth
              required
              label="Contraseña temporal"
              type="password"
              autoComplete="new-password"
              value={form.temporaryPassword}
              onChange={updateForm("temporaryPassword")}
              margin="normal"
              inputProps={{ minLength: 8, maxLength: 128 }}
              disabled={submitting}
            />
            <TextField
              fullWidth
              required
              label="Confirmar contraseña"
              type="password"
              autoComplete="new-password"
              value={form.confirmPassword}
              onChange={updateForm("confirmPassword")}
              margin="normal"
              inputProps={{ minLength: 8, maxLength: 128 }}
              disabled={submitting}
            />
            <Alert severity="info" sx={{ mt: 2 }}>
              El usuario deberá definir una contraseña personal en su primer ingreso.
            </Alert>
            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={
                submitting ||
                form.username.trim().length < 3 ||
                form.temporaryPassword.length < 8 ||
                !form.confirmPassword
              }
              sx={{ mt: 2.5, py: 1.1, bgcolor: "#005026", fontWeight: 800 }}
            >
              {submitting ? "Creando…" : "Crear usuario"}
            </Button>
          </Box>
        </Paper>

        <Paper elevation={2} sx={{ borderRadius: 3, overflow: "hidden" }}>
          <Box p={2.5}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              gap={1}
            >
              <Box>
                <Typography variant="h6" fontWeight={800}>
                  Usuarios de la dependencia
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {users.length} registrados · {activeCount} activos
                </Typography>
              </Box>
              <Chip label={currentUser?.dependency ?? ""} color="success" variant="outlined" />
            </Stack>
          </Box>
          <Divider />

          {loading ? (
            <Box sx={{ minHeight: 260, display: "grid", placeItems: "center" }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table size="small" aria-label="Usuarios de la dependencia">
                <TableHead>
                  <TableRow sx={{ bgcolor: "#f4f7f5" }}>
                    <TableCell>Usuario</TableCell>
                    <TableCell>Rol</TableCell>
                    <TableCell>Estado</TableCell>
                    <TableCell>Último acceso</TableCell>
                    <TableCell align="right">Acciones</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((item) => {
                    const isCurrent = item.id === currentUser?.id;
                    return (
                      <TableRow key={item.id} hover>
                        <TableCell>
                          <Typography fontWeight={700}>{item.username}</Typography>
                          {isCurrent && (
                            <Typography variant="caption" color="text.secondary">
                              Cuenta actual
                            </Typography>
                          )}
                          {item.must_change_password && !isCurrent && (
                            <Typography variant="caption" display="block" color="warning.main">
                              Cambio de contraseña pendiente
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>{roleLabel(item.role)}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={item.is_active ? "Activo" : "Inactivo"}
                            color={item.is_active ? "success" : "default"}
                            variant={item.is_active ? "filled" : "outlined"}
                          />
                        </TableCell>
                        <TableCell>{formatDate(item.last_login_at)}</TableCell>
                        <TableCell align="right">
                          <Tooltip title="Restablecer contraseña">
                            <span>
                              <IconButton
                                size="small"
                                onClick={() => openResetDialog(item)}
                                disabled={isCurrent}
                                aria-label={`Restablecer contraseña de ${item.username}`}
                              >
                                <LockResetIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                          <Tooltip title={item.is_active ? "Desactivar" : "Activar"}>
                            <span>
                              <IconButton
                                size="small"
                                color={item.is_active ? "error" : "success"}
                                onClick={() => handleStatusChange(item)}
                                disabled={isCurrent && item.is_active}
                                aria-label={`${item.is_active ? "Desactivar" : "Activar"} ${item.username}`}
                              >
                                {item.is_active ? (
                                  <BlockIcon fontSize="small" />
                                ) : (
                                  <CheckCircleIcon fontSize="small" />
                                )}
                              </IconButton>
                            </span>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {users.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} align="center" sx={{ py: 6 }}>
                        No hay usuarios registrados para esta dependencia.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Paper>
      </Box>

      <Dialog open={Boolean(resetTarget)} onClose={closeResetDialog} fullWidth maxWidth="xs">
        <DialogTitle>Restablecer contraseña</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary" mb={1}>
            Defina una contraseña temporal para <strong>{resetTarget?.username}</strong>.
          </Typography>
          <TextField
            autoFocus
            fullWidth
            label="Contraseña temporal"
            type="password"
            value={resetPassword}
            onChange={(event) => setResetPassword(event.target.value)}
            margin="normal"
            inputProps={{ minLength: 8, maxLength: 128 }}
            disabled={resetting}
          />
          <TextField
            fullWidth
            label="Confirmar contraseña"
            type="password"
            value={resetConfirmation}
            onChange={(event) => setResetConfirmation(event.target.value)}
            margin="normal"
            inputProps={{ minLength: 8, maxLength: 128 }}
            disabled={resetting}
          />
          <Alert severity="warning" sx={{ mt: 1 }}>
            El usuario deberá cambiarla en su siguiente ingreso.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeResetDialog} disabled={resetting} color="inherit">
            Cancelar
          </Button>
          <Button
            onClick={handleResetPassword}
            variant="contained"
            disabled={
              resetting ||
              resetPassword.length < 8 ||
              !resetConfirmation
            }
            sx={{ bgcolor: "#005026" }}
          >
            {resetting ? "Guardando…" : "Restablecer"}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={5000}
        onClose={() => setNotice(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.text}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Box>
  );
}

export default Usuarios;

import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import ReplayIcon from "@mui/icons-material/Replay";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useMemo, useState } from "react";
import {
  applyContractExecutionToBatch,
  confirmationMatches,
  contractActionLabel,
  executeSelectedContract,
  extractExecutionApiError,
  getContractExecutionPreflight,
  getContractExecutionStatus,
} from "../api/batchContractExecution";

const STEP_LABELS = {
  PENDING: "Pendiente",
  INPUT_VALIDATED: "Entrada validada",
  ASSISTANT_OPENED: "Asistente abierto",
  HEADER_COMPLETED: "Encabezado completado",
  HEADER_VALIDATED: "Encabezado validado",
  GENERAL_DATA_COMPLETED: "Datos generales completados",
  CONTRACT_SAVED: "Contrato guardado",
  SUPERVISOR_LINKED: "Supervisor vinculado",
  AVAILABILITY_LINKED: "CDP vinculado",
  BUDGET_REGISTER_LINKED: "RP vinculado",
  ADDITIONAL_DATES_LINKED: "Fechas adicionales vinculadas",
  COMPLETED: "Completado",
};

const STATUS_META = {
  PENDING: { label: "Pendiente", color: "default" },
  PROCESSING: { label: "En proceso", color: "info" },
  COMPLETED: { label: "Completado", color: "success" },
  FAILED: { label: "Fallido", color: "error" },
  MANUAL_REVIEW: { label: "Revisión manual", color: "warning" },
};

function statusChip(status) {
  const meta = STATUS_META[status] ?? { label: status || "Sin estado", color: "default" };
  return <Chip size="small" label={meta.label} color={meta.color} variant="outlined" />;
}

function stepLabel(step) {
  return STEP_LABELS[step] ?? step ?? "—";
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

function CheckpointSummary({ data }) {
  if (!data) return null;

  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
      <Stack spacing={0.5}>
        <Typography variant="subtitle2">Checkpoint</Typography>
        <Typography variant="body2">
          Último paso confirmado: <strong>{stepLabel(data.last_completed_step)}</strong>
        </Typography>
        <Typography variant="body2">
          Paso actual: <strong>{stepLabel(data.current_step)}</strong>
        </Typography>
        {data.last_failed_step && (
          <Typography variant="body2" color="error.main">
            Último paso fallido: <strong>{stepLabel(data.last_failed_step)}</strong>
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary">
          Intentos: {data.attempt_count ?? 0} · Actualizado: {formatDateTime(data.checkpoint_updated_at ?? data.checked_at)}
        </Typography>
      </Stack>
    </Paper>
  );
}

function ResultDetails({ result }) {
  if (!result) return null;

  const severity = result.success
    ? "success"
    : result.requires_manual_review
      ? "warning"
      : "error";

  return (
    <Stack spacing={1.25} sx={{ mt: 1.5 }}>
      <Alert severity={severity} variant="outlined">
        <Stack spacing={0.25}>
          <Typography variant="body2" fontWeight="bold">
            {result.operational_message}
          </Typography>
          {result.error_code && (
            <Typography variant="caption">Código: {result.error_code}</Typography>
          )}
        </Stack>
      </Alert>
      <CheckpointSummary data={result} />
      {result.technical_detail && (
        <Accordion disableGutters elevation={0} variant="outlined">
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2">Detalle técnico</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography
              variant="caption"
              component="pre"
              sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", m: 0 }}
            >
              {result.technical_detail}
            </Typography>
          </AccordionDetails>
        </Accordion>
      )}
    </Stack>
  );
}

function BatchContractExecutionPanel({
  batch,
  user,
  onBatchChange,
  onBusyChange,
  onNotify,
}) {
  const [preflights, setPreflights] = useState({});
  const [results, setResults] = useState({});
  const [loadingItems, setLoadingItems] = useState(new Set());
  const [busyItemId, setBusyItemId] = useState(null);
  const [dialogItem, setDialogItem] = useState(null);
  const [confirmation, setConfirmation] = useState("");

  const contracts = batch?.contracts ?? [];
  const isSuperuser = user?.role === "SUPERUSER";
  const selectedPreflight = dialogItem ? preflights[dialogItem.item_id] : null;
  const selectedResult = dialogItem ? results[dialogItem.item_id] : null;

  const confirmationValid = useMemo(
    () =>
      Boolean(selectedPreflight?.can_execute) &&
      confirmationMatches(
        confirmation,
        selectedPreflight?.required_confirmation,
      ),
    [confirmation, selectedPreflight],
  );

  if (!batch || !isSuperuser) return null;

  const setItemLoading = (itemId, loading) => {
    setLoadingItems((current) => {
      const next = new Set(current);
      if (loading) next.add(itemId);
      else next.delete(itemId);
      return next;
    });
  };

  const publishResult = (result) => {
    setResults((current) => ({ ...current, [result.item_id]: result }));
    onBatchChange?.((current) => applyContractExecutionToBatch(current, result));
  };

  const loadPreflight = async (item, { openDialog = true } = {}) => {
    setItemLoading(item.item_id, true);
    try {
      const preflight = await getContractExecutionPreflight(
        batch.batch_id,
        item.item_id,
      );
      setPreflights((current) => ({ ...current, [item.item_id]: preflight }));
      if (openDialog) {
        setDialogItem(item);
        setConfirmation("");
      }
      onNotify?.(
        preflight.can_execute ? "success" : "warning",
        preflight.can_execute
          ? `El contrato ${item.contract_number} está listo para ${preflight.resumable ? "reanudarse" : "ejecutarse"}.`
          : `El contrato ${item.contract_number} tiene bloqueos de seguridad.`,
      );
      return preflight;
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible comprobar el contrato seleccionado.",
      );
      onNotify?.("error", problem.message);
      return null;
    } finally {
      setItemLoading(item.item_id, false);
    }
  };

  const loadStatus = async (item) => {
    setItemLoading(item.item_id, true);
    try {
      const result = await getContractExecutionStatus(batch.batch_id, item.item_id);
      publishResult(result);
      onNotify?.("info", `Checkpoint actualizado para ${item.contract_number}.`);
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible consultar el checkpoint del contrato.",
      );
      onNotify?.("error", problem.message);
    } finally {
      setItemLoading(item.item_id, false);
    }
  };

  const executeContract = async () => {
    if (!dialogItem || !selectedPreflight || !confirmationValid || busyItemId) return;

    setBusyItemId(dialogItem.item_id);
    onBusyChange?.(true);
    try {
      const result = await executeSelectedContract({
        batchId: batch.batch_id,
        itemId: dialogItem.item_id,
        confirmation,
        executionId: selectedPreflight.resumable
          ? selectedPreflight.execution_id
          : null,
      });
      publishResult(result);
      setDialogItem(null);
      setConfirmation("");
      onNotify?.(
        result.success ? "success" : result.requires_manual_review ? "warning" : "error",
        result.operational_message,
      );
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible ejecutar el contrato seleccionado.",
      );
      setResults((current) => ({
        ...current,
        [dialogItem.item_id]: {
          success: false,
          requires_manual_review: false,
          operational_message: problem.message,
          error_code: problem.code,
          technical_detail: problem.technicalDetail,
        },
      }));
      if (problem.requiredConfirmation) {
        setPreflights((current) => ({
          ...current,
          [dialogItem.item_id]: {
            ...current[dialogItem.item_id],
            required_confirmation: problem.requiredConfirmation,
          },
        }));
      }
      onNotify?.("error", problem.message);
    } finally {
      setBusyItemId(null);
      onBusyChange?.(false);
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 3 }}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h6" fontWeight="bold" color="#005026">
            Ejecución individual de contratos
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Cada contrato se comprueba, confirma y ejecuta por separado. La ejecución masiva permanece deshabilitada.
          </Typography>
        </Box>

        <Alert severity="warning" icon={<WarningAmberOutlinedIcon />}>
          La acción puede escribir datos reales en Gestión Transparente. Revise los bloqueos y escriba exactamente la frase solicitada.
        </Alert>

        <TableContainer>
          <Table size="small" aria-label="Ejecución individual de contratos">
            <TableHead>
              <TableRow>
                <TableCell><strong>Contrato</strong></TableCell>
                <TableCell><strong>Estado</strong></TableCell>
                <TableCell><strong>Checkpoint</strong></TableCell>
                <TableCell align="right"><strong>Acciones</strong></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {contracts.map((item) => {
                const preflight = preflights[item.item_id];
                const result = results[item.item_id];
                const loading = loadingItems.has(item.item_id);
                const itemBusy = busyItemId === item.item_id;
                const terminal = ["COMPLETED", "FAILED", "MANUAL_REVIEW"].includes(item.status);

                return (
                  <TableRow key={item.item_id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="bold">
                        {item.contract_number}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Fila {item.row_number} · {item.item_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack spacing={0.5} alignItems="flex-start">
                        {statusChip(result?.item_status ?? item.status)}
                        {(result?.operational_message || item.last_message) && (
                          <Typography variant="caption" color="text.secondary">
                            {result?.operational_message || item.last_message}
                          </Typography>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {stepLabel(result?.last_completed_step ?? preflight?.last_completed_step)}
                      </Typography>
                      {(result?.execution_status || preflight?.execution_status) && (
                        <Typography variant="caption" color="text.secondary">
                          Ejecución: {result?.execution_status || preflight?.execution_status}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={loading ? <CircularProgress size={16} /> : <RefreshIcon />}
                          onClick={() => loadStatus(item)}
                          disabled={loading || Boolean(busyItemId)}
                        >
                          Estado
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          startIcon={
                            itemBusy ? (
                              <CircularProgress size={16} color="inherit" />
                            ) : preflight?.resumable ? (
                              <ReplayIcon />
                            ) : (
                              <PlayArrowIcon />
                            )
                          }
                          onClick={() => loadPreflight(item)}
                          disabled={loading || Boolean(busyItemId) || terminal}
                          sx={{
                            backgroundColor: "#005026",
                            "&:hover": { backgroundColor: "#00441f" },
                          }}
                        >
                          {loading ? "Comprobando…" : contractActionLabel(preflight)}
                        </Button>
                      </Stack>
                      <ResultDetails result={result} />
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      </Stack>

      <Dialog
        open={Boolean(dialogItem)}
        onClose={busyItemId ? undefined : () => setDialogItem(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {selectedPreflight?.resumable ? "Reanudar contrato" : "Ejecutar contrato"}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Typography>
              Contrato: <strong>{dialogItem?.contract_number}</strong>
            </Typography>

            {selectedPreflight && (
              <>
                <Alert severity={selectedPreflight.can_execute ? "success" : "warning"}>
                  {selectedPreflight.can_execute
                    ? "El preflight permite continuar con la escritura controlada."
                    : "La ejecución está bloqueada. Corrija las condiciones antes de continuar."}
                </Alert>

                {selectedPreflight.issues.map((issue) => (
                  <Alert
                    key={issue.code}
                    severity={issue.blocking ? "error" : "info"}
                    variant="outlined"
                  >
                    <strong>{issue.code}:</strong> {issue.message}
                  </Alert>
                ))}

                <CheckpointSummary data={selectedPreflight} />

                {selectedPreflight.can_execute && (
                  <>
                    <Divider />
                    <Typography variant="body2">
                      Escriba exactamente:
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 1.5, backgroundColor: "#fafafa" }}>
                      <Typography component="code" fontWeight="bold">
                        {selectedPreflight.required_confirmation}
                      </Typography>
                    </Paper>
                    <TextField
                      autoFocus
                      fullWidth
                      label="Confirmación de escritura real"
                      value={confirmation}
                      onChange={(event) => setConfirmation(event.target.value)}
                      error={Boolean(confirmation) && !confirmationValid}
                      helperText={
                        confirmation && !confirmationValid
                          ? "La frase no coincide exactamente."
                          : "La comparación ignora mayúsculas y espacios repetidos."
                      }
                      disabled={Boolean(busyItemId)}
                    />
                  </>
                )}
              </>
            )}

            <ResultDetails result={selectedResult} />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogItem(null)} disabled={Boolean(busyItemId)}>
            Cerrar
          </Button>
          {selectedPreflight?.can_execute && (
            <Button
              variant="contained"
              onClick={executeContract}
              disabled={!confirmationValid || Boolean(busyItemId)}
              startIcon={
                busyItemId ? (
                  <CircularProgress size={18} color="inherit" />
                ) : selectedPreflight.resumable ? (
                  <ReplayIcon />
                ) : (
                  <PlayArrowIcon />
                )
              }
              sx={{
                backgroundColor: "#005026",
                "&:hover": { backgroundColor: "#00441f" },
              }}
            >
              {busyItemId
                ? "Ejecutando…"
                : selectedPreflight.resumable
                  ? "Reanudar"
                  : "Ejecutar contrato"}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Paper>
  );
}

export default BatchContractExecutionPanel;

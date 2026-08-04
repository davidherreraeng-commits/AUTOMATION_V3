import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import ReplayIcon from "@mui/icons-material/Replay";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import SecurityOutlinedIcon from "@mui/icons-material/SecurityOutlined";
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
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
import { useMemo, useState } from "react";
import {
  applyContractExecutionToBatch,
  confirmationMatches,
  contractActionLabel,
  executeSelectedContract,
  extractExecutionApiError,
  getContractExecutionEvidence,
  getContractExecutionPreflight,
  getContractExecutionStatus,
} from "../api/batchContractExecution";

const EXECUTION_MODES = {
  DRY_RUN: {
    label: "SIMULACIÓN",
    shortLabel: "Simular",
    color: "info",
    writesToPortal: false,
  },
  REAL: {
    label: "ESCRITURA REAL",
    shortLabel: "Ejecutar",
    color: "error",
    writesToPortal: true,
  },
};

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
  const meta = STATUS_META[status] ?? {
    label: status || "Sin estado",
    color: "default",
  };
  return (
    <Chip
      size="small"
      label={meta.label}
      color={meta.color}
      variant="outlined"
    />
  );
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

function ModeChip({ mode }) {
  const meta = EXECUTION_MODES[mode] ?? EXECUTION_MODES.DRY_RUN;
  return (
    <Chip
      size="small"
      label={meta.label}
      color={meta.color}
      icon={
        mode === "REAL" ? (
          <SecurityOutlinedIcon />
        ) : (
          <ScienceOutlinedIcon />
        )
      }
    />
  );
}

function CheckpointSummary({ data }) {
  if (!data) return null;

  return (
    <Paper variant="outlined" sx={{ p: 1.5, borderRadius: 2 }}>
      <Stack spacing={0.5}>
        <Typography variant="subtitle2">Checkpoint</Typography>
        <Typography variant="body2">
          Último paso confirmado:{" "}
          <strong>{stepLabel(data.last_completed_step)}</strong>
        </Typography>
        <Typography variant="body2">
          Paso actual: <strong>{stepLabel(data.current_step)}</strong>
        </Typography>
        {data.last_failed_step && (
          <Typography variant="body2" color="error.main">
            Último paso fallido:{" "}
            <strong>{stepLabel(data.last_failed_step)}</strong>
          </Typography>
        )}
        <Typography variant="caption" color="text.secondary">
          Intentos: {data.attempt_count ?? 0} · Actualizado:{" "}
          {formatDateTime(
            data.checkpoint_updated_at ?? data.checked_at,
          )}
        </Typography>
      </Stack>
    </Paper>
  );
}

function EvidenceDetails({ evidence }) {
  if (!evidence) return null;

  return (
    <Accordion disableGutters elevation={0} variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ sm: "center" }}
        >
          <FactCheckOutlinedIcon fontSize="small" />
          <Typography variant="body2">
            Evidencias ({evidence.evidence_count})
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Correlación: {evidence.correlation_id}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1}>
          <Typography variant="caption" color="text.secondary">
            Usuario: {evidence.actor_username} · Dependencia:{" "}
            {evidence.dependency} · Inicio:{" "}
            {formatDateTime(evidence.started_at)}
          </Typography>
          {(evidence.events ?? []).map((event) => (
            <Paper
              key={`${event.sequence}-${event.step}-${event.outcome}`}
              variant="outlined"
              sx={{ p: 1.25, borderRadius: 2 }}
            >
              <Typography variant="body2" fontWeight="bold">
                {event.sequence}. {stepLabel(event.step)} · {event.outcome}
              </Typography>
              {event.message && (
                <Typography variant="caption" color="text.secondary">
                  {event.message}
                </Typography>
              )}
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                {formatDateTime(event.recorded_at)}
              </Typography>
            </Paper>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

function ResultDetails({ result, evidence }) {
  if (!result) return null;

  const severity = result.success
    ? "success"
    : result.requires_manual_review
      ? "warning"
      : result.error_code
        ? "error"
        : "info";

  return (
    <Stack spacing={1.25} sx={{ mt: 1.5 }}>
      <Alert severity={severity} variant="outlined">
        <Stack spacing={0.5}>
          <Stack direction="row" spacing={1} alignItems="center">
            <ModeChip mode={result.mode ?? "DRY_RUN"} />
            <Typography variant="body2" fontWeight="bold">
              {result.operational_message}
            </Typography>
          </Stack>
          {result.error_code && (
            <Typography variant="caption">
              Código: {result.error_code}
            </Typography>
          )}
          {result.correlation_id && (
            <Typography variant="caption">
              Correlación: {result.correlation_id}
            </Typography>
          )}
        </Stack>
      </Alert>
      <CheckpointSummary data={result} />
      <EvidenceDetails evidence={evidence} />
      {result.technical_detail && (
        <Accordion disableGutters elevation={0} variant="outlined">
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="body2">Detalle técnico</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography
              variant="caption"
              component="pre"
              sx={{
                whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
                m: 0,
              }}
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
  const [executionMode, setExecutionMode] = useState("DRY_RUN");
  const [preflights, setPreflights] = useState({});
  const [results, setResults] = useState({});
  const [evidences, setEvidences] = useState({});
  const [loadingItems, setLoadingItems] = useState(new Set());
  const [busyItemId, setBusyItemId] = useState(null);
  const [dialogItem, setDialogItem] = useState(null);
  const [confirmation, setConfirmation] = useState("");

  const contracts = batch?.contracts ?? [];
  const isSuperuser = user?.role === "SUPERUSER";
  const selectedPreflight = dialogItem
    ? preflights[dialogItem.item_id]
    : null;
  const selectedResult = dialogItem
    ? results[dialogItem.item_id]
    : null;
  const selectedEvidence = dialogItem
    ? evidences[dialogItem.item_id]
    : null;
  const modeMeta =
    EXECUTION_MODES[executionMode] ?? EXECUTION_MODES.DRY_RUN;

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

  const changeMode = (event) => {
    const nextMode = event.target.value;
    setExecutionMode(nextMode);
    setPreflights({});
    setResults({});
    setEvidences({});
    setDialogItem(null);
    setConfirmation("");
  };

  const publishResult = (result) => {
    setResults((current) => ({
      ...current,
      [result.item_id]: result,
    }));
    onBatchChange?.((current) =>
      applyContractExecutionToBatch(current, result),
    );
  };

  const loadEvidence = async (item, correlationId) => {
    if (!correlationId) return null;
    try {
      const evidence = await getContractExecutionEvidence({
        batchId: batch.batch_id,
        itemId: item.item_id,
        correlationId,
      });
      setEvidences((current) => ({
        ...current,
        [item.item_id]: evidence,
      }));
      return evidence;
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible consultar las evidencias de ejecución.",
      );
      onNotify?.("warning", problem.message);
      return null;
    }
  };

  const loadPreflight = async (
    item,
    { openDialog = true } = {},
  ) => {
    setItemLoading(item.item_id, true);
    try {
      const preflight = await getContractExecutionPreflight(
        batch.batch_id,
        item.item_id,
        executionMode,
      );
      setPreflights((current) => ({
        ...current,
        [item.item_id]: preflight,
      }));
      if (openDialog) {
        setDialogItem(item);
        setConfirmation("");
      }
      onNotify?.(
        preflight.can_execute ? "success" : "warning",
        preflight.can_execute
          ? `El contrato ${item.contract_number} está listo para ${
              executionMode === "DRY_RUN"
                ? "simularse"
                : preflight.resumable
                  ? "reanudarse"
                  : "ejecutarse"
            }.`
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
      const result = await getContractExecutionStatus(
        batch.batch_id,
        item.item_id,
        executionMode,
      );
      publishResult(result);
      await loadEvidence(item, result.correlation_id);
      onNotify?.(
        "info",
        executionMode === "DRY_RUN"
          ? `Estado de simulación actualizado para ${item.contract_number}.`
          : `Checkpoint real actualizado para ${item.contract_number}.`,
      );
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible consultar el estado del contrato.",
      );
      onNotify?.("error", problem.message);
    } finally {
      setItemLoading(item.item_id, false);
    }
  };

  const executeContract = async () => {
    if (
      !dialogItem ||
      !selectedPreflight ||
      !confirmationValid ||
      busyItemId
    ) {
      return;
    }

    setBusyItemId(dialogItem.item_id);
    onBusyChange?.(true);
    try {
      const result = await executeSelectedContract({
        batchId: batch.batch_id,
        itemId: dialogItem.item_id,
        confirmation,
        executionId:
          executionMode === "REAL" && selectedPreflight.resumable
            ? selectedPreflight.execution_id
            : null,
        mode: executionMode,
      });
      publishResult(result);
      await loadEvidence(dialogItem, result.correlation_id);
      setDialogItem(null);
      setConfirmation("");
      onNotify?.(
        result.success
          ? "success"
          : result.requires_manual_review
            ? "warning"
            : "error",
        result.operational_message,
      );
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        executionMode === "DRY_RUN"
          ? "No fue posible simular el contrato seleccionado."
          : "No fue posible ejecutar el contrato seleccionado.",
      );
      setResults((current) => ({
        ...current,
        [dialogItem.item_id]: {
          mode: executionMode,
          writes_to_portal: executionMode === "REAL",
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
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ md: "center" }}
        >
          <Box>
            <Typography
              variant="h6"
              fontWeight="bold"
              color="#005026"
            >
              Ejecución individual de contratos
            </Typography>
            <Typography variant="body2" color="text.secondary">
              La simulación es el modo predeterminado. La ejecución
              masiva permanece deshabilitada.
            </Typography>
          </Box>

          <FormControl size="small" sx={{ minWidth: 220 }}>
            <InputLabel id="contract-execution-mode-label">
              Modo
            </InputLabel>
            <Select
              labelId="contract-execution-mode-label"
              value={executionMode}
              label="Modo"
              onChange={changeMode}
              disabled={Boolean(busyItemId)}
            >
              <MenuItem value="DRY_RUN">
                SIMULACIÓN — sin escritura
              </MenuItem>
              <MenuItem value="REAL">
                ESCRITURA REAL — restringida
              </MenuItem>
            </Select>
          </FormControl>
        </Stack>

        {executionMode === "DRY_RUN" ? (
          <Alert severity="info" icon={<ScienceOutlinedIcon />}>
            <strong>SIMULACIÓN:</strong> valida el flujo completo,
            genera correlación y evidencias, pero no abre Chrome ni
            modifica Gestión Transparente.
          </Alert>
        ) : (
          <Alert
            severity="error"
            icon={<WarningAmberOutlinedIcon />}
          >
            <strong>ESCRITURA REAL:</strong> solo estará disponible
            cuando exista autorización institucional explícita en el
            servidor. Puede modificar Gestión Transparente.
          </Alert>
        )}

        <TableContainer>
          <Table
            size="small"
            aria-label="Ejecución individual de contratos"
          >
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Contrato</strong>
                </TableCell>
                <TableCell>
                  <strong>Estado</strong>
                </TableCell>
                <TableCell>
                  <strong>Último resultado</strong>
                </TableCell>
                <TableCell align="right">
                  <strong>Acciones</strong>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {contracts.map((item) => {
                const preflight = preflights[item.item_id];
                const result = results[item.item_id];
                const evidence = evidences[item.item_id];
                const loading = loadingItems.has(item.item_id);
                const itemBusy = busyItemId === item.item_id;
                const terminal =
                  executionMode === "REAL" &&
                  ["COMPLETED", "FAILED", "MANUAL_REVIEW"].includes(
                    item.status,
                  );

                return (
                  <TableRow key={item.item_id} hover>
                    <TableCell>
                      <Typography
                        variant="body2"
                        fontWeight="bold"
                      >
                        {item.contract_number}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                      >
                        Fila {item.row_number} · {item.item_id}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Stack spacing={0.5} alignItems="flex-start">
                        {statusChip(
                          executionMode === "REAL"
                            ? result?.item_status ?? item.status
                            : item.status,
                        )}
                        <ModeChip mode={executionMode} />
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {stepLabel(
                          result?.last_completed_step ??
                            preflight?.last_completed_step,
                        )}
                      </Typography>
                      {result?.correlation_id && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Correlación: {result.correlation_id}
                        </Typography>
                      )}
                      {evidence && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                        >
                          Evidencias: {evidence.evidence_count}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Stack
                        direction="row"
                        spacing={1}
                        justifyContent="flex-end"
                      >
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={
                            loading ? (
                              <CircularProgress size={16} />
                            ) : (
                              <RefreshIcon />
                            )
                          }
                          onClick={() => loadStatus(item)}
                          disabled={
                            loading || Boolean(busyItemId)
                          }
                        >
                          Estado
                        </Button>
                        <Button
                          size="small"
                          variant="contained"
                          color={
                            executionMode === "REAL"
                              ? "error"
                              : "primary"
                          }
                          startIcon={
                            itemBusy ? (
                              <CircularProgress
                                size={16}
                                color="inherit"
                              />
                            ) : executionMode === "DRY_RUN" ? (
                              <ScienceOutlinedIcon />
                            ) : preflight?.resumable ? (
                              <ReplayIcon />
                            ) : (
                              <PlayArrowIcon />
                            )
                          }
                          onClick={() => loadPreflight(item)}
                          disabled={
                            loading ||
                            Boolean(busyItemId) ||
                            terminal
                          }
                          sx={
                            executionMode === "DRY_RUN"
                              ? {
                                  backgroundColor: "#005026",
                                  "&:hover": {
                                    backgroundColor: "#00441f",
                                  },
                                }
                              : undefined
                          }
                        >
                          {loading
                            ? "Comprobando…"
                            : contractActionLabel(
                                preflight,
                                executionMode,
                              )}
                        </Button>
                      </Stack>
                      <ResultDetails
                        result={result}
                        evidence={evidence}
                      />
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
        onClose={
          busyItemId
            ? undefined
            : () => setDialogItem(null)
        }
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
          >
            <ModeChip mode={executionMode} />
            <Typography component="span" variant="h6">
              {executionMode === "DRY_RUN"
                ? "Simular contrato"
                : selectedPreflight?.resumable
                  ? "Reanudar contrato"
                  : "Ejecutar contrato"}
            </Typography>
          </Stack>
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            <Typography>
              Contrato:{" "}
              <strong>{dialogItem?.contract_number}</strong>
            </Typography>

            {selectedPreflight && (
              <>
                <Alert
                  severity={
                    selectedPreflight.can_execute
                      ? executionMode === "DRY_RUN"
                        ? "info"
                        : "success"
                      : "warning"
                  }
                >
                  {selectedPreflight.can_execute
                    ? executionMode === "DRY_RUN"
                      ? "El preflight permite una simulación segura sin escritura."
                      : "El preflight permite continuar con la escritura real controlada."
                    : "La operación está bloqueada. Corrija las condiciones antes de continuar."}
                </Alert>

                {executionMode === "REAL" &&
                  !selectedPreflight.real_write_enabled && (
                    <Alert severity="error">
                      La escritura real no tiene autorización
                      institucional en el servidor.
                    </Alert>
                  )}

                {selectedPreflight.issues.map((issue) => (
                  <Alert
                    key={issue.code}
                    severity={
                      issue.blocking ? "error" : "info"
                    }
                    variant="outlined"
                  >
                    <strong>{issue.code}:</strong>{" "}
                    {issue.message}
                  </Alert>
                ))}

                <CheckpointSummary data={selectedPreflight} />

                {selectedPreflight.can_execute && (
                  <>
                    <Divider />
                    <Typography variant="body2">
                      Escriba exactamente:
                    </Typography>
                    <Paper
                      variant="outlined"
                      sx={{
                        p: 1.5,
                        backgroundColor: "#fafafa",
                      }}
                    >
                      <Typography
                        component="code"
                        fontWeight="bold"
                      >
                        {
                          selectedPreflight.required_confirmation
                        }
                      </Typography>
                    </Paper>
                    <TextField
                      autoFocus
                      fullWidth
                      label={
                        executionMode === "DRY_RUN"
                          ? "Confirmación de simulación"
                          : "Confirmación de escritura real"
                      }
                      value={confirmation}
                      onChange={(event) =>
                        setConfirmation(event.target.value)
                      }
                      error={
                        Boolean(confirmation) &&
                        !confirmationValid
                      }
                      helperText={
                        confirmation && !confirmationValid
                          ? "La frase no coincide."
                          : "La comparación ignora mayúsculas y espacios repetidos."
                      }
                      disabled={Boolean(busyItemId)}
                    />
                  </>
                )}
              </>
            )}

            <ResultDetails
              result={selectedResult}
              evidence={selectedEvidence}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setDialogItem(null)}
            disabled={Boolean(busyItemId)}
          >
            Cerrar
          </Button>
          {selectedPreflight?.can_execute && (
            <Button
              variant="contained"
              color={
                executionMode === "REAL"
                  ? "error"
                  : "primary"
              }
              onClick={executeContract}
              disabled={
                !confirmationValid || Boolean(busyItemId)
              }
              startIcon={
                busyItemId ? (
                  <CircularProgress
                    size={18}
                    color="inherit"
                  />
                ) : executionMode === "DRY_RUN" ? (
                  <ScienceOutlinedIcon />
                ) : selectedPreflight.resumable ? (
                  <ReplayIcon />
                ) : (
                  <PlayArrowIcon />
                )
              }
              sx={
                executionMode === "DRY_RUN"
                  ? {
                      backgroundColor: "#005026",
                      "&:hover": {
                        backgroundColor: "#00441f",
                      },
                    }
                  : undefined
              }
            >
              {busyItemId
                ? executionMode === "DRY_RUN"
                  ? "Simulando…"
                  : "Ejecutando…"
                : executionMode === "DRY_RUN"
                  ? "Simular contrato"
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

import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import HealthAndSafetyOutlinedIcon from "@mui/icons-material/HealthAndSafetyOutlined";
import LockOpenOutlinedIcon from "@mui/icons-material/LockOpenOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useEffect, useMemo, useState } from "react";
import {
  armInstitutionalTestPlan,
  cancelInstitutionalTestPlan,
  confirmationMatches,
  createInstitutionalTestPlan,
  diagnoseInstitutionalTestPlan,
  extractExecutionApiError,
  formatAuthorizationCountdown,
  getInstitutionalTestPlan,
} from "../api/batchContractExecution";

const ACTIVE_STATUSES = new Set(["DRAFT", "READY", "ARMED"]);

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

function remainingSeconds(expiresAt, now) {
  if (!expiresAt) return 0;
  const expires = new Date(expiresAt).getTime();
  if (!Number.isFinite(expires)) return 0;
  return Math.max(0, Math.ceil((expires - now) / 1000));
}

export default function InstitutionalTestPlanPanel({
  batchId,
  item,
  disabled = false,
  onPlanChange,
  onNotify,
}) {
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [clock, setClock] = useState(() => Date.now());
  const [createConfirmation, setCreateConfirmation] = useState("");
  const [armConfirmation, setArmConfirmation] = useState("");
  const [cancelConfirmation, setCancelConfirmation] = useState("");

  const secondsRemaining = remainingSeconds(plan?.expires_at, clock);
  const active =
    plan &&
    ACTIVE_STATUSES.has(plan.status) &&
    secondsRemaining > 0;
  const armed = active && plan.status === "ARMED";
  const createValid = confirmationMatches(
    createConfirmation,
    plan?.required_create_confirmation ??
      `CREAR PLAN INSTITUCIONAL ${item?.contract_number ?? ""}`,
  );
  const armValid = confirmationMatches(
    armConfirmation,
    plan?.required_arm_confirmation ??
      `ARMAR PRUEBA INSTITUCIONAL ${item?.contract_number ?? ""}`,
  );
  const cancelValid = confirmationMatches(
    cancelConfirmation,
    plan?.required_cancel_confirmation ??
      `CANCELAR PLAN INSTITUCIONAL ${item?.contract_number ?? ""}`,
  );

  const publish = (next) => {
    setPlan(next);
    onPlanChange?.(next);
  };

  const load = async () => {
    if (!batchId || !item?.item_id) return null;
    setLoading(true);
    try {
      const response = await getInstitutionalTestPlan({
        batchId,
        itemId: item.item_id,
      });
      publish(response);
      return response;
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible consultar el plan institucional.",
      );
      onNotify?.("warning", problem.message);
      return null;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId, item?.item_id]);

  useEffect(() => {
    if (!plan?.expires_at || !ACTIVE_STATUSES.has(plan.status)) {
      return undefined;
    }
    setClock(Date.now());
    const timer = window.setInterval(() => setClock(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [plan?.expires_at, plan?.status]);

  const run = async (action, successMessage) => {
    setLoading(true);
    try {
      const response = await action();
      publish(response);
      setCreateConfirmation("");
      setArmConfirmation("");
      setCancelConfirmation("");
      onNotify?.("success", successMessage);
    } catch (error) {
      const problem = extractExecutionApiError(
        error,
        "No fue posible actualizar el plan institucional.",
      );
      onNotify?.("error", problem.message);
    } finally {
      setLoading(false);
    }
  };

  const statusColor = armed
    ? "success"
    : plan?.status === "READY"
      ? "info"
      : plan?.status === "DRAFT"
        ? "warning"
        : "default";

  const diagnosticSummary = useMemo(() => {
    if (!plan?.diagnostic_checked_at) {
      return "El diagnóstico read-only todavía no se ha ejecutado.";
    }
    return plan.diagnostic_success
      ? "Diagnóstico read-only aprobado."
      : `Diagnóstico rechazado: ${plan.diagnostic_message ?? plan.diagnostic_code}`;
  }, [plan]);

  return (
    <Paper variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
      <Stack spacing={1.5}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ sm: "center" }}
          justifyContent="space-between"
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <HealthAndSafetyOutlinedIcon color="warning" />
            <Typography variant="subtitle2" fontWeight="bold">
              Plan institucional supervisado
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1}>
            <Chip
              size="small"
              color={statusColor}
              label={plan?.status ?? "NO CREADO"}
            />
            <Button
              size="small"
              startIcon={
                loading ? <CircularProgress size={15} /> : <RefreshIcon />
              }
              onClick={load}
              disabled={loading || disabled}
            >
              Actualizar
            </Button>
          </Stack>
        </Stack>

        {plan?.enabled === false && (
          <Alert severity="warning">
            La preparación institucional está deshabilitada en el servidor.
            Esta barrera es independiente de la escritura real.
          </Alert>
        )}

        <Alert severity={armed ? "warning" : "info"} variant="outlined">
          {armed
            ? "PLAN ARMADO — EJECUCIÓN REAL BLOQUEADA. El armado no emite token ni inicia Selenium contractual."
            : "El plan no habilita por sí solo ninguna escritura. Primero debe superar el diagnóstico read-only y luego armarse."}
        </Alert>

        {plan?.status === "READY" && plan?.arming_enabled !== true && (
          <Alert severity="warning">
            El armado institucional está deshabilitado en el servidor. El
            diagnóstico permanece válido, pero este plan no puede pasar a
            ARMED.
          </Alert>
        )}

        {plan?.expires_at && (
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              size="small"
              color={
                secondsRemaining > 60
                  ? "success"
                  : secondsRemaining > 0
                    ? "warning"
                    : "error"
              }
              label={`Ventana: ${formatAuthorizationCountdown(secondsRemaining)}`}
            />
            <Typography variant="caption" color="text.secondary">
              Vence: {formatDateTime(plan.expires_at)}
            </Typography>
          </Stack>
        )}

        <Typography variant="body2">{diagnosticSummary}</Typography>
        {plan?.diagnostic_checked_at && (
          <Typography variant="caption" color="text.secondary">
            Código: {plan.diagnostic_code ?? "—"} · Revisado:{" "}
            {formatDateTime(plan.diagnostic_checked_at)} · Duración:{" "}
            {plan.diagnostic_duration_ms ?? 0} ms
          </Typography>
        )}

        {!active && (
          <>
            <Typography variant="body2">
              Para crear una ventana de un solo contrato escriba:
            </Typography>
            <Typography component="code" fontWeight="bold">
              {plan?.required_create_confirmation ??
                `CREAR PLAN INSTITUCIONAL ${item?.contract_number ?? ""}`}
            </Typography>
            <TextField
              size="small"
              label="Confirmación de creación"
              value={createConfirmation}
              onChange={(event) => setCreateConfirmation(event.target.value)}
              disabled={loading || disabled || plan?.enabled === false}
            />
            <Box>
              <Button
                variant="outlined"
                color="warning"
                startIcon={<HealthAndSafetyOutlinedIcon />}
                disabled={
                  !createValid ||
                  loading ||
                  disabled ||
                  plan?.enabled === false
                }
                onClick={() =>
                  run(
                    () =>
                      createInstitutionalTestPlan({
                        batchId,
                        itemId: item.item_id,
                        confirmation: createConfirmation,
                      }),
                    "Plan institucional creado.",
                  )
                }
              >
                Crear plan
              </Button>
            </Box>
          </>
        )}

        {active && (
          <>
            <Divider />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button
                variant="outlined"
                startIcon={<FactCheckOutlinedIcon />}
                disabled={loading || disabled || plan.status === "ARMED"}
                onClick={() =>
                  run(
                    () =>
                      diagnoseInstitutionalTestPlan({
                        batchId,
                        itemId: item.item_id,
                        planId: plan.plan_id,
                      }),
                    "Diagnóstico read-only finalizado.",
                  )
                }
              >
                Diagnóstico read-only
              </Button>
            </Stack>

            {plan.status === "READY" && (
              <>
                <Typography variant="body2">
                  Para armar el plan escriba:
                </Typography>
                <Typography component="code" fontWeight="bold">
                  {plan.required_arm_confirmation}
                </Typography>
                <TextField
                  size="small"
                  label="Confirmación para armar"
                  value={armConfirmation}
                  onChange={(event) => setArmConfirmation(event.target.value)}
                  disabled={loading || disabled || plan?.arming_enabled !== true}
                />
                <Box>
                  <Button
                    variant="contained"
                    color="warning"
                    startIcon={<LockOpenOutlinedIcon />}
                    disabled={
                      !armValid ||
                      loading ||
                      disabled ||
                      plan?.arming_enabled !== true
                    }
                    onClick={() =>
                      run(
                        () =>
                          armInstitutionalTestPlan({
                            batchId,
                            itemId: item.item_id,
                            planId: plan.plan_id,
                            confirmation: armConfirmation,
                          }),
                        "Plan institucional armado.",
                      )
                    }
                  >
                    Armar plan
                  </Button>
                </Box>
              </>
            )}

            <Divider />
            <Typography variant="body2">
              Para cancelar el plan escriba:
            </Typography>
            <Typography component="code" fontWeight="bold">
              {plan.required_cancel_confirmation}
            </Typography>
            <TextField
              size="small"
              label="Confirmación de cancelación"
              value={cancelConfirmation}
              onChange={(event) => setCancelConfirmation(event.target.value)}
              disabled={loading || disabled}
            />
            <Box>
              <Button
                variant="outlined"
                color="error"
                startIcon={<CancelOutlinedIcon />}
                disabled={!cancelValid || loading || disabled}
                onClick={() =>
                  run(
                    () =>
                      cancelInstitutionalTestPlan({
                        batchId,
                        itemId: item.item_id,
                        planId: plan.plan_id,
                        confirmation: cancelConfirmation,
                      }),
                    "Plan institucional cancelado.",
                  )
                }
              >
                Cancelar plan
              </Button>
            </Box>
          </>
        )}

        {(plan?.events ?? []).length > 0 && (
          <Accordion disableGutters elevation={0} variant="outlined">
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="body2">
                Auditoría del plan ({plan.events.length})
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Stack spacing={1}>
                {plan.events.map((event) => (
                  <Paper
                    key={event.event_id}
                    variant="outlined"
                    sx={{ p: 1, borderRadius: 1.5 }}
                  >
                    <Typography variant="caption" fontWeight="bold">
                      {event.event_type}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      display="block"
                    >
                      {formatDateTime(event.recorded_at)}
                      {event.reason ? ` · ${event.reason}` : ""}
                    </Typography>
                  </Paper>
                ))}
              </Stack>
            </AccordionDetails>
          </Accordion>
        )}
      </Stack>
    </Paper>
  );
}

import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import PlaylistAddCheckIcon from "@mui/icons-material/PlaylistAddCheck";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import TravelExploreOutlinedIcon from "@mui/icons-material/TravelExploreOutlined";
import FindInPageOutlinedIcon from "@mui/icons-material/FindInPageOutlined";
import EditNoteOutlinedIcon from "@mui/icons-material/EditNoteOutlined";
import DataObjectOutlinedIcon from "@mui/icons-material/DataObjectOutlined";
import AccountBalanceOutlinedIcon from "@mui/icons-material/AccountBalanceOutlined";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Divider,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import api from "../api/axiosConfig";
import { useAuth } from "../auth/useAuth";
import BatchContractExecutionPanel from "../components/BatchContractExecutionPanel";
import { findProcessingBatch } from "../api/batchContractExecutionUtils";

function getApiError(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(" ");
  }
  return fallback;
}

function formatAmount(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value ?? "—";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(amount);
}

function SummaryCard({ label, value, icon }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2 }}>
      <Stack direction="row" spacing={1.5} alignItems="center">
        {icon}
        <Box>
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          <Typography variant="h5" fontWeight="bold">
            {value}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  );
}

function Home() {
  const { user } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [validation, setValidation] = useState(null);
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [createdBatch, setCreatedBatch] = useState(null);
  const [loading, setLoading] = useState(false);
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [preflight, setPreflight] = useState(null);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [checkingExecution, setCheckingExecution] = useState(false);
  const [portalProbe, setPortalProbe] = useState(null);
  const [probingPortal, setProbingPortal] = useState(false);
  const [assistantProbe, setAssistantProbe] = useState(null);
  const [probingAssistant, setProbingAssistant] = useState(false);
  const [headerDraftProbe, setHeaderDraftProbe] = useState(null);
  const [probingHeaderDraft, setProbingHeaderDraft] = useState(false);
  const [headerValidationProbe, setHeaderValidationProbe] = useState(null);
  const [probingHeaderValidation, setProbingHeaderValidation] = useState(false);
  const [generalDataDraftProbe, setGeneralDataDraftProbe] = useState(null);
  const [probingGeneralDataDraft, setProbingGeneralDataDraft] = useState(false);
  const [generalCompletionDraftProbe, setGeneralCompletionDraftProbe] = useState(null);
  const [probingGeneralCompletionDraft, setProbingGeneralCompletionDraft] = useState(false);
  const [generalValidationProbe, setGeneralValidationProbe] = useState(null);
  const [probingGeneralValidation, setProbingGeneralValidation] = useState(false);
  const [contractSaveProbe, setContractSaveProbe] = useState(null);
  const [savingTestContract, setSavingTestContract] = useState(false);
  const [contractSupervisorLinkProbe, setContractSupervisorLinkProbe] = useState(null);
  const [linkingSupervisor, setLinkingSupervisor] = useState(false);
  const [contractAvailabilityLinkProbe, setContractAvailabilityLinkProbe] = useState(null);
  const [linkingAvailability, setLinkingAvailability] = useState(false);
  const [contractBudgetRegisterLinkProbe, setContractBudgetRegisterLinkProbe] = useState(null);
  const [linkingBudgetRegister, setLinkingBudgetRegister] = useState(false);
  const [contractAdditionalDatesLinkProbe, setContractAdditionalDatesLinkProbe] = useState(null);
  const [linkingAdditionalDates, setLinkingAdditionalDates] = useState(false);
  const [startingExecution, setStartingExecution] = useState(false);
  const [cancellingBatch, setCancellingBatch] = useState(false);
  const [recoveringActiveBatch, setRecoveringActiveBatch] = useState(false);
  const [activeBatchRecovered, setActiveBatchRecovered] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    severity: "success",
    message: "",
  });

  const status = useMemo(() => {
    if (!validation) return null;
    if (validation.fully_valid) {
      return { label: "Archivo completamente válido", color: "success" };
    }
    if (validation.valid_count > 0) {
      return { label: "Archivo válido con observaciones", color: "warning" };
    }
    return { label: "Archivo sin contratos procesables", color: "error" };
  }, [validation]);

  const allValidRows = useMemo(
    () => validation?.valid_rows.map((row) => row.row_number) ?? [],
    [validation],
  );

  const portalProbeBusy =
    probingPortal ||
    probingAssistant ||
    probingHeaderDraft ||
    probingHeaderValidation ||
    probingGeneralDataDraft ||
    probingGeneralCompletionDraft ||
    probingGeneralValidation ||
    savingTestContract ||
    linkingSupervisor ||
    linkingAvailability ||
    linkingBudgetRegister ||
    linkingAdditionalDates;

  const allRowsSelected =
    allValidRows.length > 0 && allValidRows.every((row) => selectedRows.has(row));
  const someRowsSelected = selectedRows.size > 0 && !allRowsSelected;

  const showMessage = (severity, message) => {
    setSnackbar({ open: true, severity, message });
  };

  const recoverActiveBatch = async ({ notify = true } = {}) => {
    if (!user?.dependency || recoveringActiveBatch) return null;

    setRecoveringActiveBatch(true);
    try {
      const response = await api.get("/batches", {
        params: { limit: 50 },
      });
      const activeBatch = findProcessingBatch(response.data?.items);

      if (!activeBatch) {
        if (notify) {
          showMessage(
            "info",
            "No existe un lote PROCESSING para recuperar en esta dependencia.",
          );
        }
        return null;
      }

      setCreatedBatch(activeBatch);
      setActiveBatchRecovered(true);
      setPreflight(null);
      setExecutionStatus(null);
      if (notify) {
        showMessage(
          "success",
          `Se recuperó el lote activo ${activeBatch.batch_id}.`,
        );
      }
      return activeBatch;
    } catch (error) {
      if (notify) {
        showMessage(
          "error",
          getApiError(
            error,
            "No fue posible recuperar el lote activo.",
          ),
        );
      }
      return null;
    } finally {
      setRecoveringActiveBatch(false);
    }
  };

  const resetValidatedState = () => {
    setValidation(null);
    setSelectedRows(new Set());
    setCreatedBatch(null);
    setPreflight(null);
    setPortalProbe(null);
    setAssistantProbe(null);
    setHeaderDraftProbe(null);
    setHeaderValidationProbe(null);
    setGeneralDataDraftProbe(null);
    setGeneralCompletionDraftProbe(null);
    setGeneralValidationProbe(null);
    setContractSaveProbe(null);
    setContractSupervisorLinkProbe(null);
    setContractAvailabilityLinkProbe(null);
    setContractBudgetRegisterLinkProbe(null);
    setContractAdditionalDatesLinkProbe(null);
    setExecutionStatus(null);
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    resetValidatedState();
  };

  const validateSelectedFile = async () => {
    if (!selectedFile) {
      showMessage("warning", "Seleccione un archivo Excel antes de validar.");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    setLoading(true);
    try {
      const response = await api.post("/files/validate", formData, {
        timeout: 120000,
      });
      const outcome = response.data;
      setValidation(outcome);
      setSelectedRows(new Set(outcome.valid_rows.map((row) => row.row_number)));
      setCreatedBatch(null);
      showMessage(
        outcome.valid_count > 0 ? "success" : "warning",
        "La validación del archivo finalizó correctamente.",
      );
    } catch (error) {
      resetValidatedState();
      showMessage(
        "error",
        getApiError(error, "No fue posible validar el archivo seleccionado."),
      );
    } finally {
      setLoading(false);
    }
  };

  const clearValidation = () => {
    setSelectedFile(null);
    resetValidatedState();
    const input = document.getElementById("contracts-excel-input");
    if (input) input.value = "";
  };

  const toggleRow = (rowNumber) => {
    if (createdBatch) return;
    setSelectedRows((current) => {
      const next = new Set(current);
      if (next.has(rowNumber)) next.delete(rowNumber);
      else next.add(rowNumber);
      return next;
    });
  };

  const toggleAllRows = () => {
    if (createdBatch) return;
    setSelectedRows(
      allRowsSelected ? new Set() : new Set(allValidRows),
    );
  };

  const createBatch = async () => {
    if (!validation || selectedRows.size === 0) {
      showMessage("warning", "Seleccione al menos un contrato válido.");
      return;
    }

    setCreatingBatch(true);
    try {
      const response = await api.post("/batches", {
        validation_id: validation.validation_id,
        selected_row_numbers: [...selectedRows].sort((a, b) => a - b),
      });
      setCreatedBatch(response.data);
      setPreflight(null);
      setPortalProbe(null);
      setAssistantProbe(null);
      setHeaderDraftProbe(null);
      setHeaderValidationProbe(null);
      setGeneralDataDraftProbe(null);
      setGeneralCompletionDraftProbe(null);
      setGeneralValidationProbe(null);
      setContractSaveProbe(null);
      setContractSupervisorLinkProbe(null);
      setContractAvailabilityLinkProbe(null);
    setContractBudgetRegisterLinkProbe(null);
    setContractAdditionalDatesLinkProbe(null);
      setExecutionStatus(null);
      showMessage(
        "success",
        `Lote creado con ${response.data.selected_count} contrato(s).`,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(error, "No fue posible crear el lote."),
      );
    } finally {
      setCreatingBatch(false);
    }
  };

  const checkExecution = async () => {
    if (!createdBatch) return;
    setCheckingExecution(true);
    try {
      const response = await api.get(
        `/batches/${createdBatch.batch_id}/execution/preflight`,
      );
      setPreflight(response.data);
      showMessage(
        response.data.can_execute ? "success" : "warning",
        response.data.can_execute
          ? "El lote cumple las condiciones para ejecutarse."
          : "La ejecución permanece bloqueada por condiciones de seguridad.",
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(error, "No fue posible comprobar la ejecución del lote."),
      );
    } finally {
      setCheckingExecution(false);
    }
  };

  const probePortalNavigation = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    setProbingPortal(true);
    setPortalProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/probe`,
        null,
        { timeout: 120000 },
      );
      setPortalProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible comprobar el acceso de navegación al portal.",
        ),
      );
    } finally {
      setProbingPortal(false);
    }
  };

  const probeAssistantForm = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    setProbingAssistant(true);
    setAssistantProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/assistant-probe`,
        null,
        { timeout: 120000 },
      );
      setAssistantProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible comprobar el formulario C1-C2.",
        ),
      );
    } finally {
      setProbingAssistant(false);
    }
  };

  const probeHeaderDraft = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage("warning", "El lote no contiene contratos para el diagnóstico.");
      return;
    }

    setProbingHeaderDraft(true);
    setHeaderDraftProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/header-draft-probe`,
        { item_id: diagnosticItem.item_id },
        { timeout: 180000 },
      );
      setHeaderDraftProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible probar la carga controlada del encabezado C1-C2.",
        ),
      );
    } finally {
      setProbingHeaderDraft(false);
    }
  };

  const probeHeaderValidation = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para validar el encabezado.",
      );
      return;
    }

    setProbingHeaderValidation(true);
    setHeaderValidationProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/header-validation-probe`,
        { item_id: diagnosticItem.item_id },
        { timeout: 300000 },
      );
      setHeaderValidationProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible validar C1-C2 y comprobar los datos generales C3.",
        ),
      );
    } finally {
      setProbingHeaderValidation(false);
    }
  };

  const probeGeneralDataDraft = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para probar la carga C3.",
      );
      return;
    }

    setProbingGeneralDataDraft(true);
    setGeneralDataDraftProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/general-data-draft-probe`,
        { item_id: diagnosticItem.item_id },
        { timeout: 360000 },
      );
      setGeneralDataDraftProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible completar y comprobar los datos generales C3.",
        ),
      );
    } finally {
      setProbingGeneralDataDraft(false);
    }
  };


  const probeGeneralCompletionDraft = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para probar la carga C4.",
      );
      return;
    }

    setProbingGeneralCompletionDraft(true);
    setGeneralCompletionDraftProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/general-completion-draft-probe`,
        { item_id: diagnosticItem.item_id },
        { timeout: 480000 },
      );
      setGeneralCompletionDraftProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible completar y comprobar los datos C4.",
        ),
      );
    } finally {
      setProbingGeneralCompletionDraft(false);
    }
  };


  const probeGeneralValidation = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para probar la validación C3-C4.",
      );
      return;
    }

    setProbingGeneralValidation(true);
    setGeneralValidationProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/general-validation-probe`,
        { item_id: diagnosticItem.item_id },
        { timeout: 540000 },
      );
      setGeneralValidationProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible validar los datos generales C3-C4.",
        ),
      );
    } finally {
      setProbingGeneralValidation(false);
    }
  };


  const saveTestContract = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para realizar el guardado controlado.",
      );
      return;
    }

    const expected = `GUARDAR ${diagnosticItem.contract_number}`;
    const confirmation = window.prompt(
      "Esta acción registrará definitivamente el contrato en Gestión " +
      `Transparente. Escriba exactamente: ${expected}`,
    );
    if (confirmation === null) return;
    if (confirmation.trim().toLocaleUpperCase("es-CO") !== expected) {
      showMessage(
        "warning",
        `La confirmación no coincide. Debe escribir: ${expected}`,
      );
      return;
    }

    const accepted = window.confirm(
      "El contrato quedará guardado y cerrar Chrome no deshará la operación. " +
      "Confirme que el número contractual es único para esta prueba.",
    );
    if (!accepted) return;

    setSavingTestContract(true);
    setContractSaveProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/contract-save-probe`,
        {
          item_id: diagnosticItem.item_id,
          confirmation,
          allow_test_values: true,
        },
        { timeout: 660000 },
      );
      setContractSaveProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible guardar el contrato de prueba.",
        ),
      );
    } finally {
      setSavingTestContract(false);
    }
  };


  const saveContractAndLinkSupervisor = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para guardar y vincular.",
      );
      return;
    }

    const expected = `GUARDAR Y VINCULAR ${diagnosticItem.contract_number}`;
    const confirmation = window.prompt(
      "Esta acción registrará definitivamente el contrato y vinculará " +
      `su supervisor interno. Escriba exactamente: ${expected}`,
    );
    if (confirmation === null) return;
    if (confirmation.trim().toLocaleUpperCase("es-CO") !== expected) {
      showMessage(
        "warning",
        `La confirmación no coincide. Debe escribir: ${expected}`,
      );
      return;
    }

    const accepted = window.confirm(
      "El contrato y el supervisor quedarán vinculados definitivamente. " +
      "Cerrar Chrome no deshará estas operaciones. Confirme que el número " +
      "contractual todavía no existe en Gestión Transparente.",
    );
    if (!accepted) return;

    setLinkingSupervisor(true);
    setContractSupervisorLinkProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/contract-supervisor-link-probe`,
        {
          item_id: diagnosticItem.item_id,
          confirmation,
          allow_test_values: true,
        },
        { timeout: 900000 },
      );
      setContractSupervisorLinkProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible guardar el contrato y vincular el supervisor.",
        ),
      );
    } finally {
      setLinkingSupervisor(false);
    }
  };


  const saveContractSupervisorAndLinkAvailability = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para vincular al CDP.",
      );
      return;
    }

    const expected = `GUARDAR SUPERVISOR Y CDP ${diagnosticItem.contract_number}`;
    const confirmation = window.prompt(
      "Esta acción registrará el contrato, vinculará el supervisor y " +
      `vinculará el CDP. Escriba exactamente: ${expected}`,
    );
    if (confirmation === null) return;
    if (confirmation.trim().toLocaleUpperCase("es-CO") !== expected) {
      showMessage(
        "warning",
        `La confirmación no coincide. Debe escribir: ${expected}`,
      );
      return;
    }

    const accepted = window.confirm(
      "El contrato, el supervisor y el CDP quedarán registrados " +
      "definitivamente. Confirme que el número contractual todavía no " +
      "existe en Gestión Transparente.",
    );
    if (!accepted) return;

    setLinkingAvailability(true);
    setContractAvailabilityLinkProbe(null);
    setContractBudgetRegisterLinkProbe(null);
    setContractAdditionalDatesLinkProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/contract-availability-link-probe`,
        {
          item_id: diagnosticItem.item_id,
          confirmation,
          allow_test_values: true,
        },
        { timeout: 1080000 },
      );
      setContractAvailabilityLinkProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible guardar, vincular el supervisor y el CDP.",
        ),
      );
    } finally {
      setLinkingAvailability(false);
    }
  };


  const saveContractSupervisorCdpAndBudgetRegister = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para vincular al registro presupuestal.",
      );
      return;
    }

    const expected = `GUARDAR SUPERVISOR CDP Y RP ${diagnosticItem.contract_number}`;
    const confirmation = window.prompt(
      "Esta acción registrará el contrato, vinculará el supervisor, " +
      "el CDP y el registro presupuestal. Escriba exactamente: " +
      expected,
    );
    if (confirmation === null) return;
    if (confirmation.trim().toLocaleUpperCase("es-CO") !== expected) {
      showMessage(
        "warning",
        `La confirmación no coincide. Debe escribir: ${expected}`,
      );
      return;
    }

    const accepted = window.confirm(
      "El contrato, el supervisor, el CDP y el RP quedarán registrados " +
      "definitivamente. Confirme que el número contractual todavía no " +
      "existe en Gestión Transparente.",
    );
    if (!accepted) return;

    setLinkingBudgetRegister(true);
    setContractBudgetRegisterLinkProbe(null);
    setContractAdditionalDatesLinkProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/contract-budget-register-link-probe`,
        {
          item_id: diagnosticItem.item_id,
          confirmation,
          allow_test_values: true,
        },
        { timeout: 1260000 },
      );
      setContractBudgetRegisterLinkProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible guardar y vincular el registro presupuestal.",
        ),
      );
    } finally {
      setLinkingBudgetRegister(false);
    }
  };


  const saveContractThroughAdditionalDates = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    const diagnosticItem = createdBatch.contracts?.[0];
    if (!diagnosticItem) {
      showMessage(
        "warning",
        "El lote no contiene contratos para vincular las fechas adicionales.",
      );
      return;
    }

    const expected = `GUARDAR SUPERVISOR CDP RP Y FECHAS ${diagnosticItem.contract_number}`;
    const confirmation = window.prompt(
      "Esta acción registrará el contrato, supervisor, CDP, RP y fechas " +
      "adicionales. Escriba exactamente: " + expected,
    );
    if (confirmation === null) return;
    if (confirmation.trim().toLocaleUpperCase("es-CO") !== expected) {
      showMessage(
        "warning",
        `La confirmación no coincide. Debe escribir: ${expected}`,
      );
      return;
    }

    const accepted = window.confirm(
      "El contrato quedará registrado definitivamente hasta la etapa de " +
      "fechas adicionales. La pantalla de archivos se abrirá únicamente " +
      "como postcondición y no se gestionarán adjuntos.",
    );
    if (!accepted) return;

    setLinkingAdditionalDates(true);
    setContractAdditionalDatesLinkProbe(null);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/execution/contract-additional-dates-link-probe`,
        {
          item_id: diagnosticItem.item_id,
          confirmation,
          allow_test_values: true,
        },
        { timeout: 1440000 },
      );
      setContractAdditionalDatesLinkProbe(response.data);
      showMessage(
        response.data.success ? "success" : "warning",
        response.data.message,
      );
    } catch (error) {
      showMessage(
        "error",
        getApiError(
          error,
          "No fue posible guardar y vincular las fechas adicionales.",
        ),
      );
    } finally {
      setLinkingAdditionalDates(false);
    }
  };


  const refreshExecution = async () => {
    if (!createdBatch) return;
    try {
      const response = await api.get(
        `/batches/${createdBatch.batch_id}/execution`,
      );
      setExecutionStatus(response.data);
      setCreatedBatch(response.data.batch);
    } catch (error) {
      showMessage(
        "error",
        getApiError(error, "No fue posible consultar el progreso del lote."),
      );
    }
  };

  const cancelBatch = async () => {
    if (!createdBatch || createdBatch.status !== "READY") return;
    setCancellingBatch(true);
    try {
      const response = await api.post(
        `/batches/${createdBatch.batch_id}/cancel`,
      );
      setCreatedBatch(response.data);
      setPreflight(null);
      showMessage("success", "El lote READY fue cancelado.");
    } catch (error) {
      showMessage(
        "error",
        getApiError(error, "No fue posible cancelar el lote."),
      );
    } finally {
      setCancellingBatch(false);
    }
  };

  useEffect(() => {
    if (
      user?.role !== "SUPERUSER" ||
      !user?.dependency ||
      createdBatch
    ) {
      return undefined;
    }

    let cancelled = false;
    const recover = async () => {
      const recovered = await recoverActiveBatch({ notify: false });
      if (cancelled || !recovered) return;
      showMessage(
        "info",
        `Se reabrió el lote PROCESSING ${recovered.batch_id}.`,
      );
    };
    recover();
    return () => {
      cancelled = true;
    };
  }, [user?.dependency, user?.role]);

  useEffect(() => {
    if (!createdBatch || createdBatch.status !== "PROCESSING") return undefined;
    const timer = window.setInterval(refreshExecution, 1500);
    return () => window.clearInterval(timer);
  }, [createdBatch?.batch_id, createdBatch?.status]);


  return (
    <Box sx={{ maxWidth: 1280 }}>
      <Paper elevation={2} sx={{ p: { xs: 3, md: 4 }, borderRadius: 3 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ md: "center" }}
        >
          <Box>
            <Typography variant="h4" fontWeight="bold" color="#005026">
              Automatización de contratos
            </Typography>
            <Typography color="text.secondary" mt={0.5}>
              Dependencia de trabajo: <strong>{user?.dependency}</strong>
            </Typography>
          </Box>
          {status && (
            <Chip label={status.label} color={status.color} variant="outlined" />
          )}
        </Stack>

        <Alert severity="info" sx={{ mt: 3 }}>
          El archivo se valida usando la dependencia de su sesión. Los lotes quedan
          protegidos por una comprobación previa; ningún navegador se abre mientras
          la ejecución esté deshabilitada o el runner Selenium no esté disponible.
        </Alert>

        <Divider sx={{ my: 3 }} />

        <Stack spacing={2}>
          <input
            id="contracts-excel-input"
            type="file"
            accept=".xlsx,.xlsm"
            hidden
            onChange={handleFileChange}
          />

          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            alignItems={{ sm: "center" }}
          >
            <label htmlFor="contracts-excel-input">
              <Button
                component="span"
                variant="outlined"
                startIcon={<UploadFileIcon />}
                disabled={
                  loading ||
                  creatingBatch ||
                  createdBatch?.status === "PROCESSING"
                }
              >
                Seleccionar Excel
              </Button>
            </label>

            <Button
              variant="contained"
              onClick={validateSelectedFile}
              disabled={
                !selectedFile ||
                loading ||
                creatingBatch ||
                createdBatch?.status === "PROCESSING"
              }
              startIcon={
                loading ? (
                  <CircularProgress size={18} color="inherit" />
                ) : (
                  <CheckCircleOutlineIcon />
                )
              }
              sx={{
                backgroundColor: "#005026",
                "&:hover": { backgroundColor: "#00441f" },
              }}
            >
              {loading ? "Validando…" : "Validar archivo"}
            </Button>

            {validation && (
              <Button
                variant="text"
                onClick={clearValidation}
                disabled={loading || creatingBatch}
              >
                Validar otro archivo
              </Button>
            )}
          </Stack>

          <Paper
            variant="outlined"
            sx={{ p: 2, borderRadius: 2, backgroundColor: "#fafafa" }}
          >
            <Stack direction="row" spacing={1.5} alignItems="center">
              <DescriptionOutlinedIcon color="action" />
              <Box>
                <Typography fontWeight="bold">
                  {selectedFile?.name ?? "Ningún archivo seleccionado"}
                </Typography>
                {selectedFile && (
                  <Typography variant="body2" color="text.secondary">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                )}
              </Box>
            </Stack>
          </Paper>
        </Stack>
      </Paper>

      {createdBatch && !validation && (
        <Paper elevation={1} sx={{ p: 3, borderRadius: 3, mt: 3 }}>
          <Stack spacing={1.5}>
            <Alert severity="info" icon={<PlaylistAddCheckIcon />}>
              {activeBatchRecovered
                ? "Se recuperó automáticamente el lote activo de la dependencia."
                : "Hay un lote activo disponible para continuar."}
            </Alert>
            <Typography fontWeight="bold">Lote en ejecución recuperado</Typography>
            <Typography variant="body2" color="text.secondary">
              Identificador: {createdBatch.batch_id}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Estado: {createdBatch.status} · Contratos: {createdBatch.selected_count}
            </Typography>
            <Alert severity="warning" variant="outlined">
              No cree otro lote. Continúe el contrato PROCESSING desde este panel.
            </Alert>
            <BatchContractExecutionPanel
              batch={createdBatch}
              user={user}
              onBatchChange={setCreatedBatch}
              onBusyChange={setStartingExecution}
              onNotify={showMessage}
            />
          </Stack>
        </Paper>
      )}

      {validation && (
        <Stack spacing={3} mt={3}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(3, minmax(0, 1fr))",
              },
              gap: 2,
            }}
          >
            <SummaryCard
              label="Filas evaluadas"
              value={validation.total_rows}
              icon={<DescriptionOutlinedIcon color="primary" />}
            />
            <SummaryCard
              label="Contratos válidos"
              value={validation.valid_count}
              icon={<CheckCircleOutlineIcon color="success" />}
            />
            <SummaryCard
              label="Contratos inválidos"
              value={validation.invalid_count}
              icon={<ErrorOutlineIcon color="error" />}
            />
          </Box>

          {validation.batch_issues.map((issue) => (
            <Alert severity="warning" key={`${issue.code}-${issue.message}`}>
              <strong>{issue.code}:</strong> {issue.message}
            </Alert>
          ))}

          <Paper elevation={1} sx={{ p: 3, borderRadius: 3 }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              alignItems={{ sm: "center" }}
              spacing={1}
              mb={2}
            >
              <Typography variant="h6" fontWeight="bold" color="#005026">
                Contratos válidos
              </Typography>
              {validation.valid_rows.length > 0 && (
                <Typography variant="body2" color="text.secondary">
                  Seleccionados: {selectedRows.size} de {validation.valid_count}
                </Typography>
              )}
            </Stack>

            {validation.valid_rows.length === 0 ? (
              <Alert severity="warning">No se encontraron contratos válidos.</Alert>
            ) : (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={allRowsSelected}
                          indeterminate={someRowsSelected}
                          onChange={toggleAllRows}
                          disabled={Boolean(createdBatch)}
                          inputProps={{ "aria-label": "Seleccionar todos" }}
                        />
                      </TableCell>
                      <TableCell><strong>Fila</strong></TableCell>
                      <TableCell><strong>Contrato</strong></TableCell>
                      <TableCell><strong>Contratista</strong></TableCell>
                      <TableCell><strong>Proyecto</strong></TableCell>
                      <TableCell align="right"><strong>Valor</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {validation.valid_rows.map((row) => (
                      <TableRow
                        key={row.row_number}
                        hover
                        selected={selectedRows.has(row.row_number)}
                        onClick={() => toggleRow(row.row_number)}
                        sx={{ cursor: createdBatch ? "default" : "pointer" }}
                      >
                        <TableCell padding="checkbox">
                          <Checkbox
                            checked={selectedRows.has(row.row_number)}
                            disabled={Boolean(createdBatch)}
                            onClick={(event) => event.stopPropagation()}
                            onChange={() => toggleRow(row.row_number)}
                            inputProps={{
                              "aria-label": `Seleccionar fila ${row.row_number}`,
                            }}
                          />
                        </TableCell>
                        <TableCell>{row.row_number}</TableCell>
                        <TableCell>{row.contract_number}</TableCell>
                        <TableCell>{row.contractor_document}</TableCell>
                        <TableCell>{row.project_code}</TableCell>
                        <TableCell align="right">{formatAmount(row.amount)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>

          {validation.invalid_rows.length > 0 && (
            <Paper elevation={1} sx={{ p: 3, borderRadius: 3 }}>
              <Typography variant="h6" fontWeight="bold" color="error" mb={2}>
                Errores encontrados
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Fila</strong></TableCell>
                      <TableCell><strong>Contrato</strong></TableCell>
                      <TableCell><strong>Clasificación</strong></TableCell>
                      <TableCell><strong>Campo</strong></TableCell>
                      <TableCell><strong>Detalle</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {validation.invalid_rows.flatMap((row) =>
                      row.issues.map((issue, index) => (
                        <TableRow key={`${row.row_number}-${issue.code}-${index}`}>
                          <TableCell>{row.row_number}</TableCell>
                          <TableCell>{row.contract_number ?? "—"}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={
                                issue.code === "MISSING_CRITICAL_FIELD"
                                  ? "Error crítico"
                                  : "Error"
                              }
                              color={
                                issue.code === "MISSING_CRITICAL_FIELD"
                                  ? "error"
                                  : "warning"
                              }
                              variant="outlined"
                            />
                          </TableCell>
                          <TableCell>{issue.field ?? "General"}</TableCell>
                          <TableCell>{issue.message}</TableCell>
                        </TableRow>
                      )),
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          )}

          <Paper variant="outlined" sx={{ p: 3, borderRadius: 3 }}>
            {createdBatch ? (
              <Stack spacing={1.5}>
                <Alert severity="success" icon={<PlaylistAddCheckIcon />}>
                  El lote fue creado y quedó listo para la etapa de ejecución.
                </Alert>
                <Typography fontWeight="bold">Lote preparado</Typography>
                <Typography variant="body2" color="text.secondary">
                  Identificador: {createdBatch.batch_id}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Estado: {createdBatch.status} · Contratos: {createdBatch.selected_count}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  La creación del lote no abre el navegador. Compruebe las condiciones
                  antes de autorizar cualquier ejecución contra el portal real.
                </Typography>

                {user?.role === "SUPERUSER" && (
                  <Stack spacing={1.5} mt={1}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      spacing={1.5}
                      useFlexGap
                      flexWrap="wrap"
                    >
                      <Button
                        variant="outlined"
                        startIcon={
                          checkingExecution ? (
                            <CircularProgress size={18} />
                          ) : (
                            <FactCheckOutlinedIcon />
                          )
                        }
                        onClick={checkExecution}
                        disabled={
                          checkingExecution ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {checkingExecution ? "Comprobando…" : "Comprobar ejecución"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingPortal ? (
                            <CircularProgress size={18} />
                          ) : (
                            <TravelExploreOutlinedIcon />
                          )
                        }
                        onClick={probePortalNavigation}
                        disabled={
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingPortal ? "Probando acceso…" : "Probar acceso GT"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingAssistant ? (
                            <CircularProgress size={18} />
                          ) : (
                            <FindInPageOutlinedIcon />
                          )
                        }
                        onClick={probeAssistantForm}
                        disabled={
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingAssistant
                          ? "Comprobando C1-C2…"
                          : "Probar formulario C1-C2"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingHeaderDraft ? (
                            <CircularProgress size={18} />
                          ) : (
                            <EditNoteOutlinedIcon />
                          )
                        }
                        onClick={probeHeaderDraft}
                        disabled={
                          probingHeaderDraft ||
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingHeaderDraft
                          ? "Cargando C1-C2…"
                          : "Probar carga C1-C2"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingHeaderValidation ? (
                            <CircularProgress size={18} />
                          ) : (
                            <CheckCircleOutlineIcon />
                          )
                        }
                        onClick={probeHeaderValidation}
                        disabled={
                          probingHeaderValidation ||
                          probingHeaderDraft ||
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingHeaderValidation
                          ? "Validando C1-C2…"
                          : "Probar validación C1-C2"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingGeneralDataDraft ? (
                            <CircularProgress size={18} />
                          ) : (
                            <DataObjectOutlinedIcon />
                          )
                        }
                        onClick={probeGeneralDataDraft}
                        disabled={
                          probingGeneralDataDraft ||
                          probingHeaderValidation ||
                          probingHeaderDraft ||
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingGeneralDataDraft
                          ? "Cargando C3…"
                          : "Probar carga C3"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingGeneralCompletionDraft ? (
                            <CircularProgress size={18} />
                          ) : (
                            <AccountBalanceOutlinedIcon />
                          )
                        }
                        onClick={probeGeneralCompletionDraft}
                        disabled={
                          probingGeneralCompletionDraft ||
                          probingGeneralDataDraft ||
                          probingHeaderValidation ||
                          probingHeaderDraft ||
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingGeneralCompletionDraft
                          ? "Cargando C4…"
                          : "Probar carga C4"}
                      </Button>

                      <Button
                        variant="outlined"
                        startIcon={
                          probingGeneralValidation ? (
                            <CircularProgress size={18} />
                          ) : (
                            <CheckCircleOutlineIcon />
                          )
                        }
                        onClick={probeGeneralValidation}
                        disabled={
                          probingGeneralValidation ||
                          probingGeneralCompletionDraft ||
                          probingGeneralDataDraft ||
                          probingHeaderValidation ||
                          probingHeaderDraft ||
                          probingAssistant ||
                          probingPortal ||
                          startingExecution ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {probingGeneralValidation
                          ? "Validando C3-C4…"
                          : "Probar validación C3-C4"}
                      </Button>

                      <Button
                        variant="contained"
                        color="warning"
                        startIcon={
                          savingTestContract ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <SaveOutlinedIcon />
                          )
                        }
                        onClick={saveTestContract}
                        disabled={
                          portalProbeBusy ||
                          createdBatch.status !== "READY" ||
                          !generalValidationProbe?.success ||
                          contractSaveProbe?.success ||
                          contractSupervisorLinkProbe?.success ||
                          contractAvailabilityLinkProbe?.success ||
                          contractBudgetRegisterLinkProbe?.success ||
                          contractAdditionalDatesLinkProbe?.success
                        }
                      >
                        {savingTestContract
                          ? "Guardando contrato…"
                          : "Guardar contrato de prueba"}
                      </Button>

                      <Button
                        variant="contained"
                        color="secondary"
                        startIcon={
                          linkingSupervisor ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <PlaylistAddCheckIcon />
                          )
                        }
                        onClick={saveContractAndLinkSupervisor}
                        disabled={
                          portalProbeBusy ||
                          createdBatch.status !== "READY" ||
                          !generalValidationProbe?.success ||
                          contractSaveProbe?.success ||
                          contractSupervisorLinkProbe?.success ||
                          contractAvailabilityLinkProbe?.success ||
                          contractBudgetRegisterLinkProbe?.success ||
                          contractAdditionalDatesLinkProbe?.success
                        }
                      >
                        {linkingSupervisor
                          ? "Guardando y vinculando…"
                          : "Guardar y vincular supervisor"}
                      </Button>

                      <Button
                        variant="contained"
                        color="secondary"
                        startIcon={
                          linkingAvailability ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <PlaylistAddCheckIcon />
                          )
                        }
                        onClick={saveContractSupervisorAndLinkAvailability}
                        disabled={
                          portalProbeBusy ||
                          createdBatch.status !== "READY" ||
                          !generalValidationProbe?.success ||
                          contractSaveProbe?.success ||
                          contractSupervisorLinkProbe?.success ||
                          contractAvailabilityLinkProbe?.success ||
                          contractBudgetRegisterLinkProbe?.success ||
                          contractAdditionalDatesLinkProbe?.success
                        }
                      >
                        {linkingAvailability
                          ? "Guardando y vinculando CDP…"
                          : "Guardar, supervisor y CDP"}
                      </Button>


                      <Button
                        variant="contained"
                        color="secondary"
                        startIcon={
                          linkingBudgetRegister ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <PlaylistAddCheckIcon />
                          )
                        }
                        onClick={saveContractSupervisorCdpAndBudgetRegister}
                        disabled={
                          portalProbeBusy ||
                          createdBatch.status !== "READY" ||
                          !generalValidationProbe?.success ||
                          contractSaveProbe?.success ||
                          contractSupervisorLinkProbe?.success ||
                          contractAvailabilityLinkProbe?.success ||
                          contractBudgetRegisterLinkProbe?.success ||
                          contractAdditionalDatesLinkProbe?.success
                        }
                      >
                        {linkingBudgetRegister
                          ? "Guardando y vinculando RP…"
                          : "Guardar, supervisor, CDP y RP"}
                      </Button>


                      <Button
                        variant="contained"
                        color="secondary"
                        startIcon={
                          linkingAdditionalDates ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <PlaylistAddCheckIcon />
                          )
                        }
                        onClick={saveContractThroughAdditionalDates}
                        disabled={
                          portalProbeBusy ||
                          createdBatch.status !== "READY" ||
                          !generalValidationProbe?.success ||
                          contractSaveProbe?.success ||
                          contractSupervisorLinkProbe?.success ||
                          contractAvailabilityLinkProbe?.success ||
                          contractBudgetRegisterLinkProbe?.success ||
                          contractAdditionalDatesLinkProbe?.success
                        }
                      >
                        {linkingAdditionalDates
                          ? "Guardando y vinculando fechas…"
                          : "Guardar hasta fechas adicionales"}
                      </Button>


                      <Button
                        color="error"
                        variant="text"
                        startIcon={
                          cancellingBatch ? (
                            <CircularProgress size={18} color="inherit" />
                          ) : (
                            <CancelOutlinedIcon />
                          )
                        }
                        onClick={cancelBatch}
                        disabled={
                          cancellingBatch ||
                          portalProbeBusy ||
                          createdBatch.status !== "READY"
                        }
                      >
                        {cancellingBatch ? "Cancelando…" : "Cancelar lote"}
                      </Button>
                    </Stack>

                    {preflight && (
                      <Stack spacing={1}>
                        <Alert severity={preflight.can_execute ? "success" : "warning"}>
                          {preflight.can_execute
                            ? "El lote cumple todas las condiciones de ejecución."
                            : "El lote no puede ejecutarse todavía."}
                        </Alert>
                        {preflight.issues.map((issue) => (
                          <Alert
                            key={issue.code}
                            severity={issue.blocking ? "error" : "info"}
                            variant="outlined"
                          >
                            <strong>{issue.code}:</strong> {issue.message}
                          </Alert>
                        ))}
                      </Stack>
                    )}

                    <BatchContractExecutionPanel
                      batch={createdBatch}
                      user={user}
                      onBatchChange={setCreatedBatch}
                      onBusyChange={setStartingExecution}
                      onNotify={showMessage}
                    />

                    {portalProbe && (
                      <Alert
                        severity={portalProbe.success ? "success" : "warning"}
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {portalProbe.code}: {portalProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Autenticado: {portalProbe.authenticated ? "Sí" : "No"} ·
                            Menú Contratación: {portalProbe.contracting_menu_found ? "Sí" : "No"} ·
                            Ingresar Contrato: {portalProbe.enter_contract_found ? "Sí" : "No"} ·
                            Acceso al Asistente: {portalProbe.assistant_access_found ? "Sí" : "No"} ·
                            Duración: {(portalProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Esta prueba no abre el formulario contractual ni guarda información.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {assistantProbe && (
                      <Alert
                        severity={assistantProbe.success ? "success" : "warning"}
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {assistantProbe.code}: {assistantProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Autenticado: {assistantProbe.authenticated ? "Sí" : "No"} ·
                            Asistente abierto: {assistantProbe.assistant_opened ? "Sí" : "No"} ·
                            Contenedor: {assistantProbe.assistant_container_found ? "Sí" : "No"} ·
                            Tipo Contrato: {assistantProbe.record_type_found ? "Sí" : "No"} ·
                            Número: {assistantProbe.contract_number_found ? "Sí" : "No"} ·
                            Contratista: {assistantProbe.contractor_search_found ? "Sí" : "No"} ·
                            Proyecto: {assistantProbe.project_search_found ? "Sí" : "No"} ·
                            Validar: {assistantProbe.validate_button_found ? "Sí" : "No"} ·
                            Duración: {(assistantProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          {assistantProbe.missing_controls?.length > 0 && (
                            <Typography variant="caption" color="error">
                              Controles faltantes:{" "}
                              {assistantProbe.missing_controls.join(", ")}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            El diagnóstico abre el formulario, pero no escribe,
                            no selecciona contratista o proyecto y no pulsa Validar.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {headerDraftProbe && (
                      <Alert
                        severity={headerDraftProbe.success ? "success" : "warning"}
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {headerDraftProbe.code}: {headerDraftProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {headerDraftProbe.row_number} ·
                            Contrato: {headerDraftProbe.contract_number} ·
                            Contratista: {headerDraftProbe.contractor_document} ·
                            Proyecto: {headerDraftProbe.project_code}
                          </Typography>
                          <Typography variant="caption">
                            Tipo Contrato: {headerDraftProbe.record_type_selected ? "Sí" : "No"} ·
                            Número escrito: {headerDraftProbe.contract_number_written ? "Sí" : "No"} ·
                            Naturaleza: {headerDraftProbe.contractor_nature_selected ? "Sí" : "No"} ·
                            Contratista seleccionado: {headerDraftProbe.contractor_selected ? "Sí" : "No"} ·
                            Proyecto seleccionado: {headerDraftProbe.project_selected ? "Sí" : "No"} ·
                            Validar disponible: {headerDraftProbe.validate_button_found ? "Sí" : "No"} ·
                            Validar pulsado: {headerDraftProbe.validate_clicked ? "Sí" : "No"} ·
                            Duración: {(headerDraftProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            Se utiliza únicamente el primer contrato del lote. El navegador
                            se cierra sin pulsar Validar ni guardar información.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {headerValidationProbe && (
                      <Alert
                        severity={
                          headerValidationProbe.success ? "success" : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {headerValidationProbe.code}:{" "}
                            {headerValidationProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {headerValidationProbe.row_number} ·
                            Contrato: {headerValidationProbe.contract_number} ·
                            Contratista:{" "}
                            {headerValidationProbe.contractor_document} ·
                            Proyecto: {headerValidationProbe.project_code}
                          </Typography>
                          <Typography variant="caption">
                            Encabezado cargado:{" "}
                            {headerValidationProbe.contractor_selected &&
                            headerValidationProbe.project_selected
                              ? "Sí"
                              : "No"} ·
                            Validar pulsado:{" "}
                            {headerValidationProbe.validate_clicked ? "Sí" : "No"} ·
                            Validación confirmada:{" "}
                            {headerValidationProbe.header_validation_confirmed
                              ? "Sí"
                              : "No"} ·
                            C3 disponible:{" "}
                            {headerValidationProbe.general_data_ready
                              ? "Sí"
                              : "No"} ·
                            Guardar pulsado:{" "}
                            {headerValidationProbe.save_clicked ? "Sí" : "No"} ·
                            Duración:{" "}
                            {(headerValidationProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption">
                            Objeto:{" "}
                            {headerValidationProbe.general_object_found
                              ? "Sí"
                              : "No"} ·
                            Fecha suscripción:{" "}
                            {headerValidationProbe.general_signing_date_found
                              ? "Sí"
                              : "No"} ·
                            Fecha inicio:{" "}
                            {headerValidationProbe.general_starting_date_found
                              ? "Sí"
                              : "No"} ·
                            Valor:{" "}
                            {headerValidationProbe.general_amount_found
                              ? "Sí"
                              : "No"} ·
                            Plazo:{" "}
                            {headerValidationProbe.general_contract_term_found
                              ? "Sí"
                              : "No"}
                          </Typography>
                          {headerValidationProbe.missing_controls?.length > 0 && (
                            <Typography variant="caption" color="error">
                              Controles C3 faltantes:{" "}
                              {headerValidationProbe.missing_controls.join(", ")}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            La prueba pulsa Validar para habilitar C3, pero no
                            completa los datos generales ni pulsa Guardar.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {generalDataDraftProbe && (
                      <Alert
                        severity={
                          generalDataDraftProbe.success ? "success" : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {generalDataDraftProbe.code}: {" "}
                            {generalDataDraftProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {generalDataDraftProbe.row_number} ·
                            Contrato: {generalDataDraftProbe.contract_number} ·
                            Contratista: {generalDataDraftProbe.contractor_document} ·
                            Proyecto: {generalDataDraftProbe.project_code}
                          </Typography>
                          <Typography variant="caption">
                            Encabezado validado: {generalDataDraftProbe.header_validation_confirmed ? "Sí" : "No"} ·
                            C3 completo: {generalDataDraftProbe.general_data_completed ? "Sí" : "No"} ·
                            Validación general pulsada: {generalDataDraftProbe.general_validate_clicked ? "Sí" : "No"} ·
                            Guardar pulsado: {generalDataDraftProbe.save_clicked ? "Sí" : "No"} ·
                            Duración: {(generalDataDraftProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption">
                            Objeto: {generalDataDraftProbe.object_written ? "Sí" : "No"} ·
                            Fecha suscripción: {generalDataDraftProbe.signing_date_written ? "Sí" : "No"} ·
                            Fecha inicio: {generalDataDraftProbe.starting_date_written ? "Sí" : "No"} ·
                            Valor: {generalDataDraftProbe.amount_written ? "Sí" : "No"} ·
                            Valor en letras: {generalDataDraftProbe.amount_in_words_generated ? "Sí" : "No"} ·
                            Plazo: {generalDataDraftProbe.contract_term_written ? "Sí" : "No"} ·
                            Unidad días: {generalDataDraftProbe.term_unit_days_selected ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Modalidad: {generalDataDraftProbe.process_type_selected ? "Sí" : "No"} ·
                            Procedimiento: {generalDataDraftProbe.procedure_selected ? "Sí" : "No"} ·
                            Tipo de contrato: {generalDataDraftProbe.contract_type_selected ? "Sí" : "No"} ·
                            Moneda extranjera No: {generalDataDraftProbe.other_currency_no_selected ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            La prueba completa C3 con el primer contrato del lote,
                            pero no pulsa la validación general ni Guardar.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {generalCompletionDraftProbe && (
                      <Alert
                        severity={
                          generalCompletionDraftProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {generalCompletionDraftProbe.code}:{" "}
                            {generalCompletionDraftProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {generalCompletionDraftProbe.row_number} ·
                            Contrato: {generalCompletionDraftProbe.contract_number} ·
                            Contratista: {generalCompletionDraftProbe.contractor_document} ·
                            Proyecto: {generalCompletionDraftProbe.project_code}
                          </Typography>
                          <Typography variant="caption">
                            C3 completo: {generalCompletionDraftProbe.general_data_completed ? "Sí" : "No"} ·
                            C4 completo: {generalCompletionDraftProbe.general_completion_completed ? "Sí" : "No"} ·
                            Validación general pulsada: {generalCompletionDraftProbe.general_validate_clicked ? "Sí" : "No"} ·
                            Guardar pulsado: {generalCompletionDraftProbe.save_clicked ? "Sí" : "No"} ·
                            Duración: {(generalCompletionDraftProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption">
                            Plan de Gobierno: {generalCompletionDraftProbe.government_plan_selected ? "Sí" : "No"} ·
                            Año: {generalCompletionDraftProbe.budget_year_selected ? "Sí" : "No"} ·
                            Rubro: {generalCompletionDraftProbe.budget_item_selected ? "Sí" : "No"} ·
                            Sub-Sector: {generalCompletionDraftProbe.budget_subsector_selected ? "Sí" : "No"} ·
                            Vincular presupuesto pulsado: {generalCompletionDraftProbe.budget_link_clicked ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            SECOP Sí: {generalCompletionDraftProbe.secop_yes_selected ? "Sí" : "No"} ·
                            URL SECOP: {generalCompletionDraftProbe.secop_url_written ? "Sí" : "No"} ·
                            Indicadores contractuales en No:{" "}
                            {generalCompletionDraftProbe.advance_no_selected &&
                            generalCompletionDraftProbe.commercial_trust_no_selected &&
                            generalCompletionDraftProbe.urgency_no_selected &&
                            generalCompletionDraftProbe.future_commitment_no_selected &&
                            generalCompletionDraftProbe.cooperation_contract_no_selected
                              ? "Sí"
                              : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Departamento: {generalCompletionDraftProbe.execution_department_selected ? "Sí" : "No"} ·
                            Municipio: {generalCompletionDraftProbe.execution_city_selected ? "Sí" : "No"} ·
                            Validar final disponible: {generalCompletionDraftProbe.final_validate_button_found ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            La prueba completa C3-C4 con el primer contrato del lote,
                            pero no pulsa la validación general ni Guardar.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}

                    {generalValidationProbe && (
                      <Alert
                        severity={
                          generalValidationProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {generalValidationProbe.code}:{" "}
                            {generalValidationProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {generalValidationProbe.row_number} ·
                            Contrato: {generalValidationProbe.contract_number} ·
                            Contratista: {generalValidationProbe.contractor_document} ·
                            Proyecto: {generalValidationProbe.project_code}
                          </Typography>
                          <Typography variant="caption">
                            C3 completo: {generalValidationProbe.general_data_completed ? "Sí" : "No"} ·
                            C4 completo: {generalValidationProbe.general_completion_completed ? "Sí" : "No"} ·
                            Validar final disponible: {generalValidationProbe.final_validate_button_found ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Validación general pulsada: {generalValidationProbe.general_validate_clicked ? "Sí" : "No"} ·
                            Validación confirmada: {generalValidationProbe.general_validation_confirmed ? "Sí" : "No"} ·
                            Guardar disponible: {generalValidationProbe.save_button_found ? "Sí" : "No"} ·
                            Guardar pulsado: {generalValidationProbe.save_clicked ? "Sí" : "No"} ·
                            Duración: {(generalValidationProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            La prueba valida C3-C4 y confirma el botón Guardar,
                            pero no registra el contrato.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}


                    {contractSaveProbe && (
                      <Alert
                        severity={
                          contractSaveProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {contractSaveProbe.code}:{" "}
                            {contractSaveProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {contractSaveProbe.row_number} ·
                            Contrato: {contractSaveProbe.contract_number} ·
                            Valor: {formatAmount(contractSaveProbe.amount)}
                          </Typography>
                          <Typography variant="caption">
                            Guardar pulsado: {contractSaveProbe.save_clicked ? "Sí" : "No"} ·
                            Diálogo de éxito: {contractSaveProbe.success_dialog_found ? "Sí" : "No"} ·
                            Aceptar pulsado: {contractSaveProbe.success_dialog_accepted ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Contrato guardado confirmado: {contractSaveProbe.contract_saved_confirmed ? "Sí" : "No"} ·
                            Supervisor disponible: {contractSaveProbe.supervisor_section_found ? "Sí" : "No"} ·
                            Duración: {(contractSaveProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          <Typography variant="caption" color="error">
                            El contrato ya fue registrado. No repita el guardado
                            con el mismo número.
                          </Typography>
                        </Stack>
                      </Alert>
                    )}


                    {contractSupervisorLinkProbe && (
                      <Alert
                        severity={
                          contractSupervisorLinkProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {contractSupervisorLinkProbe.code}: {" "}
                            {contractSupervisorLinkProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {contractSupervisorLinkProbe.row_number} ·
                            Contrato: {contractSupervisorLinkProbe.contract_number} ·
                            Supervisor: {contractSupervisorLinkProbe.supervisor_document} ·
                            Tipo: {contractSupervisorLinkProbe.supervisor_type} ·
                            Valor: {formatAmount(contractSupervisorLinkProbe.amount)}
                          </Typography>
                          <Typography variant="caption">
                            Contrato guardado: {contractSupervisorLinkProbe.contract_saved_confirmed ? "Sí" : "No"} ·
                            Diálogo supervisor: {contractSupervisorLinkProbe.supervisor_dialog_opened ? "Sí" : "No"} ·
                            Persona: {contractSupervisorLinkProbe.supervisor_nature_selected ? "Sí" : "No"} ·
                            Cédula: {contractSupervisorLinkProbe.supervisor_id_type_selected ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Coincidencia encontrada: {contractSupervisorLinkProbe.supervisor_result_found ? "Sí" : "No"} ·
                            Supervisor seleccionado: {contractSupervisorLinkProbe.supervisor_selected ? "Sí" : "No"} ·
                            Tipo Interno: {contractSupervisorLinkProbe.supervisor_type_internal_confirmed ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Validar pulsado: {contractSupervisorLinkProbe.supervisor_validate_clicked ? "Sí" : "No"} ·
                            Vincular pulsado: {contractSupervisorLinkProbe.supervisor_link_clicked ? "Sí" : "No"} ·
                            Éxito aceptado: {contractSupervisorLinkProbe.success_dialog_accepted ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Supervisor vinculado: {contractSupervisorLinkProbe.supervisor_linked_confirmed ? "Sí" : "No"} ·
                            Disponibilidad disponible: {contractSupervisorLinkProbe.availability_section_found ? "Sí" : "No"} ·
                            Duración: {(contractSupervisorLinkProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          {contractSupervisorLinkProbe.success ? (
                            <Typography variant="caption" color="error">
                              El contrato y el supervisor quedaron registrados.
                              No repita este flujo con el mismo número contractual.
                            </Typography>
                          ) : contractSupervisorLinkProbe.contract_saved_confirmed ? (
                            <Typography variant="caption" color="error">
                              El contrato sí quedó registrado, pero el supervisor
                              no fue vinculado. No repita el guardado con este
                              número contractual.
                            </Typography>
                          ) : (
                            <Typography variant="caption" color="warning.main">
                              El contrato no quedó confirmado como guardado.
                              Revise el código de error antes de reintentar.
                            </Typography>
                          )}
                        </Stack>
                      </Alert>
                    )}


                    {contractAvailabilityLinkProbe && (
                      <Alert
                        severity={
                          contractAvailabilityLinkProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {contractAvailabilityLinkProbe.code}: {" "}
                            {contractAvailabilityLinkProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {contractAvailabilityLinkProbe.row_number} ·
                            Contrato: {contractAvailabilityLinkProbe.contract_number} ·
                            Supervisor: {contractAvailabilityLinkProbe.supervisor_document} ·
                            CDP: {contractAvailabilityLinkProbe.cdp_code} ·
                            Valor: {formatAmount(contractAvailabilityLinkProbe.amount)}
                          </Typography>
                          <Typography variant="caption">
                            Contrato guardado: {contractAvailabilityLinkProbe.contract_saved_confirmed ? "Sí" : "No"} ·
                            Supervisor vinculado: {contractAvailabilityLinkProbe.supervisor_linked_confirmed ? "Sí" : "No"} ·
                            Disponibilidad disponible: {contractAvailabilityLinkProbe.availability_section_found ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Búsqueda CDP escrita: {contractAvailabilityLinkProbe.availability_search_written ? "Sí" : "No"} ·
                            Coincidencia CDP: {contractAvailabilityLinkProbe.availability_result_matches ? "Sí" : "No"} ·
                            Vincular pulsado: {contractAvailabilityLinkProbe.availability_link_clicked ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            CDP vinculado: {contractAvailabilityLinkProbe.availability_linked_row_confirmed ? "Sí" : "No"} ·
                            Continuar pulsado: {contractAvailabilityLinkProbe.continue_clicked ? "Sí" : "No"} ·
                            Registro presupuestal disponible: {contractAvailabilityLinkProbe.budget_register_section_found ? "Sí" : "No"} ·
                            Duración: {(contractAvailabilityLinkProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          {contractAvailabilityLinkProbe.contract_saved_confirmed ? (
                            <Typography variant="caption" color="error">
                              El contrato ya quedó registrado. No repita este
                              flujo con el mismo número contractual.
                            </Typography>
                          ) : null}
                        </Stack>
                      </Alert>
                    )}


                    {contractBudgetRegisterLinkProbe && (
                      <Alert
                        severity={
                          contractBudgetRegisterLinkProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {contractBudgetRegisterLinkProbe.code}: {" "}
                            {contractBudgetRegisterLinkProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {contractBudgetRegisterLinkProbe.row_number} ·
                            Contrato: {contractBudgetRegisterLinkProbe.contract_number} ·
                            CDP: {contractBudgetRegisterLinkProbe.cdp_code} ·
                            RP: {contractBudgetRegisterLinkProbe.budget_register_number} ·
                            Total Bruto: {formatAmount(contractBudgetRegisterLinkProbe.gross_total)}
                          </Typography>
                          <Typography variant="caption">
                            Contrato guardado: {contractBudgetRegisterLinkProbe.contract_saved_confirmed ? "Sí" : "No"} ·
                            Supervisor vinculado: {contractBudgetRegisterLinkProbe.supervisor_linked_confirmed ? "Sí" : "No"} ·
                            CDP vinculado: {contractBudgetRegisterLinkProbe.availability_linked_row_confirmed ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            No. RP escrito: {contractBudgetRegisterLinkProbe.budget_register_number_written ? "Sí" : "No"} ·
                            Fecha RP: {contractBudgetRegisterLinkProbe.budget_register_date_provided
                              ? (contractBudgetRegisterLinkProbe.budget_register_date_written ? "Sí" : "No")
                              : "No suministrada"} ·
                            Disponibilidad seleccionada: {contractBudgetRegisterLinkProbe.budget_register_availability_selected ? "Sí" : "No"} ·
                            Total Bruto escrito: {contractBudgetRegisterLinkProbe.gross_total_written ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Validar RP pulsado: {contractBudgetRegisterLinkProbe.budget_register_validate_clicked ? "Sí" : "No"} ·
                            Vincular RP pulsado: {contractBudgetRegisterLinkProbe.budget_register_link_clicked ? "Sí" : "No"} ·
                            RP vinculado: {contractBudgetRegisterLinkProbe.budget_register_linked_confirmed ? "Sí" : "No"} ·
                            Fechas adicionales disponibles: {contractBudgetRegisterLinkProbe.additional_dates_section_found ? "Sí" : "No"} ·
                            Duración: {(contractBudgetRegisterLinkProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          {contractBudgetRegisterLinkProbe.contract_saved_confirmed ? (
                            <Typography variant="caption" color="error">
                              El contrato ya quedó registrado. No repita este
                              flujo con el mismo número contractual.
                            </Typography>
                          ) : null}
                        </Stack>
                      </Alert>
                    )}


                    {contractAdditionalDatesLinkProbe && (
                      <Alert
                        severity={
                          contractAdditionalDatesLinkProbe.success
                            ? "success"
                            : "warning"
                        }
                        variant="outlined"
                      >
                        <Stack spacing={0.5}>
                          <Typography variant="body2" fontWeight="bold">
                            {contractAdditionalDatesLinkProbe.code}: {" "}
                            {contractAdditionalDatesLinkProbe.message}
                          </Typography>
                          <Typography variant="caption">
                            Fila: {contractAdditionalDatesLinkProbe.row_number} ·
                            Contrato: {contractAdditionalDatesLinkProbe.contract_number} ·
                            CDP: {contractAdditionalDatesLinkProbe.cdp_code} ·
                            RP: {contractAdditionalDatesLinkProbe.budget_register_number}
                          </Typography>
                          <Typography variant="caption">
                            Contrato guardado: {contractAdditionalDatesLinkProbe.contract_saved_confirmed ? "Sí" : "No"} ·
                            Supervisor vinculado: {contractAdditionalDatesLinkProbe.supervisor_linked_confirmed ? "Sí" : "No"} ·
                            CDP vinculado: {contractAdditionalDatesLinkProbe.availability_linked_row_confirmed ? "Sí" : "No"} ·
                            RP vinculado: {contractAdditionalDatesLinkProbe.budget_register_linked_confirmed ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Garantía única: {contractAdditionalDatesLinkProbe.guarantee_approval_date_provided
                              ? (contractAdditionalDatesLinkProbe.guarantee_approval_date_written ? "Sí" : "No")
                              : "No suministrada"} ·
                            Página web: {contractAdditionalDatesLinkProbe.website_publication_date_provided
                              ? (contractAdditionalDatesLinkProbe.website_publication_date_written ? "Sí" : "No")
                              : "No suministrada"} ·
                            SECOP: {contractAdditionalDatesLinkProbe.secop_publication_date_provided
                              ? (contractAdditionalDatesLinkProbe.secop_publication_date_written ? "Sí" : "No")
                              : "No suministrada"}
                          </Typography>
                          <Typography variant="caption">
                            Fechas omitidas: {contractAdditionalDatesLinkProbe.additional_dates_skipped ? "Sí" : "No"} ·
                            Validar pulsado: {contractAdditionalDatesLinkProbe.additional_dates_validate_clicked ? "Sí" : "No"} ·
                            Vincular pulsado: {contractAdditionalDatesLinkProbe.additional_dates_link_clicked ? "Sí" : "No"} ·
                            Fechas vinculadas: {contractAdditionalDatesLinkProbe.additional_dates_linked_confirmed ? "Sí" : "No"}
                          </Typography>
                          <Typography variant="caption">
                            Archivos reportados disponible: {contractAdditionalDatesLinkProbe.file_reported_section_found ? "Sí" : "No"} ·
                            Duración: {(contractAdditionalDatesLinkProbe.duration_ms / 1000).toFixed(1)} s
                          </Typography>
                          {contractAdditionalDatesLinkProbe.contract_saved_confirmed ? (
                            <Typography variant="caption" color="error">
                              El contrato ya quedó registrado. No repita este
                              flujo con el mismo número contractual. Los adjuntos
                              permanecen fuera del alcance.
                            </Typography>
                          ) : null}
                        </Stack>
                      </Alert>
                    )}


                    {executionStatus && (
                      <Alert severity="info" variant="outlined">
                        Pendientes: {executionStatus.pending_count} · En proceso:{" "}
                        {executionStatus.processing_count} · Completados:{" "}
                        {executionStatus.completed_count} · Fallidos:{" "}
                        {executionStatus.failed_count} · Revisión manual:{" "}
                        {executionStatus.manual_review_count}
                      </Alert>
                    )}
                  </Stack>
                )}
              </Stack>
            ) : (
              <>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={2}
                  justifyContent="space-between"
                  alignItems={{ sm: "center" }}
                >
                  <Box>
                    <Typography fontWeight="bold">Validación registrada</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Identificador: {validation.validation_id}
                    </Typography>
                  </Box>
                  <Button
                    variant="contained"
                    onClick={createBatch}
                    disabled={
                      !validation.can_create_batch ||
                      selectedRows.size === 0 ||
                      creatingBatch
                    }
                    startIcon={
                      creatingBatch ? (
                        <CircularProgress size={18} color="inherit" />
                      ) : (
                        <PlaylistAddCheckIcon />
                      )
                    }
                    sx={{
                      backgroundColor: "#005026",
                      "&:hover": { backgroundColor: "#00441f" },
                    }}
                  >
                    {creatingBatch
                      ? "Creando lote…"
                      : `Crear lote (${selectedRows.size})`}
                  </Button>
                </Stack>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  mt={1.5}
                >
                  El servidor vuelve a verificar la validación y persiste únicamente
                  las filas válidas seleccionadas.
                </Typography>
              </>
            )}
          </Paper>
        </Stack>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar((current) => ({ ...current, open: false }))}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert severity={snackbar.severity} variant="filled">
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default Home;

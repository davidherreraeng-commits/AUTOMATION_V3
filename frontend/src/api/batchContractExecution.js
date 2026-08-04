import api from "./axiosConfig";
import {
  applyContractExecutionToBatch,
  canSubmitContractExecution,
  confirmationMatches,
  contractActionLabel,
  normalizeConfirmation,
} from "./batchContractExecutionUtils";

export {
  applyContractExecutionToBatch,
  canSubmitContractExecution,
  confirmationMatches,
  contractActionLabel,
  normalizeConfirmation,
};

const CONTRACT_EXECUTION_TIMEOUT_MS = 30 * 60 * 1000;

export async function getContractExecutionPreflight(
  batchId,
  itemId,
  mode = "DRY_RUN",
) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution/preflight`,
    { params: { mode } },
  );
  return response.data;
}

export async function getContractExecutionStatus(
  batchId,
  itemId,
  mode = "DRY_RUN",
) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution`,
    { params: { mode } },
  );
  return response.data;
}

export async function issueRealWriteAuthorization({
  batchId,
  itemId,
  confirmation,
}) {
  const response = await api.post(
    `/batches/${batchId}/contracts/${itemId}/execution/authorization`,
    { confirmation },
  );
  return response.data;
}

export async function getRealWriteAuthorization({
  batchId,
  itemId,
}) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution/authorization`,
  );
  return response.data;
}

export async function executeSelectedContract({
  batchId,
  itemId,
  confirmation,
  executionId = null,
  mode = "DRY_RUN",
  authorizationToken = null,
}) {
  const response = await api.post(
    `/batches/${batchId}/contracts/${itemId}/execution`,
    {
      confirmation,
      execution_id: executionId,
      mode,
      authorization_token: authorizationToken,
    },
    {
      timeout: CONTRACT_EXECUTION_TIMEOUT_MS,
    },
  );
  return response.data;
}

export async function getContractExecutionEvidence({
  batchId,
  itemId,
  correlationId,
}) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution/evidence/${correlationId}`,
  );
  return response.data;
}

export function extractExecutionApiError(error, fallback) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return {
      message: detail,
      code: null,
      technicalDetail: null,
      requiredConfirmation: null,
      issues: [],
    };
  }

  if (Array.isArray(detail)) {
    return {
      message:
        detail.map((item) => item?.msg).filter(Boolean).join(" ") || fallback,
      code: null,
      technicalDetail: null,
      requiredConfirmation: null,
      issues: [],
    };
  }

  if (detail && typeof detail === "object") {
    return {
      message: detail.message || fallback,
      code: detail.code || null,
      technicalDetail: detail.technical_detail || null,
      requiredConfirmation: detail.required_confirmation || null,
      issues: Array.isArray(detail.issues) ? detail.issues : [],
    };
  }

  return {
    message: fallback,
    code: null,
    technicalDetail: error?.message || null,
    requiredConfirmation: null,
    issues: [],
  };
}

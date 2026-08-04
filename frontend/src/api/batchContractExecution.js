import api from "./axiosConfig";
import {
  applyContractExecutionToBatch,
  confirmationMatches,
  contractActionLabel,
  normalizeConfirmation,
} from "./batchContractExecutionUtils";

export {
  applyContractExecutionToBatch,
  confirmationMatches,
  contractActionLabel,
  normalizeConfirmation,
};

const CONTRACT_EXECUTION_TIMEOUT_MS = 30 * 60 * 1000;

export async function getContractExecutionPreflight(batchId, itemId) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution/preflight`,
  );
  return response.data;
}

export async function getContractExecutionStatus(batchId, itemId) {
  const response = await api.get(
    `/batches/${batchId}/contracts/${itemId}/execution`,
  );
  return response.data;
}

export async function executeSelectedContract({
  batchId,
  itemId,
  confirmation,
  executionId = null,
}) {
  const response = await api.post(
    `/batches/${batchId}/contracts/${itemId}/execution`,
    {
      confirmation,
      execution_id: executionId,
    },
    {
      timeout: CONTRACT_EXECUTION_TIMEOUT_MS,
    },
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

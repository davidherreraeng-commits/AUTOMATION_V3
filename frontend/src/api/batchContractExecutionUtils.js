export function normalizeConfirmation(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ").toLocaleUpperCase("es-CO");
}

export function confirmationMatches(value, requiredConfirmation) {
  return normalizeConfirmation(value) === normalizeConfirmation(requiredConfirmation);
}

export function applyContractExecutionToBatch(batch, result) {
  if (!batch || !result) return batch;
  if (result.writes_to_portal === false || result.mode === "DRY_RUN") {
    return batch;
  }

  return {
    ...batch,
    status: result.batch_status ?? batch.status,
    contracts: (batch.contracts ?? []).map((item) =>
      item.item_id === result.item_id
        ? {
            ...item,
            status: result.item_status ?? item.status,
            last_message: result.operational_message ?? item.last_message,
          }
        : item,
    ),
  };
}

export function contractActionLabel(preflight, mode = "DRY_RUN") {
  if (!preflight) return mode === "DRY_RUN" ? "Comprobar simulación" : "Comprobar";
  if (!preflight.can_execute) return "Revisar bloqueos";
  if (mode === "DRY_RUN") return "Simular";
  return preflight.resumable ? "Reanudar" : "Ejecutar";
}

export function canSubmitContractExecution({
  preflight,
  mode = "DRY_RUN",
  confirmation,
  authorizationToken = null,
  authorizationExpiresAt = null,
  institutionalPlanId = null,
  now = Date.now(),
}) {
  if (!preflight?.can_execute) return false;
  if (
    !confirmationMatches(
      confirmation,
      preflight.required_confirmation,
    )
  ) {
    return false;
  }
  if (mode === "REAL") {
    if (!String(authorizationToken ?? "").trim()) {
      return false;
    }
    if (
      authorizationExpiresAt &&
      authorizationRemainingSeconds(authorizationExpiresAt, now) <= 0
    ) {
      return false;
    }
    if (!String(institutionalPlanId ?? "").trim()) {
      return false;
    }
    if (preflight.institutional_plan_ready !== true) {
      return false;
    }
  }
  return true;
}

export function authorizationRemainingSeconds(
  expiresAt,
  now = Date.now(),
) {
  if (!expiresAt) return 0;
  const expires = new Date(expiresAt).getTime();
  const current = now instanceof Date ? now.getTime() : Number(now);
  if (!Number.isFinite(expires) || !Number.isFinite(current)) return 0;
  return Math.max(0, Math.ceil((expires - current) / 1000));
}

export function formatAuthorizationCountdown(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(value / 60);
  const remainder = value % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export function findProcessingBatch(batches) {
  if (!Array.isArray(batches)) return null;
  return (
    batches.find((batch) => batch?.status === "PROCESSING") ?? null
  );
}

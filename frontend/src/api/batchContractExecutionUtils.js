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
  if (mode === "REAL" && !String(authorizationToken ?? "").trim()) {
    return false;
  }
  return true;
}

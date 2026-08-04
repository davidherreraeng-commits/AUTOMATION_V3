export function normalizeConfirmation(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ").toLocaleUpperCase("es-CO");
}

export function confirmationMatches(value, requiredConfirmation) {
  return normalizeConfirmation(value) === normalizeConfirmation(requiredConfirmation);
}

export function applyContractExecutionToBatch(batch, result) {
  if (!batch || !result) return batch;

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

export function contractActionLabel(preflight) {
  if (!preflight) return "Comprobar";
  if (!preflight.can_execute) return "Revisar bloqueos";
  return preflight.resumable ? "Reanudar" : "Ejecutar";
}

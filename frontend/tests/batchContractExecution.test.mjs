import test from "node:test";
import assert from "node:assert/strict";

import {
  applyContractExecutionToBatch,
  confirmationMatches,
  contractActionLabel,
  normalizeConfirmation,
} from "../src/api/batchContractExecutionUtils.js";

test("normaliza la confirmación sin alterar su identidad", () => {
  assert.equal(
    normalizeConfirmation("  ejecutar   contrato  70-2026 "),
    "EJECUTAR CONTRATO 70-2026",
  );
});

test("acepta la frase requerida ignorando mayúsculas y espacios repetidos", () => {
  assert.equal(
    confirmationMatches(
      "ejecutar   contrato 70-2026",
      "EJECUTAR CONTRATO 70-2026",
    ),
    true,
  );
});

test("no acepta una confirmación contractual diferente", () => {
  assert.equal(
    confirmationMatches(
      "EJECUTAR CONTRATO 71-2026",
      "EJECUTAR CONTRATO 70-2026",
    ),
    false,
  );
});

test("actualiza únicamente el contrato ejecutado dentro del lote", () => {
  const batch = {
    batch_id: "batch-1",
    status: "READY",
    contracts: [
      { item_id: "item-1", status: "PENDING", last_message: null },
      { item_id: "item-2", status: "PENDING", last_message: null },
    ],
  };

  const updated = applyContractExecutionToBatch(batch, {
    item_id: "item-2",
    batch_status: "PROCESSING",
    item_status: "COMPLETED",
    operational_message: "Contrato completado.",
  });

  assert.equal(updated.status, "PROCESSING");
  assert.deepEqual(updated.contracts[0], batch.contracts[0]);
  assert.equal(updated.contracts[1].status, "COMPLETED");
  assert.equal(updated.contracts[1].last_message, "Contrato completado.");
  assert.notEqual(updated, batch);
});

test("diferencia simulación, ejecución y reanudación", () => {
  assert.equal(
    contractActionLabel({ can_execute: true, resumable: false }, "DRY_RUN"),
    "Simular",
  );
  assert.equal(
    contractActionLabel({ can_execute: true, resumable: true }, "REAL"),
    "Reanudar",
  );
  assert.equal(
    contractActionLabel({ can_execute: true, resumable: false }, "REAL"),
    "Ejecutar",
  );
  assert.equal(
    contractActionLabel({ can_execute: false, resumable: false }, "DRY_RUN"),
    "Revisar bloqueos",
  );
  assert.equal(contractActionLabel(null, "DRY_RUN"), "Comprobar simulación");
});

test("la simulación no cambia el estado operativo del lote", () => {
  const batch = {
    batch_id: "batch-1",
    status: "READY",
    contracts: [
      { item_id: "item-1", status: "PENDING", last_message: null },
    ],
  };

  const updated = applyContractExecutionToBatch(batch, {
    mode: "DRY_RUN",
    writes_to_portal: false,
    item_id: "item-1",
    batch_status: "COMPLETED",
    item_status: "COMPLETED",
    operational_message: "Simulación completada.",
  });

  assert.equal(updated, batch);
  assert.equal(updated.status, "READY");
  assert.equal(updated.contracts[0].status, "PENDING");
});

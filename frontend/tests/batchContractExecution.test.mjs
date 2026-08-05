import test from "node:test";
import assert from "node:assert/strict";

import {
  applyContractExecutionToBatch,
  authorizationRemainingSeconds,
  canSubmitContractExecution,
  confirmationMatches,
  contractActionLabel,
  formatAuthorizationCountdown,
  findProcessingBatch,
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

test("la escritura real exige un token temporal en memoria", () => {
  const preflight = {
    can_execute: true,
    required_confirmation: "EJECUTAR CONTRATO 70-2026",
    institutional_plan_ready: true,
  };

  assert.equal(
    canSubmitContractExecution({
      preflight,
      mode: "REAL",
      confirmation: "EJECUTAR CONTRATO 70-2026",
      authorizationToken: null,
    }),
    false,
  );
  assert.equal(
    canSubmitContractExecution({
      preflight,
      mode: "REAL",
      confirmation: "EJECUTAR CONTRATO 70-2026",
      authorizationToken: "token-temporal",
      institutionalPlanId: "plan-1",
    }),
    true,
  );
});

test("la simulación no requiere autorización temporal", () => {
  assert.equal(
    canSubmitContractExecution({
      preflight: {
        can_execute: true,
        required_confirmation: "SIMULAR CONTRATO 70-2026",
      },
      mode: "DRY_RUN",
      confirmation: "simular contrato 70-2026",
    }),
    true,
  );
});

test("calcula y formatea el tiempo restante de la autorización", () => {
  const now = new Date("2026-08-04T18:00:00Z").getTime();
  assert.equal(
    authorizationRemainingSeconds(
      "2026-08-04T18:01:05Z",
      now,
    ),
    65,
  );
  assert.equal(formatAuthorizationCountdown(65), "01:05");
  assert.equal(
    authorizationRemainingSeconds(
      "2026-08-04T17:59:59Z",
      now,
    ),
    0,
  );
});

test("la escritura real rechaza un token vencido en memoria", () => {
  const preflight = {
    can_execute: true,
    required_confirmation: "EJECUTAR CONTRATO 70-2026",
    institutional_plan_ready: true,
  };
  const now = new Date("2026-08-04T18:00:00Z").getTime();

  assert.equal(
    canSubmitContractExecution({
      preflight,
      mode: "REAL",
      confirmation: "EJECUTAR CONTRATO 70-2026",
      authorizationToken: "token-temporal",
      authorizationExpiresAt: "2026-08-04T17:59:59Z",
      institutionalPlanId: "plan-1",
      now,
    }),
    false,
  );
  assert.equal(
    canSubmitContractExecution({
      preflight,
      mode: "REAL",
      confirmation: "EJECUTAR CONTRATO 70-2026",
      authorizationToken: "token-temporal",
      authorizationExpiresAt: "2026-08-04T18:00:30Z",
      institutionalPlanId: "plan-1",
      now,
    }),
    true,
  );
});


test("la escritura real exige un plan institucional armado", () => {
  const base = {
    can_execute: true,
    required_confirmation: "EJECUTAR CONTRATO 70-2026",
  };

  assert.equal(
    canSubmitContractExecution({
      preflight: {
        ...base,
        institutional_plan_ready: false,
      },
      mode: "REAL",
      confirmation: base.required_confirmation,
      authorizationToken: "token-temporal",
      institutionalPlanId: "plan-1",
    }),
    false,
  );

  assert.equal(
    canSubmitContractExecution({
      preflight: {
        ...base,
        institutional_plan_ready: true,
      },
      mode: "REAL",
      confirmation: base.required_confirmation,
      authorizationToken: "token-temporal",
      institutionalPlanId: null,
    }),
    false,
  );
});

test("un plan armado no habilita por sí solo la escritura real", () => {
  const plan = {
    status: "ARMED",
    arming_enabled: true,
    execution_enabled_by_plan: false,
  };

  assert.equal(plan.status, "ARMED");
  assert.equal(plan.execution_enabled_by_plan, false);
});

test("recupera únicamente el lote PROCESSING de la dependencia", () => {
  const active = findProcessingBatch([
    { batch_id: "ready-1", status: "READY" },
    { batch_id: "active-1", status: "PROCESSING" },
    { batch_id: "cancelled-1", status: "CANCELLED" },
  ]);

  assert.equal(active?.batch_id, "active-1");
  assert.equal(findProcessingBatch([]), null);
  assert.equal(findProcessingBatch(null), null);
});

test("la coincidencia de frase es independiente de los bloqueos operativos", () => {
  const preflight = {
    can_execute: false,
    required_confirmation: "EJECUTAR CONTRATO 70-2026",
  };

  assert.equal(
    confirmationMatches(
      "ejecutar contrato 70-2026",
      preflight.required_confirmation,
    ),
    true,
  );
  assert.equal(
    canSubmitContractExecution({
      preflight,
      mode: "REAL",
      confirmation: "EJECUTAR CONTRATO 70-2026",
      authorizationToken: "token",
      institutionalPlanId: "plan",
    }),
    false,
  );
});


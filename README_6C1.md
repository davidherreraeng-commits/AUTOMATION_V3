# Incremento 6C-1 — Control y preflight de ejecución de lotes

## Motivo del alcance

El baseline 6B-3 ya contiene:

- lotes persistidos en estado `READY`;
- checkpoints contractuales y `StepExecutor`;
- credenciales cifradas por dependencia;
- perfil de 118 localizadores C1–C9.

Sin embargo, los módulos concretos que deben operar cada pantalla de
Gestión Transparente todavía son placeholders vacíos. Por seguridad, este
incremento **no habilita escrituras reales en el portal**. Primero instala el
control de ejecución, el preflight, la exclusión por dependencia, los estados
persistentes y la interfaz de autorización. El runner Selenium real se conecta
en 6C-2.

## Funcionalidades

### Preflight

`GET /api/v1/batches/{batch_id}/execution/preflight`

Comprueba, antes de abrir cualquier navegador:

- que el usuario sea `SUPERUSER`;
- que el lote exista en su dependencia;
- que el lote esté en `READY`;
- que no exista otro lote `PROCESSING` en la dependencia;
- que la ejecución esté habilitada por configuración;
- que exista un runner disponible;
- que existan credenciales GT;
- que la última prueba de credenciales sea exitosa y reciente;
- que Fernet esté configurado;
- que no existan valores unitarios de prueba `$1`.

El endpoint retorna todas las condiciones bloqueantes, no solamente la primera.

### Control de ciclo de vida

- `POST /api/v1/batches/{batch_id}/execution`
- `GET /api/v1/batches/{batch_id}/execution`
- `POST /api/v1/batches/{batch_id}/cancel`

Se incorporan:

- transición atómica `READY -> PROCESSING`;
- índice SQLite parcial para impedir dos lotes `PROCESSING` por dependencia;
- progreso por contrato;
- mensajes de resultado por contrato;
- estados finales `COMPLETED`, `COMPLETED_WITH_ERRORS` y `FAILED`;
- cancelación únicamente desde `READY`;
- ejecución en un `ThreadPoolExecutor` inyectable y comprobable.

### Seguridad predeterminada

La configuración predeterminada es:

```env
RPA_BATCH_EXECUTION_ENABLED=false
RPA_BATCH_EXECUTION_CREDENTIAL_MAX_AGE_HOURS=24
RPA_BATCH_EXECUTION_REJECT_UNIT_TEST_VALUES=true
RPA_BATCH_EXECUTION_WORKERS=1
```

Aunque se cambie accidentalmente `RPA_BATCH_EXECUTION_ENABLED=true`, el runner
de producción de 6C-1 reporta `RUNNER_UNAVAILABLE`, por lo que no puede iniciar
Selenium ni modificar Gestión Transparente.

## Migración SQLite

Al iniciar FastAPI:

- se agrega `batch_contracts.last_message` cuando no existe;
- se crea un índice único parcial para un solo lote `PROCESSING` por dependencia.

No se requiere ejecutar SQL manual.

## Interfaz

Después de crear un lote, el superusuario puede:

- pulsar `Comprobar ejecución`;
- revisar todos los bloqueos;
- ejecutar solamente cuando `can_execute=true`;
- cancelar un lote `READY`;
- consultar el progreso cuando el lote esté `PROCESSING`.

Con el lote actual de valores `$1`, el preflight debe mostrar como mínimo:

- `EXECUTION_DISABLED`;
- `RUNNER_UNAVAILABLE`;
- `TEST_VALUES_DETECTED`.

## Pruebas nuevas

```powershell
python -m pytest `
  tests\unit\adapters\persistence\sqlite\test_batch_execution_repository.py `
  tests\unit\application\services\test_batch_execution_service.py `
  tests\integration\interfaces\api\test_batch_execution_routes.py `
  -v
```

Resultado esperado:

```text
14 passed
```

La suite completa esperada pasa de 249 a 263 pruebas.

## Límite deliberado

6C-1 no contiene el runner Selenium real. El siguiente incremento, 6C-2,
implementará y probará los componentes concretos C1–C9 antes de habilitar la
primera ejecución real.

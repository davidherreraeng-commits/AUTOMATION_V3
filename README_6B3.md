# Incremento 6B-3 — Persistencia y selección de lotes

## Alcance

Este incremento convierte una validación de Excel en un lote persistente, sin iniciar Selenium.

### Backend

- `POST /api/v1/batches`
  - Recibe `validation_id` y `selected_row_numbers`.
  - Recupera el Excel almacenado desde el servidor.
  - Vuelve a validar el archivo; no confía en los contratos enviados por el navegador.
  - Solo admite filas válidas y pertenecientes a la dependencia autenticada.
  - Persiste un snapshot completo de cada contrato seleccionado.
  - Impide crear dos lotes desde la misma validación y dependencia.
- `GET /api/v1/batches`
  - Lista los lotes de la dependencia autenticada.
- `GET /api/v1/batches/{batch_id}`
  - Consulta un lote de la dependencia autenticada.

### Persistencia

Al iniciar FastAPI se crean automáticamente las tablas:

- `contract_batches`
- `batch_contracts`

No se requiere ejecutar una migración manual. El estado inicial del lote es `READY`; los contratos quedan en `PENDING`.

### Frontend

- Selección individual de contratos válidos.
- Selección o deselección total.
- Contador de filas seleccionadas.
- Botón real `Crear lote`.
- Confirmación del identificador y estado del lote creado.
- Después de crear el lote, la selección queda bloqueada para evitar inconsistencias.

## Límites deliberados

- No abre Chrome.
- No usa las credenciales de Gestión Transparente.
- No inicia `StepExecutor`.
- No procesa el lote en segundo plano.
- No modifica el historial antiguo todavía.

## Pruebas

Pruebas específicas nuevas:

```powershell
python -m pytest `
  tests\unit\adapters\persistence\sqlite\test_batch_repository.py `
  tests\unit\application\services\test_batch_creation_service.py `
  tests\integration\interfaces\api\test_batch_routes.py `
  -v
```

Resultado esperado:

```text
14 passed
```

Suite completa esperada, partiendo de 229 pruebas:

```text
243 passed
```

## Validación funcional

1. Iniciar backend y frontend.
2. Cargar la plantilla Excel.
3. Validar el archivo.
4. Desmarcar uno o más contratos válidos, si corresponde.
5. Pulsar `Crear lote`.
6. Confirmar que aparece el identificador del lote y el estado `READY`.
7. Confirmar que Chrome no se abre.

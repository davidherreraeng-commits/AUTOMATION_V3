# Incremento 6C-3 — Diagnóstico seguro del formulario C1-C2

## Objetivo

Abrir el **Asistente de Contratación** desde un lote `READY` y confirmar
que la pantalla inicial C1-C2 conserva su estructura esperada.

Este incremento es diagnóstico y no ejecuta el lote.

## Endpoint nuevo

```text
POST /api/v1/batches/{batch_id}/execution/assistant-probe
```

Solo puede utilizarlo un superusuario.

## Controles verificados

Después de iniciar sesión y abrir el asistente se comprueban:

1. Contenedor del nuevo contrato.
2. Tipo de registro **Contrato**.
3. Campo **Número del contrato**.
4. Búsqueda de contratista.
5. Búsqueda de proyecto.
6. Botón **Validar**.

Para el radio de tipo de registro se comprueba presencia en el DOM, porque
Material UI puede mantener oculto el `input` nativo. Para los botones se
comprueba que sean interactivos.

## Acciones que NO realiza

- No escribe el número contractual.
- No cambia el tipo de registro.
- No abre la búsqueda de contratista.
- No abre la búsqueda de proyecto.
- No selecciona resultados.
- No pulsa `Validar`.
- No guarda información.
- No cambia el lote de `READY`.
- No requiere `RPA_BATCH_EXECUTION_ENABLED=true`.

Chrome se cierra automáticamente al finalizar.

## Respuestas funcionales

Resultado correcto:

```text
ASSISTANT_FORM_READY
```

Cuando el asistente abre pero falta algún control:

```text
ASSISTANT_FORM_INCOMPLETE
```

La respuesta incluye `missing_controls` con nombres seguros y legibles.

Otros códigos posibles:

```text
INVALID_CREDENTIALS
ASSISTANT_OPEN_TIMEOUT
ASSISTANT_FORM_TIMEOUT
BROWSER_UNAVAILABLE
BROWSER_BUSY
ASSISTANT_PROBE_ERROR
```

## Pruebas específicas

```powershell
python -m pytest `
  tests\unit\adapters\portal\gestion_transparente\test_batch_assistant_form_probe.py `
  tests\unit\application\services\test_batch_assistant_probe_service.py `
  tests\integration\interfaces\api\test_batch_assistant_probe_routes.py `
  -v
```

Resultado esperado:

```text
9 passed
```

## Suite completa

El baseline 6C-2 tiene 275 pruebas. Este incremento agrega 9:

```text
284 passed
```

## Prueba funcional

1. Mantenga `RPA_BATCH_EXECUTION_ENABLED=false`.
2. Inicie backend y frontend.
3. Utilice un lote `READY`.
4. Pulse **Probar formulario C1-C2**.
5. Chrome debe iniciar sesión, navegar y abrir el asistente.
6. No complete ni valide ningún campo manualmente.
7. Chrome debe cerrarse automáticamente.
8. La interfaz debe mostrar `ASSISTANT_FORM_READY`.
9. El lote debe continuar en estado `READY`.

El lote con valores de prueba `$1` puede usarse para este diagnóstico porque
no se envía ningún dato contractual.

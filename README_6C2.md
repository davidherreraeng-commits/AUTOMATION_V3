# Incremento 6C-2 — Prueba segura de acceso al portal

## Objetivo

Validar desde un lote `READY` que las credenciales cifradas permiten:

1. Iniciar sesión en Gestión Transparente.
2. Ubicar el menú **Contratación**.
3. Ubicar **Ingresar Contrato**.
4. Ubicar el acceso al **Asistente de Contratación**.

La prueba se detiene antes de abrir el formulario contractual. No escribe,
valida, guarda ni vincula información del contrato.

## Endpoint

```text
POST /api/v1/batches/{batch_id}/execution/probe
```

Solo está disponible para superusuarios y lotes `READY`.

## Seguridad

- La contraseña se descifra únicamente en memoria.
- La API no devuelve ni registra la contraseña.
- Exige que las credenciales tengan una prueba exitosa vigente.
- No cambia el estado del lote.
- No requiere `RPA_BATCH_EXECUTION_ENABLED=true`.
- El runner real continúa no disponible.
- Chrome se cierra automáticamente al terminar la comprobación.

## Configuración

Se agregan estas opciones:

```env
RPA_BATCH_EXECUTION_HEADLESS=false
RPA_BATCH_EXECUTION_TIMEOUT_SECONDS=25
```

Mantenga:

```env
RPA_BATCH_EXECUTION_ENABLED=false
```

## Pruebas específicas

```powershell
python -m pytest `
  tests\unit\application\services\test_batch_portal_probe_service.py `
  tests\integration\interfaces\api\test_batch_portal_probe_routes.py `
  -v
```

Resultado esperado:

```text
9 passed
```

## Suite completa

El baseline 6C-1 contiene 263 pruebas. Este incremento agrega 9:

```powershell
python -m pytest -v
```

Resultado esperado:

```text
272 passed
```

## Prueba funcional

1. Inicie backend y frontend.
2. Cree un lote `READY`.
3. Pulse **Probar acceso GT**.
4. Chrome debe iniciar sesión, expandir la navegación y cerrarse.
5. La interfaz debe mostrar `NAVIGATION_READY`.
6. El lote debe continuar en estado `READY`.
7. **Ejecutar lote** debe continuar deshabilitado por 6C-1.

# Incremento 6B-1 / 6B-2 — carga y validación de Excel

Este incremento conecta el lector de Excel y `ValidateBatch` existentes con FastAPI y React.

## Alcance

- `POST /api/v1/files/validate` protegido por sesión.
- Formatos permitidos: `.xlsx` y `.xlsm`.
- Límite predeterminado: 10 MB.
- Validación del contenedor Open XML antes de abrir el libro.
- Almacenamiento aislado por dependencia y por identificador de validación.
- La dependencia de la sesión prevalece sobre cualquier valor incluido en el Excel.
- Separación de filas válidas, inválidas y problemas globales del lote.
- Nueva pantalla de Inicio para seleccionar, validar y revisar resultados.
- No abre Selenium y no modifica Gestión Transparente.

El botón `Crear lote (6B-3)` queda deliberadamente deshabilitado hasta incorporar persistencia y ciclo de vida del lote.

## Configuración

Valores predeterminados:

```env
RPA_UPLOAD_DIRECTORY=data/uploads
RPA_UPLOAD_MAX_BYTES=10485760
RPA_DEFAULT_BUDGET_YEAR=2026
```

No es obligatorio agregarlos al `.env` cuando los valores predeterminados son adecuados.

## Dependencia nueva

```text
python-multipart>=0.0.9,<1
```

## Pruebas

```powershell
python -m pytest `
  tests\unit\adapters\input\excel\test_upload_validation.py `
  tests\integration\interfaces\api\test_file_routes.py `
  -v
```

Resultado esperado: `10 passed`.

La suite completa parte de 219 pruebas y debe finalizar con `229 passed`.

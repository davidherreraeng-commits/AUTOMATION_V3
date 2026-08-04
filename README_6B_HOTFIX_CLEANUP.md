# Hotfix 6B — limpieza segura de Excel inválidos en Windows

Corrige el bloqueo temporal de `contracts.xlsx` observado durante la validación estructural de un libro inválido.

Cambios:

- Cierre explícito del iterador usado para leer encabezados con openpyxl en modo `read_only`.
- Limpieza del directorio parcial con reintentos breves para bloqueos transitorios de Windows.
- La limpieza deja de ignorar silenciosamente errores del sistema de archivos.

No agrega dependencias ni cambia contratos válidos, rutas API o frontend.

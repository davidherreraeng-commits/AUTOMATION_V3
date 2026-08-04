# Incremento 6A-4 — Gestión institucional de usuarios

Este paquete agrega administración de cuentas desde React y FastAPI, sin usar PowerShell para la operación cotidiana.

## Funcionalidad incorporada

- Listado de usuarios limitado a la dependencia del superusuario autenticado.
- Creación de operadores y superusuarios.
- La dependencia se toma de la sesión; no se acepta desde el navegador.
- Activación y desactivación de cuentas.
- Protección contra la desactivación de la cuenta actual.
- Restablecimiento de contraseña temporal.
- Obligación de cambiar la contraseña temporal al iniciar sesión.
- Bloqueo de acceso a la administración para operadores.
- Ocultamiento de cuentas de otras dependencias.
- Página React de gestión de usuarios.
- Página React de cambio obligatorio de contraseña.

## Endpoints

```text
GET   /api/v1/users
POST  /api/v1/users
PATCH /api/v1/users/{user_id}/status
POST  /api/v1/users/{user_id}/reset-password
```

Todos exigen una sesión `SUPERUSER`. La dependencia siempre se deriva del usuario autenticado.

## 1. Detener temporalmente los servidores

En las terminales de Uvicorn y Vite pulse `Ctrl+C`. Esto evita que el recargador importe archivos mientras se están copiando.

## 2. Aplicar el incremento

Extraiga el ZIP fuera de `D:\automation_v2` y ejecute:

```powershell
Unblock-File .\apply_6a4.ps1
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\apply_6a4.ps1 -ProjectRoot "D:\automation_v2"
```

El script genera una copia de seguridad en:

```text
D:\automation_v2\artifacts\backups\6A4-users-<fecha>
```

No vuelva a ejecutar `apply_6a.ps1`.

## 3. Activar el entorno del backend

```powershell
cd D:\automation_v2
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& .\.venv\Scripts\Activate.ps1
```

Verificación:

```powershell
python -c "import sys; print(sys.executable)"
```

Debe apuntar a:

```text
D:\automation_v2\.venv\Scripts\python.exe
```

## 4. Compilar y probar

```powershell
python -m compileall `
  domain `
  application `
  adapters `
  interfaces
```

Pruebas del incremento:

```powershell
python -m pytest `
  tests\unit\adapters\persistence\sqlite\test_user_repository.py `
  tests\unit\application\services\test_user_management_service.py `
  tests\integration\interfaces\api\test_auth_routes.py `
  tests\integration\interfaces\api\test_user_routes.py `
  -v
```

Resultado esperado:

```text
14 passed
```

Suite completa:

```powershell
python -m pytest -v
```

Partiendo de las 197 pruebas aprobadas, el resultado esperado es:

```text
207 passed
```

## 5. Comprobar el frontend

No se requieren paquetes npm nuevos. Como `node_modules` ya existe:

```powershell
cd D:\automation_v2\frontend
npm run build
```

Después inicie Vite:

```powershell
npm run dev
```

## 6. Iniciar FastAPI

En otra terminal:

```powershell
cd D:\automation_v2
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& .\.venv\Scripts\Activate.ps1

python -m uvicorn interfaces.api.main:app `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

## 7. Prueba funcional recomendada

1. Inicie sesión con `carlos_herrera`.
2. Abra **Usuarios** en el menú lateral.
3. Cree un usuario operador con una contraseña temporal de al menos 8 caracteres.
4. Cierre la sesión.
5. Ingrese con el usuario nuevo y la contraseña temporal.
6. Confirme que el sistema obliga a abrir `/cambiar-contrasena`.
7. Defina una contraseña personal y confirme el acceso a `/inicio`.
8. Vuelva a entrar como superusuario.
9. Restablezca la contraseña del operador y compruebe el indicador de cambio pendiente.
10. Desactive el operador y compruebe que ya no puede iniciar sesión.

## Reglas de seguridad aplicadas

- Un superusuario solo administra cuentas de su propia dependencia.
- La dependencia enviada desde el frontend no se utiliza.
- Un operador recibe `403 Forbidden` en todos los endpoints de usuarios.
- La cuenta actual no puede desactivarse desde la pantalla administrativa.
- La contraseña temporal nunca se devuelve en respuestas ni se registra en logs.

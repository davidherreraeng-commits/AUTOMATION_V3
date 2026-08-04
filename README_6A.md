# Incremento 6A — Configuración central, autenticación y sesión web

Este paquete agrega a `automation_v2`:

- Configuración única mediante `pydantic-settings`.
- Base SQLite nueva para usuarios de la herramienta.
- Hash de contraseñas con `scrypt`.
- Compatibilidad temporal con hashes bcrypt heredados.
- Login único mediante FastAPI.
- JWT almacenado en cookie `HttpOnly`.
- Endpoints `login`, `me`, `logout` y cambio de contraseña.
- Contexto de autenticación React sin tokens en `localStorage`.
- Rutas privadas y autorización visual por rol.
- Navbar y Sidebar basados en la sesión real.
- Ocho pruebas nuevas.

## 1. Aplicar el paquete

Extraiga este ZIP fuera de `D:\automation_v2` y ejecute:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\apply_6a.ps1 -ProjectRoot "D:\automation_v2"
```

El script crea una copia de seguridad de cada archivo reemplazado en:

```text
D:\automation_v2\artifacts\backups\6A-auth-<fecha>
```

## 2. Instalar dependencias

```powershell
cd D:\automation_v2
python -m pip install -r requirements.6a.txt
```

`bcrypt` solo es necesario para validar usuarios migrados desde la versión anterior. Los hashes nuevos se almacenan con `scrypt`.

## 3. Configurar el entorno

```powershell
Copy-Item .env.example .env
```

Genere una clave aleatoria:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copie el resultado en:

```text
RPA_JWT_SECRET_KEY=...
```

No suba `.env` al repositorio.

## 4. Crear el primer superusuario

```powershell
python -m scripts.create_user `
  --username "carlos_herrera" `
  --dependency "Adquisiciones" `
  --role SUPERUSER
```

La contraseña se solicita sin mostrarla en pantalla.

### Migrar usuarios del backend anterior

```powershell
python -m scripts.migrate_legacy_users `
  "D:\ruta\backend_anterior\usuarios.db"
```

Los usuarios migrados conservan su hash bcrypt y quedan marcados para cambio de contraseña. En el primer inicio de sesión correcto, el hash se actualiza automáticamente a scrypt.

## 5. Ejecutar la API

```powershell
python -m uvicorn interfaces.api.main:app `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

Comprobación rápida:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Resultado esperado:

```json
{"status":"ok"}
```

## 6. Ejecutar el frontend

```powershell
cd D:\automation_v2\frontend
npm install
npm run dev
```

Vite enviará `/api/*` a `http://127.0.0.1:8000`. Esto permite que la cookie `HttpOnly` funcione sin almacenar el JWT en el navegador.

Abra:

```text
http://localhost:5173/login
```

## 7. Ejecutar pruebas

```powershell
cd D:\automation_v2
python -m compileall `
  domain application adapters infrastructure interfaces scripts

python -m pytest `
  tests\unit\infrastructure\security\test_scrypt_password_hasher.py `
  tests\unit\adapters\persistence\sqlite\test_user_repository.py `
  tests\unit\application\services\test_authentication_service.py `
  tests\integration\interfaces\api\test_auth_routes.py `
  -v
```

Resultado del paquete:

```text
8 passed
```

Después ejecute la suite completa:

```powershell
python -m pytest -v
```

Tomando como base las 189 pruebas existentes, el resultado esperado es:

```text
197 passed
```

## 8. Endpoints disponibles en este incremento

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/logout
POST /api/v1/auth/change-password
GET  /health
```

## 9. Alcance pendiente

Las páginas de carga, historial, errores, usuarios y credenciales todavía dependen de endpoints heredados o provisionales. Se migrarán en los siguientes incrementos:

- 6A-4: gestión de usuarios.
- 6A-5: credenciales cifradas de Gestión Transparente.
- 6B: carga, validación de Excel y lotes.

La identidad, el rol y la dependencia ya no deben tomarse de `localStorage`; se obtienen exclusivamente desde `/api/v1/auth/me`.

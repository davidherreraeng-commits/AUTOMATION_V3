from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.portal_credential_verifier import (
    PortalCredentialVerificationResult,
)
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app


VALID_HEADERS = [
    "No. de Contrato",
    "Dependencia",
    "Cédula o Nit Contratista",
    "Código del Proyecto",
    "Objeto del Contrato",
    "Fecha de Suscripción",
    "Fecha de Inicio",
    "Valor",
    "Plazo Estimado (En Dias)",
    "Modalidad o Proceso",
    "Procedimiento/Causal",
    "Tipo de Contrato",
    "Rubro Presupuestal",
    "Sub-Sector",
    "Enlace Proceso SECOP II",
    "Cédula Supervisor",
    "No. CDP",
    "No. RP",
    "Total Bruto",
]

VALID_ROW = [
    "70-2026",
    "Dependencia manipulada",
    "900469775-8",
    "I-23021-2026",
    "Servicio de software institucional.",
    "20/01/2026",
    "21/01/2026",
    "$ 1.476.190",
    180,
    "Contratación Directa",
    "Prestación de Servicios",
    "Servicios",
    "IDEA-2026 - RECURSOS CONVENIO IDEA",
    "Tecnología",
    "https://community.secop.gov.co/example",
    71693738,
    235097,
    950172,
    "$ 1.476.190",
]


class FakeVerifier:
    def verify(self, *, portal_username: str, portal_password: str):
        return PortalCredentialVerificationResult(
            success=True,
            code="AUTHENTICATED",
            message="Credenciales correctas.",
        )


def workbook_bytes(*, headers=None, rows=None) -> bytes:
    stream = BytesIO()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Contratos"
    worksheet.append(headers if headers is not None else VALID_HEADERS)
    for row in rows or []:
        worksheet.append(row)
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def build_settings(tmp_path: Path, *, max_size: int = 10_000_000) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        database_path=tmp_path / "api.sqlite3",
        upload_directory=tmp_path / "uploads",
        upload_max_bytes=max_size,
        default_budget_year=2026,
        jwt_secret_key=SecretStr(
            "test-secret-key-with-at-least-thirty-two-characters"
        ),
        fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),
        cookie_secure=False,
        cors_origins=["http://testserver"],
    )


def create_account(app, *, username: str, dependency: str) -> None:
    app.state.user_repository.create(
        username=username,
        password_hash=app.state.password_hasher.hash("Clave2026"),
        dependency=dependency,
        role=UserRole.OPERATOR,
    )


def login(client: TestClient, username: str) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Clave2026"},
    )
    assert response.status_code == 200


def test_authenticated_user_should_validate_excel_in_own_dependency(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
        )
        login(client, "operador")

        response = client.post(
            "/api/v1/files/validate",
            files={
                "file": (
                    "contratos.xlsx",
                    workbook_bytes(rows=[VALID_ROW]),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["dependency"] == "Adquisiciones"
        assert payload["valid_count"] == 1
        assert payload["invalid_count"] == 0
        assert payload["can_create_batch"] is True
        assert payload["valid_rows"][0]["dependency"] == "Adquisiciones"
        assert payload["valid_rows"][0]["process_type"] == (
            "Contratacion Directa"
        )
        assert payload["valid_rows"][0]["procedure"] == (
            "Prestación De Servicios Contratación Directa"
        )
        assert payload["valid_rows"][0]["contract_type"] == (
            "Contrato de Prestación de Servicios"
        )
        assert "stored_file_name" not in payload
        assert "file_path" not in payload


def test_should_require_authenticated_session(tmp_path: Path) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/files/validate",
            files={
                "file": (
                    "contratos.xlsx",
                    workbook_bytes(rows=[VALID_ROW]),
                )
            },
        )
        assert response.status_code == 401


def test_should_reject_unsupported_and_structurally_invalid_files(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
        )
        login(client, "operador")

        unsupported = client.post(
            "/api/v1/files/validate",
            files={"file": ("contratos.xls", b"legacy")},
        )
        assert unsupported.status_code == 400

        invalid_structure = client.post(
            "/api/v1/files/validate",
            files={
                "file": (
                    "contratos.xlsx",
                    workbook_bytes(headers=["Columna desconocida"]),
                )
            },
        )
        assert invalid_structure.status_code == 422


def test_should_reject_request_above_streaming_limit(tmp_path: Path) -> None:
    content = workbook_bytes(rows=[VALID_ROW])
    app = create_app(
        build_settings(tmp_path, max_size=len(content) - 1),
        portal_credential_verifier=FakeVerifier(),
    )

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
        )
        login(client, "operador")

        response = client.post(
            "/api/v1/files/validate",
            files={"file": ("contratos.xlsx", content)},
        )
        assert response.status_code == 413


def test_should_report_missing_secop_rp_and_gross_total_as_critical(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )

    invalid_row = list(VALID_ROW)
    invalid_row[14] = None  # Enlace Proceso SECOP II
    invalid_row[17] = None  # No. RP
    invalid_row[18] = None  # Total Bruto

    with TestClient(app) as client:
        create_account(
            app,
            username="operador",
            dependency="Adquisiciones",
        )
        login(client, "operador")

        response = client.post(
            "/api/v1/files/validate",
            files={
                "file": (
                    "contratos.xlsx",
                    workbook_bytes(rows=[invalid_row]),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid_count"] == 0
        assert payload["invalid_count"] == 1
        issues = payload["invalid_rows"][0]["issues"]
        assert {issue["field"] for issue in issues} == {
            "secop_url",
            "budget_register_number",
            "gross_total",
        }
        assert {issue["code"] for issue in issues} == {
            "MISSING_CRITICAL_FIELD"
        }

def test_should_reject_unknown_gt_catalog_value_before_batch_creation(
    tmp_path: Path,
) -> None:
    app = create_app(
        build_settings(tmp_path),
        portal_credential_verifier=FakeVerifier(),
    )
    invalid_row = list(VALID_ROW)
    invalid_row[10] = "Causal inexistente"

    with TestClient(app) as client:
        create_account(
            app,
            username="operador_catalogo",
            dependency="Adquisiciones",
        )
        login(client, "operador_catalogo")

        response = client.post(
            "/api/v1/files/validate",
            files={
                "file": (
                    "contratos.xlsx",
                    workbook_bytes(rows=[invalid_row]),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["valid_count"] == 0
        assert payload["invalid_count"] == 1
        assert payload["can_create_batch"] is False
        assert payload["invalid_rows"][0]["issues"][0]["code"] == (
            "PROCEDURE_CATALOG_VALUE_INVALID"
        )

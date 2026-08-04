from __future__ import annotations

from io import BytesIO
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pydantic import SecretStr

from application.ports.batch_portal_probe import BatchContractAvailabilityLinkProbeResult
from application.ports.portal_credential_verifier import PortalCredentialVerificationResult
from domain.enums.user_role import UserRole
from infrastructure.config.settings import Settings
from interfaces.api.main import create_app

HEADERS=["No. de Contrato","Cédula o Nit Contratista","Código del Proyecto","Objeto del Contrato","Fecha de Suscripción","Fecha de Inicio","Valor","Plazo Estimado (En Dias)","Modalidad o Proceso","Procedimiento/Causal","Tipo de Contrato","Rubro Presupuestal","Sub-Sector","Enlace Proceso SECOP II","Cédula Supervisor","No. CDP","No. RP","Total Bruto"]

class FakeVerifier:
    def verify(self, **kwargs): return PortalCredentialVerificationResult(success=True,code="AUTHENTICATED",message="OK")
class FakeProbe:
    name="fake-availability"
    def probe_contract_availability_link(self, **kwargs):
        return BatchContractAvailabilityLinkProbeResult(
            success=True,code="CONTRACT_AVAILABILITY_LINK_READY",message="Listo",
            authenticated=True,assistant_opened=True,contract_saved_confirmed=True,
            supervisor_linked_confirmed=True,availability_section_found=True,
            availability_search_written=True,availability_result_found=True,
            availability_result_matches=True,availability_link_clicked=True,
            availability_link_success_found=True,availability_linked_row_confirmed=True,
            continue_button_found=True,continue_clicked=True,budget_register_section_found=True,
        )

def settings(tmp_path):
    return Settings(_env_file=None,environment="test",database_path=tmp_path/"api.sqlite3",upload_directory=tmp_path/"uploads",jwt_secret_key=SecretStr("test-secret-key-with-at-least-thirty-two-characters"),fernet_key=SecretStr(Fernet.generate_key().decode("ascii")),cookie_secure=False,cors_origins=["http://testserver"],batch_execution_enabled=False)
def account(app,u,role): app.state.user_repository.create(username=u,password_hash=app.state.password_hasher.hash("Clave2026"),dependency="Adquisiciones",role=role)
def login(c,u): assert c.post("/api/v1/auth/login",json={"username":u,"password":"Clave2026"}).status_code==200
def workbook_bytes():
    b=BytesIO(); w=Workbook(); s=w.active; s.title="Contratos"; s.append(HEADERS); s.append(["86-2026","1042063697","I-23021-2026","Prueba","20/01/2026","21/01/2026","$ 1",30,"Contratación Directa","Prestación de Servicios","Servicios","IDEA-2026","Tecnología","https://secop.test","71693738","700","10","$ 1"]); w.save(b); w.close(); return b.getvalue()
def create_batch(c):
    v=c.post("/api/v1/files/validate",files={"file":("c.xlsx",workbook_bytes(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}); assert v.status_code==200
    r=c.post("/api/v1/batches",json={"validation_id":v.json()["validation_id"],"selected_row_numbers":[2]}); assert r.status_code==201; return r.json()
def creds(c):
    assert c.put("/api/v1/portal-credentials",json={"portal_username":"u","portal_password":"p"}).status_code==200
    assert c.post("/api/v1/portal-credentials/test").status_code==200

def test_superuser_should_link_cdp(tmp_path: Path):
    app=create_app(settings(tmp_path),portal_credential_verifier=FakeVerifier(),batch_portal_probe=FakeProbe())
    with TestClient(app) as c:
        account(app,"jefe",UserRole.SUPERUSER); login(c,"jefe"); creds(c); b=create_batch(c)
        r=c.post(f"/api/v1/batches/{b['batch_id']}/execution/contract-availability-link-probe",json={"item_id":b["contracts"][0]["item_id"],"confirmation":"GUARDAR SUPERVISOR Y CDP 86-2026","allow_test_values":True})
        assert r.status_code==200; p=r.json(); assert p["code"]=="CONTRACT_AVAILABILITY_LINK_READY"; assert p["cdp_code"]=="700"; assert p["budget_register_section_found"] is True

def test_should_reject_wrong_confirmation(tmp_path: Path):
    app=create_app(settings(tmp_path),portal_credential_verifier=FakeVerifier(),batch_portal_probe=FakeProbe())
    with TestClient(app) as c:
        account(app,"jefe",UserRole.SUPERUSER); login(c,"jefe"); creds(c); b=create_batch(c)
        r=c.post(f"/api/v1/batches/{b['batch_id']}/execution/contract-availability-link-probe",json={"item_id":b["contracts"][0]["item_id"],"confirmation":"GUARDAR 86-2026","allow_test_values":True})
        assert r.status_code==409

def test_operator_should_not_link_cdp(tmp_path: Path):
    app=create_app(settings(tmp_path),portal_credential_verifier=FakeVerifier(),batch_portal_probe=FakeProbe())
    with TestClient(app) as c:
        account(app,"operador",UserRole.OPERATOR); login(c,"operador"); b=create_batch(c)
        r=c.post(f"/api/v1/batches/{b['batch_id']}/execution/contract-availability-link-probe",json={"item_id":b["contracts"][0]["item_id"],"confirmation":"GUARDAR SUPERVISOR Y CDP 86-2026","allow_test_values":True})
        assert r.status_code==403

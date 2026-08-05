from __future__ import annotations

from uuid import UUID


class InstitutionalTestPlanError(RuntimeError):
    code = "INSTITUTIONAL_TEST_PLAN_ERROR"


class InstitutionalTestPlanRepositoryError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_REPOSITORY_ERROR"


class InstitutionalTestPlanDisabledError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_DISABLED"

    def __init__(self) -> None:
        super().__init__(
            "La preparación de pruebas institucionales no está habilitada "
            "en el servidor."
        )


class InstitutionalTestPlanArmingDisabledError(
    InstitutionalTestPlanError
):
    code = "INSTITUTIONAL_TEST_PLAN_ARMING_DISABLED"

    def __init__(self) -> None:
        super().__init__(
            "El armado de planes institucionales está deshabilitado "
            "en el servidor."
        )


class InstitutionalTestPlanNotFoundError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_NOT_FOUND"

    def __init__(self) -> None:
        super().__init__(
            "No existe un plan institucional para el contrato solicitado."
        )


class InstitutionalTestPlanConfirmationError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_CONFIRMATION_REQUIRED"

    def __init__(self, required_confirmation: str) -> None:
        self.required_confirmation = required_confirmation
        super().__init__(
            "La confirmación del plan institucional no coincide."
        )


class InstitutionalTestPlanContextError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_CONTEXT_MISMATCH"

    def __init__(self) -> None:
        super().__init__(
            "El plan institucional no pertenece al usuario, dependencia, "
            "lote, ítem o contrato solicitado."
        )


class InstitutionalTestPlanExpiredError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_EXPIRED"

    def __init__(self, plan_id: UUID | None = None) -> None:
        self.plan_id = plan_id
        super().__init__(
            "La ventana del plan institucional venció."
        )


class InstitutionalTestPlanCancelledError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_CANCELLED"

    def __init__(self, plan_id: UUID | None = None) -> None:
        self.plan_id = plan_id
        super().__init__(
            "El plan institucional fue cancelado."
        )


class InstitutionalTestPlanConsumedError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_CONSUMED"

    def __init__(self, plan_id: UUID | None = None) -> None:
        self.plan_id = plan_id
        super().__init__(
            "El plan institucional ya fue consumido y no puede reutilizarse."
        )


class InstitutionalTestPlanDiagnosticRequiredError(
    InstitutionalTestPlanError
):
    code = "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            "El plan requiere un diagnóstico read-only exitoso del portal."
        )


class InstitutionalTestPlanDiagnosticExpiredError(
    InstitutionalTestPlanError
):
    code = "INSTITUTIONAL_TEST_PLAN_DIAGNOSTIC_EXPIRED"

    def __init__(self) -> None:
        super().__init__(
            "El diagnóstico read-only del portal perdió vigencia."
        )


class InstitutionalTestPlanNotArmedError(InstitutionalTestPlanError):
    code = "INSTITUTIONAL_TEST_PLAN_NOT_ARMED"

    def __init__(self) -> None:
        super().__init__(
            "El plan institucional debe estar armado antes de la escritura."
        )

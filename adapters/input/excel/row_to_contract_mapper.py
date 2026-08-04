from __future__ import annotations

from typing import Any, Callable, Mapping, TypeVar, cast

from application.dto import ContractImportResult, ImportIssue
from domain.enums import ContractorNature
from domain.models import (
    BudgetData,
    ContractData,
    ContractorData,
    SupervisorData,
)

from adapters.input.excel.columns import ContractField
from adapters.input.excel.errors import ValueNormalizationError
from adapters.input.excel.value_normalizer import ValueNormalizer


T = TypeVar("T")


class ContractRowMapper:
    """
    Convierte una fila con claves canónicas en un ContractData.

    Responsabilidades:

    - Normalizar cada valor al tipo esperado.
    - Inferir la naturaleza del contratista desde su documento.
    - Aplicar valores configurables del lote.
    - Acumular todos los errores detectados en la fila.
    - Construir entidades de dominio solamente si la fila es válida.

    Esta clase no conoce openpyxl, pandas ni Selenium.
    """

    def __init__(
        self,
        *,
        default_dependency: str | None,
        default_budget_year: int,
        force_default_dependency: bool = False,
        normalizer: type[ValueNormalizer] = ValueNormalizer,
    ) -> None:
        self._default_dependency = (
            str(default_dependency).strip()
            if default_dependency is not None
            else None
        )

        self._default_budget_year = int(default_budget_year)
        self._force_default_dependency = bool(force_default_dependency)
        self._normalizer = normalizer

        if self._default_budget_year < 2000:
            raise ValueError(
                "El año presupuestal predeterminado no es válido."
            )

    def map(
        self,
        *,
        row_number: int,
        canonical_row: Mapping[str, Any],
    ) -> ContractImportResult:
        """
        Convierte una fila canónica en un resultado de importación.

        No lanza por errores propios de una fila. En esos casos devuelve
        un ContractImportResult inválido con uno o más ImportIssue.
        """

        if row_number < 2:
            raise ValueError(
                "El número de fila debe ser igual o superior a 2."
            )

        raw_data = dict(canonical_row)
        issues: list[ImportIssue] = []

        contract_number = self._read(
            canonical_row,
            ContractField.CONTRACT_NUMBER,
            self._normalizer.to_text,
            issues,
        )

        dependency = self._read_dependency(
            canonical_row,
            issues,
        )

        contractor_document = self._read(
            canonical_row,
            ContractField.CONTRACTOR_DOCUMENT,
            self._normalizer.to_text,
            issues,
        )

        contractor_nature = self._infer_contractor_nature(
            contractor_document
        )

        project_code = self._read(
            canonical_row,
            ContractField.PROJECT_CODE,
            self._normalizer.to_text,
            issues,
        )

        object_description = self._read(
            canonical_row,
            ContractField.OBJECT_DESCRIPTION,
            self._normalizer.to_text,
            issues,
        )

        signing_date = self._read(
            canonical_row,
            ContractField.SIGNING_DATE,
            self._normalizer.to_date,
            issues,
        )

        starting_date = self._read(
            canonical_row,
            ContractField.STARTING_DATE,
            self._normalizer.to_date,
            issues,
        )

        amount = self._read(
            canonical_row,
            ContractField.AMOUNT,
            self._normalizer.to_decimal,
            issues,
        )

        term_days = self._read(
            canonical_row,
            ContractField.TERM_DAYS,
            self._normalizer.to_integer,
            issues,
        )

        process_type = self._read(
            canonical_row,
            ContractField.PROCESS_TYPE,
            self._normalizer.to_text,
            issues,
        )

        procedure = self._read(
            canonical_row,
            ContractField.PROCEDURE,
            self._normalizer.to_text,
            issues,
        )

        contract_type = self._read(
            canonical_row,
            ContractField.CONTRACT_TYPE,
            self._normalizer.to_text,
            issues,
        )

        budget_item = self._read(
            canonical_row,
            ContractField.BUDGET_ITEM,
            self._normalizer.to_text,
            issues,
        )

        budget_subsector = self._read(
            canonical_row,
            ContractField.BUDGET_SUBSECTOR,
            self._normalizer.to_text,
            issues,
        )

        supervisor_document = self._read(
            canonical_row,
            ContractField.SUPERVISOR_DOCUMENT,
            self._normalizer.to_text,
            issues,
        )

        # Regla administrativa: el interventor siempre es interno.
        # La columna del Excel se conserva solo por compatibilidad,
        # pero su contenido no modifica el valor institucional.
        supervisor_type = "Interno"

        cdp_code = self._read(
            canonical_row,
            ContractField.CDP_CODE,
            self._normalizer.to_text,
            issues,
        )

        budget_register_number = self._read(
            canonical_row,
            ContractField.BUDGET_REGISTER_NUMBER,
            self._normalizer.to_text,
            issues,
        )

        budget_register_date = self._read(
            canonical_row,
            ContractField.BUDGET_REGISTER_DATE,
            self._normalizer.to_date,
            issues,
            required=False,
        )

        gross_total = self._read(
            canonical_row,
            ContractField.GROSS_TOTAL,
            self._normalizer.to_decimal,
            issues,
        )

        secop_url = self._read(
            canonical_row,
            ContractField.SECOP_URL,
            self._normalizer.to_text,
            issues,
        )

        guarantee_approval_date = self._read(
            canonical_row,
            ContractField.GUARANTEE_APPROVAL_DATE,
            self._normalizer.to_date,
            issues,
            required=False,
        )

        website_publication_date = self._read(
            canonical_row,
            ContractField.WEBSITE_PUBLICATION_DATE,
            self._normalizer.to_date,
            issues,
            required=False,
        )

        secop_publication_date = self._read(
            canonical_row,
            ContractField.SECOP_PUBLICATION_DATE,
            self._normalizer.to_date,
            issues,
            required=False,
        )

        if issues:
            return ContractImportResult(
                row_number=row_number,
                contract=None,
                issues=tuple(issues),
                raw_data=raw_data,
            )

        try:
            contractor = ContractorData(
                document_number=cast(
                    str,
                    contractor_document,
                ),
                nature=cast(
                    ContractorNature,
                    contractor_nature,
                ),
            )

            supervisor = SupervisorData(
                document_number=cast(
                    str,
                    supervisor_document,
                ),
                supervisor_type=cast(
                    str | None,
                    supervisor_type,
                ),
            )

            budget = BudgetData(
                year=self._default_budget_year,
                item=cast(
                    str,
                    budget_item,
                ),
                subsector=cast(
                    str,
                    budget_subsector,
                ),
                cdp_code=cast(
                    str,
                    cdp_code,
                ),
                gross_total=cast(
                    Any,
                    gross_total,
                ),
                budget_register_number=cast(
                    str | None,
                    budget_register_number,
                ),
                budget_register_date=cast(
                    Any,
                    budget_register_date,
                ),
            )

            contract = ContractData(
                contract_number=cast(
                    str,
                    contract_number,
                ),
                dependency=cast(
                    str,
                    dependency,
                ),
                contractor=contractor,
                project_code=cast(
                    str,
                    project_code,
                ),
                object_description=cast(
                    str,
                    object_description,
                ),
                signing_date=cast(
                    Any,
                    signing_date,
                ),
                starting_date=cast(
                    Any,
                    starting_date,
                ),
                amount=cast(
                    Any,
                    amount,
                ),
                term_days=cast(
                    int,
                    term_days,
                ),
                process_type=cast(
                    str,
                    process_type,
                ),
                procedure=cast(
                    str,
                    procedure,
                ),
                contract_type=cast(
                    str,
                    contract_type,
                ),
                budget=budget,
                supervisor=supervisor,
                secop_url=cast(
                    str | None,
                    secop_url,
                ),
                guarantee_approval_date=cast(
                    Any,
                    guarantee_approval_date,
                ),
                website_publication_date=cast(
                    Any,
                    website_publication_date,
                ),
                secop_publication_date=cast(
                    Any,
                    secop_publication_date,
                ),
            )

        except ValueError as error:
            return ContractImportResult(
                row_number=row_number,
                contract=None,
                issues=(
                    ImportIssue(
                        code="DOMAIN_VALIDATION_ERROR",
                        message=str(error),
                    ),
                ),
                raw_data=raw_data,
            )

        return ContractImportResult(
            row_number=row_number,
            contract=contract,
            issues=(),
            raw_data=raw_data,
        )

    def _read(
        self,
        row: Mapping[str, Any],
        field: str,
        converter: Callable[..., T | None],
        issues: list[ImportIssue],
        *,
        required: bool = True,
    ) -> T | None:
        """
        Ejecuta un normalizador y convierte sus errores en ImportIssue.
        """

        raw_value = row.get(field)

        try:
            return converter(
                raw_value,
                field=field,
                required=required,
            )
        except ValueNormalizationError as error:
            issue_code = (
                "MISSING_CRITICAL_FIELD"
                if required and self._normalizer.is_missing(raw_value)
                else "INVALID_VALUE"
            )
            issues.append(
                ImportIssue(
                    code=issue_code,
                    message=error.reason,
                    field=error.field,
                    raw_value=error.raw_value,
                )
            )

            return None

    def _read_dependency(
        self,
        row: Mapping[str, Any],
        issues: list[ImportIssue],
    ) -> str | None:
        raw_dependency = (
            self._default_dependency
            if self._force_default_dependency
            else row.get(ContractField.DEPENDENCY)
        )

        if self._normalizer.is_missing(raw_dependency):
            raw_dependency = self._default_dependency

        try:
            return self._normalizer.to_text(
                raw_dependency,
                field=ContractField.DEPENDENCY,
                required=True,
            )
        except ValueNormalizationError as error:
            issues.append(
                ImportIssue(
                    code="MISSING_DEPENDENCY",
                    message=(
                        "La dependencia no está presente en el archivo "
                        "ni fue proporcionada al iniciar el lote."
                    ),
                    field=error.field,
                    raw_value=error.raw_value,
                )
            )

            return None

    @staticmethod
    def _infer_contractor_nature(
        contractor_document: str | None,
    ) -> ContractorNature | None:
        """
        Aplica la regla administrativa institucional.

        - Documento con guion: persona jurídica.
        - Documento sin guion: persona natural.

        La validación de obligatoriedad del documento ocurre antes de
        esta inferencia; por eso ``None`` solo se propaga para evitar
        agregar errores duplicados a la misma fila.
        """

        if contractor_document is None:
            return None

        return (
            ContractorNature.LEGAL_ENTITY
            if "-" in contractor_document
            else ContractorNature.NATURAL_PERSON
        )

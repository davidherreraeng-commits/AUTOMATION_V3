from __future__ import annotations

import re
from collections import defaultdict
from typing import TypeAlias

from application.dto import (
    BatchIssue,
    BatchValidationResult,
    ContractImportResult,
    ImportIssue,
)
from application.ports import ContractSource


ContractIdentity: TypeAlias = tuple[str, str]


class ValidateBatch:
    """
    Valida todos los contratos provenientes de una fuente.

    El caso de uso:

    1. Consume la fuente completa.
    2. Conserva los errores individuales de importación.
    3. Detecta contratos duplicados.
    4. Convierte todas las apariciones duplicadas en filas inválidas.
    5. Produce un resultado que permite decidir si se abre el navegador.

    No conoce Excel, openpyxl, Selenium ni persistencia.
    """

    def execute(
        self,
        source: ContractSource,
    ) -> BatchValidationResult:
        imported_results = tuple(source.read())

        if not imported_results:
            return BatchValidationResult(
                valid_rows=(),
                invalid_rows=(),
                batch_issues=(
                    BatchIssue(
                        code="EMPTY_BATCH",
                        message=(
                            "La fuente no contiene contratos para procesar."
                        ),
                    ),
                ),
            )

        initially_valid = [
            result
            for result in imported_results
            if result.is_valid
        ]

        invalid_results = [
            result
            for result in imported_results
            if result.is_invalid
        ]

        grouped_contracts = self._group_by_identity(
            initially_valid
        )

        duplicated_groups = {
            identity: results
            for identity, results in grouped_contracts.items()
            if len(results) > 1
        }

        duplicated_row_numbers = {
            result.row_number
            for results in duplicated_groups.values()
            for result in results
        }

        final_valid_results = [
            result
            for result in initially_valid
            if result.row_number not in duplicated_row_numbers
        ]

        duplicate_invalid_results = (
            self._build_duplicate_results(
                duplicated_groups
            )
        )

        invalid_results.extend(
            duplicate_invalid_results
        )

        batch_issues: list[BatchIssue] = []

        if duplicated_groups:
            batch_issues.append(
                self._build_duplicate_batch_issue(
                    duplicated_groups
                )
            )

        return BatchValidationResult(
            valid_rows=tuple(
                sorted(
                    final_valid_results,
                    key=lambda result: result.row_number,
                )
            ),
            invalid_rows=tuple(
                sorted(
                    invalid_results,
                    key=lambda result: result.row_number,
                )
            ),
            batch_issues=tuple(batch_issues),
        )

    def _group_by_identity(
        self,
        valid_results: list[ContractImportResult],
    ) -> dict[
        ContractIdentity,
        list[ContractImportResult],
    ]:
        grouped: dict[
            ContractIdentity,
            list[ContractImportResult],
        ] = defaultdict(list)

        for result in valid_results:
            contract = result.contract

            if contract is None:
                continue

            identity = self._build_identity(
                contract_number=contract.contract_number,
                dependency=contract.dependency,
            )

            grouped[identity].append(result)

        return dict(grouped)

    @staticmethod
    def _build_identity(
        *,
        contract_number: str,
        dependency: str,
    ) -> ContractIdentity:
        """
        Construye la identidad lógica de un contrato.

        La comparación:

        - Ignora mayúsculas y minúsculas.
        - Ignora espacios en el número del contrato.
        - Normaliza espacios repetidos en la dependencia.

        No elimina guiones, barras ni otros caracteres porque podrían
        formar parte válida del número institucional.
        """

        normalized_contract_number = re.sub(
            r"\s+",
            "",
            str(contract_number),
        ).casefold()

        normalized_dependency = " ".join(
            str(dependency).split()
        ).casefold()

        return (
            normalized_dependency,
            normalized_contract_number,
        )

    def _build_duplicate_results(
        self,
        duplicated_groups: dict[
            ContractIdentity,
            list[ContractImportResult],
        ],
    ) -> list[ContractImportResult]:
        invalid_results: list[ContractImportResult] = []

        for results in duplicated_groups.values():
            row_numbers = tuple(
                sorted(
                    result.row_number
                    for result in results
                )
            )

            for result in results:
                contract = result.contract

                if contract is None:
                    continue

                invalid_results.append(
                    ContractImportResult(
                        row_number=result.row_number,
                        contract=None,
                        issues=(
                            ImportIssue(
                                code=(
                                    "DUPLICATE_CONTRACT_IN_BATCH"
                                ),
                                message=(
                                    "El contrato aparece más de una vez "
                                    "en el lote. Filas relacionadas: "
                                    + ", ".join(
                                        str(row_number)
                                        for row_number in row_numbers
                                    )
                                    + "."
                                ),
                                field="contract_number",
                                raw_value=(
                                    contract.contract_number
                                ),
                            ),
                        ),
                        raw_data=result.raw_data,
                    )
                )

        return invalid_results

    @staticmethod
    def _build_duplicate_batch_issue(
        duplicated_groups: dict[
            ContractIdentity,
            list[ContractImportResult],
        ],
    ) -> BatchIssue:
        duplicates_metadata: list[dict[str, object]] = []

        for results in duplicated_groups.values():
            first_contract = results[0].contract

            if first_contract is None:
                continue

            duplicates_metadata.append(
                {
                    "contract_number": (
                        first_contract.contract_number
                    ),
                    "dependency": (
                        first_contract.dependency
                    ),
                    "rows": tuple(
                        sorted(
                            result.row_number
                            for result in results
                        )
                    ),
                }
            )

        return BatchIssue(
            code="DUPLICATE_CONTRACTS_IN_BATCH",
            message=(
                "El lote contiene contratos duplicados. "
                "Debe corregirse el archivo antes de iniciar "
                "la automatización."
            ),
            metadata={
                "duplicates": tuple(
                    duplicates_metadata
                ),
            },
        )
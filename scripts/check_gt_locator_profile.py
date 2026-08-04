from __future__ import annotations

import argparse
import sys

from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import (
    Options,
)
from selenium.webdriver.chrome.service import (
    Service,
)
from selenium.webdriver.remote.webdriver import (
    WebDriver,
)
from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators.contract_tests import (
    InteractivePortalHealthCheckRunner,
)
from adapters.portal.gestion_transparente.locators.profiles.v2026_07 import (
    PROFILE_VERSION,
    V2026_07_HEALTH_CHECK_PHASES,
    build_registry,
)
from adapters.portal.gestion_transparente.selenium.diagnostics import (
    BrowserDiagnostics,
)
class PortalUnavailableError(RuntimeError):
    """
    El portal no está disponible y muestra una página de error
    en lugar de la aplicación esperada.
    """


SERVER_ERROR_MARKERS: tuple[str, ...] = (
    "502 bad gateway",
    "bad gateway",
    "503 service unavailable",
    "service unavailable",
    "504 gateway timeout",
    "gateway timeout",
    "internal server error",
    "error 502",
    "error 503",
    "error 504",
)


def read_browser_body(
    driver: WebDriver,
) -> str:
    """
    Obtiene de forma segura el texto visible de la página actual.
    """

    try:
        body = driver.find_element(
            By.TAG_NAME,
            "body",
        )

        return str(body.text).strip()

    except Exception:
        return ""


def validate_portal_availability(
    driver: WebDriver,
) -> None:
    """
    Impide ejecutar el diagnóstico cuando Chrome muestra una página
    de error del servidor en lugar del portal.
    """

    title = ""

    try:
        title = str(driver.title).strip()
    except Exception:
        pass

    body_text = read_browser_body(driver)

    diagnostic_text = (
        f"{title}\n{body_text}"
    ).casefold()

    detected_marker = next(
        (
            marker
            for marker in SERVER_ERROR_MARKERS
            if marker in diagnostic_text
        ),
        None,
    )

    if detected_marker is None:
        return

    current_url = ""

    try:
        current_url = str(
            driver.current_url
        ).strip()
    except Exception:
        pass

    raise PortalUnavailableError(
        "Gestión Transparente no está disponible. "
        f"Chrome detectó una página de error relacionada con "
        f"'{detected_marker}'. "
        f"URL actual: {current_url or 'desconocida'}. "
        "No se ejecutó la validación de localizadores."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Comprueba interactivamente los localizadores "
            "del perfil de Gestión Transparente."
        )
    )

    parser.add_argument(
        "--url",
        required=True,
        help=(
            "URL inicial de Gestión Transparente, normalmente "
            "la página de inicio de sesión."
        ),
    )

    parser.add_argument(
        "--output-directory",
        default=(
            "artifacts/portal-health-check"
        ),
        help=(
            "Directorio donde se escribirá el reporte JSON."
        ),
    )

    parser.add_argument(
        "--driver-path",
        default=None,
        help=(
            "Ruta opcional a chromedriver.exe. "
            "Cuando se omite, Selenium administra el driver."
        ),
    )

    parser.add_argument(
        "--capture-failed-evidence",
        action="store_true",
        help=(
            "Captura screenshot, HTML y metadatos cuando "
            "una fase contiene localizadores fallidos."
        ),
    )

    return parser.parse_args()


def build_driver(
    *,
    driver_path: str | None,
) -> WebDriver:
    options = Options()

    options.add_argument(
        "--start-maximized"
    )

    options.add_argument(
        "--disable-notifications"
    )

    options.add_argument(
        "--disable-popup-blocking"
    )

    if driver_path is None:
        return webdriver.Chrome(
            options=options
        )

    executable_path = Path(
        driver_path
    ).expanduser().resolve()

    if not executable_path.is_file():
        raise FileNotFoundError(
            "No se encontró chromedriver en: "
            f"{executable_path}"
        )

    service = Service(
        executable_path=str(
            executable_path
        )
    )

    return webdriver.Chrome(
        service=service,
        options=options,
    )


def build_report_path(
    output_directory: str | Path,
) -> Path:
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    directory = Path(
        output_directory
    )

    return (
        directory
        / (
            "gestion_transparente_"
            f"{PROFILE_VERSION}_"
            f"{timestamp}.json"
        )
    )


def print_final_summary(
    report,
    report_path: Path,
) -> None:
    print("")
    print("=== Resultado final ===")
    print(
        "Perfil: "
        f"{report.profile_version}"
    )
    print(
        "Fases verificadas: "
        f"{report.checked_phase_count}"
    )
    print(
        "Fases omitidas: "
        f"{report.skipped_phase_count}"
    )
    print(
        "Localizadores encontrados: "
        f"{report.found_count}"
    )
    print(
        "Localizadores ausentes: "
        f"{report.missing_count}"
    )
    print(
        "Errores de selector: "
        f"{report.error_count}"
    )
    print(
        "Fallbacks utilizados: "
        f"{len(report.fallback_keys)}"
    )
    print(
        "Diagnóstico completo: "
        f"{report.complete}"
    )
    print(
        "Perfil saludable: "
        f"{report.healthy}"
    )

    if report.failed_keys:
        print("")
        print("Claves fallidas:")

        for key in report.failed_keys:
            print(f"  - {key}")

    if report.skipped_keys:
        print("")
        print("Claves omitidas:")

        for key in report.skipped_keys:
            print(f"  - {key}")

    if report.unprocessed_keys:
        print("")
        print("Claves no procesadas:")

        for key in report.unprocessed_keys:
            print(f"  - {key}")

    print("")
    print(
        "Reporte JSON: "
        f"{report_path.resolve()}"
    )


def main() -> int:
    arguments = parse_arguments()

    report_path = build_report_path(
        arguments.output_directory
    )

    evidence_directory = (
        report_path.parent
        / "evidence"
    )

    driver: WebDriver | None = None

    try:
        print(
            "Iniciando Chrome para verificar "
            "Gestión Transparente..."
        )

        driver = build_driver(
            driver_path=arguments.driver_path
        )

        driver.set_page_load_timeout(60)
        driver.get(arguments.url)

        validate_portal_availability(
            driver
        )

        registry = build_registry()
        
        diagnostics = None

        if arguments.capture_failed_evidence:
            diagnostics = BrowserDiagnostics(
                driver,
                evidence_directory,
            )

        runner = (
            InteractivePortalHealthCheckRunner(
                driver=driver,
                registry=registry,
                profile_version=PROFILE_VERSION,
                phases=(
                    V2026_07_HEALTH_CHECK_PHASES
                ),
                diagnostics=diagnostics,
                capture_failed_evidence=(
                    arguments.capture_failed_evidence
                ),
            )
        )

        report = runner.run()

        written_path = report.write_json(
            report_path
        )

        print_final_summary(
            report,
            written_path,
        )

        return 0

    except KeyboardInterrupt:
        print("")
        print(
            "Verificación interrumpida desde el teclado."
        )
        return 130

    except Exception as error:
        print(
            "No fue posible ejecutar la verificación:",
            file=sys.stderr,
        )

        print(
            f"{type(error).__name__}: {error}",
            file=sys.stderr,
        )

        return 1

    finally:
        if driver is not None:
            input(
                "\nPresiona Enter para cerrar Chrome..."
            )

            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
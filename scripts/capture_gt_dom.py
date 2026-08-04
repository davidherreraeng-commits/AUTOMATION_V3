from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


DEFAULT_URL = (
    "https://rendicioncga.gestiontransparente.com/login/"
)


def sanitize_name(value: str) -> str:
    normalized = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip(),
    )

    normalized = normalized.strip("_")

    return normalized or "snapshot"


def utc_timestamp() -> str:
    return datetime.now(
        timezone.utc
    ).strftime("%Y%m%dT%H%M%S_%fZ")


def create_driver() -> WebDriver:
    options = webdriver.ChromeOptions()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    # Selenium Manager resolverá ChromeDriver.
    return webdriver.Chrome(options=options)


def get_document_metadata(
    driver: WebDriver,
) -> dict[str, Any]:
    return {
        "url": driver.current_url,
        "title": driver.title,
        "ready_state": driver.execute_script(
            "return document.readyState;"
        ),
        "document_width": driver.execute_script(
            """
            return Math.max(
                document.body?.scrollWidth || 0,
                document.documentElement?.scrollWidth || 0
            );
            """
        ),
        "document_height": driver.execute_script(
            """
            return Math.max(
                document.body?.scrollHeight || 0,
                document.documentElement?.scrollHeight || 0
            );
            """
        ),
        "frame_count": len(
            driver.find_elements(
                By.CSS_SELECTOR,
                "iframe, frame",
            )
        ),
    }


def capture_current_document(
    driver: WebDriver,
    destination: Path,
    errors: list[dict[str, Any]],
    frame_path: str = "top",
) -> None:
    destination.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        outer_html = driver.execute_script(
            """
            return document.documentElement
                ? document.documentElement.outerHTML
                : "";
            """
        )

        (destination / "dom.html").write_text(
            outer_html or "",
            encoding="utf-8",
        )
    except WebDriverException as exc:
        errors.append(
            {
                "frame": frame_path,
                "operation": "document.outerHTML",
                "error": str(exc),
            }
        )

    try:
        page_source = driver.page_source

        (destination / "page_source.html").write_text(
            page_source,
            encoding="utf-8",
        )
    except WebDriverException as exc:
        errors.append(
            {
                "frame": frame_path,
                "operation": "driver.page_source",
                "error": str(exc),
            }
        )

    try:
        visible_text = driver.execute_script(
            """
            return document.body
                ? document.body.innerText
                : "";
            """
        )

        (destination / "visible_text.txt").write_text(
            visible_text or "",
            encoding="utf-8",
        )
    except WebDriverException as exc:
        errors.append(
            {
                "frame": frame_path,
                "operation": "document.body.innerText",
                "error": str(exc),
            }
        )

    try:
        metadata = get_document_metadata(driver)

        (destination / "document_metadata.json").write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except WebDriverException as exc:
        errors.append(
            {
                "frame": frame_path,
                "operation": "document metadata",
                "error": str(exc),
            }
        )

    try:
        frame_count = len(
            driver.find_elements(
                By.CSS_SELECTOR,
                "iframe, frame",
            )
        )
    except WebDriverException as exc:
        errors.append(
            {
                "frame": frame_path,
                "operation": "list frames",
                "error": str(exc),
            }
        )
        return

    for index in range(frame_count):
        switched = False

        try:
            # Se vuelve a consultar la colección porque el DOM
            # puede cambiar al regresar de un iframe.
            frames = driver.find_elements(
                By.CSS_SELECTOR,
                "iframe, frame",
            )

            if index >= len(frames):
                errors.append(
                    {
                        "frame": frame_path,
                        "operation": "open child frame",
                        "index": index,
                        "error": (
                            "El frame dejó de existir antes "
                            "de poder capturarlo."
                        ),
                    }
                )
                continue

            driver.switch_to.frame(frames[index])
            switched = True

            child_destination = (
                destination
                / "frames"
                / f"frame_{index:02d}"
            )

            capture_current_document(
                driver=driver,
                destination=child_destination,
                errors=errors,
                frame_path=f"{frame_path}/frame_{index}",
            )
        except WebDriverException as exc:
            errors.append(
                {
                    "frame": frame_path,
                    "operation": "capture child frame",
                    "index": index,
                    "error": str(exc),
                }
            )
        finally:
            if switched:
                try:
                    driver.switch_to.parent_frame()
                except WebDriverException as exc:
                    errors.append(
                        {
                            "frame": frame_path,
                            "operation": "return to parent frame",
                            "index": index,
                            "error": str(exc),
                        }
                    )


def capture_snapshot(
    driver: WebDriver,
    output_root: Path,
    label: str,
) -> Path:
    timestamp = utc_timestamp()
    safe_label = sanitize_name(label)

    snapshot_directory = (
        output_root
        / f"{timestamp}_{safe_label}"
    )

    snapshot_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    errors: list[dict[str, Any]] = []

    try:
        driver.switch_to.default_content()
    except WebDriverException as exc:
        errors.append(
            {
                "operation": "switch to default content",
                "error": str(exc),
            }
        )

    try:
        driver.save_screenshot(
            str(snapshot_directory / "screenshot.png")
        )
    except WebDriverException as exc:
        errors.append(
            {
                "operation": "screenshot",
                "error": str(exc),
            }
        )

    capture_current_document(
        driver=driver,
        destination=snapshot_directory / "document",
        errors=errors,
    )

    metadata = {
        "captured_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "label": label,
        "url": driver.current_url,
        "title": driver.title,
        "errors": errors,
    }

    (snapshot_directory / "metadata.json").write_text(
        json.dumps(
            metadata,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return snapshot_directory


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Captura estados completos del DOM de "
            "Gestión Transparente."
        )
    )

    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="URL inicial de Gestión Transparente.",
    )

    parser.add_argument(
        "--output-dir",
        default="artifacts/dom-captures",
        help="Directorio donde se guardarán las capturas.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    output_root = Path(args.output_dir)
    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    driver = create_driver()

    try:
        driver.get(args.url)

        print()
        print("=== Capturador interactivo del DOM ===")
        print()
        print(
            "1. Inicia sesión y navega manualmente."
        )
        print(
            "2. Deja el portal exactamente en el estado "
            "que deseas capturar."
        )
        print(
            "3. Escribe una etiqueta y presiona Enter."
        )
        print(
            "4. Escribe Q para cerrar el navegador."
        )
        print()

        while True:
            label = input(
                "Etiqueta de captura [Q para finalizar]: "
            ).strip()

            if label.lower() == "q":
                break

            if not label:
                print(
                    "Debes escribir una etiqueta descriptiva."
                )
                continue

            try:
                snapshot_directory = capture_snapshot(
                    driver=driver,
                    output_root=output_root,
                    label=label,
                )

                print(
                    "Captura guardada en:"
                )
                print(
                    snapshot_directory.resolve()
                )
                print()
            except Exception as exc:
                print(
                    "No se pudo generar la captura:"
                )
                print(
                    f"{type(exc).__name__}: {exc}"
                )
                print()
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
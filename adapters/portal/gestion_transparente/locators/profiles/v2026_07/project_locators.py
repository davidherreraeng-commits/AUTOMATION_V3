<<<<<<< HEAD
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


PROJECT_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="project.dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//*[normalize-space()='Proyectos']]"
        ),
        priority=10,
        description="Diálogo específico de proyectos.",
    ),
    LocatorSpec(
        key="project.dialog",
        by=By.CSS_SELECTOR,
        value="[role='dialog'][aria-modal='true']",
        priority=20,
        description="Fallback para el diálogo modal.",
    ),
    LocatorSpec(
        key="project.code_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] input[name='projectId']"
        ),
        priority=10,
        description="Código exacto del proyecto.",
    ),
    LocatorSpec(
        key="project.search_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//button[normalize-space()='Buscar']"
        ),
        priority=10,
        description="Busca el proyecto.",
    ),
    LocatorSpec(
        key="project.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] [role='row'][data-id]"
        ),
        priority=10,
        description="Fila real de resultados de proyectos.",
    ),
    LocatorSpec(
        key="project.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] .MuiDataGrid-row[data-id]"
        ),
        priority=20,
        description="Fallback del DataGrid de proyectos.",
    ),
    LocatorSpec(
        key="project.confirm_button",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "[role='row'][data-id] "
            "button[title='Seleccionar']"
        ),
        priority=10,
        description="Selecciona el proyecto encontrado.",
    ),
    LocatorSpec(
        key="project.confirm_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//*[@role='row' and @data-id]"
            "//button[@title='Seleccionar']"
        ),
        priority=20,
        description="Fallback XPath de selección.",
    ),
=======
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


PROJECT_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="project.dialog",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "[.//*[normalize-space()='Proyectos']]"
        ),
        priority=10,
        description="Diálogo específico de proyectos.",
    ),
    LocatorSpec(
        key="project.dialog",
        by=By.CSS_SELECTOR,
        value="[role='dialog'][aria-modal='true']",
        priority=20,
        description="Fallback para el diálogo modal.",
    ),
    LocatorSpec(
        key="project.code_input",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] input[name='projectId']"
        ),
        priority=10,
        description="Código exacto del proyecto.",
    ),
    LocatorSpec(
        key="project.search_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//button[normalize-space()='Buscar']"
        ),
        priority=10,
        description="Busca el proyecto.",
    ),
    LocatorSpec(
        key="project.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] [role='row'][data-id]"
        ),
        priority=10,
        description="Fila real de resultados de proyectos.",
    ),
    LocatorSpec(
        key="project.result_row",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] .MuiDataGrid-row[data-id]"
        ),
        priority=20,
        description="Fallback del DataGrid de proyectos.",
    ),
    LocatorSpec(
        key="project.confirm_button",
        by=By.CSS_SELECTOR,
        value=(
            "[role='dialog'] "
            "[role='row'][data-id] "
            "button[title='Seleccionar']"
        ),
        priority=10,
        description="Selecciona el proyecto encontrado.",
    ),
    LocatorSpec(
        key="project.confirm_button",
        by=By.XPATH,
        value=(
            "//*[@role='dialog']"
            "//*[@role='row' and @data-id]"
            "//button[@title='Seleccionar']"
        ),
        priority=20,
        description="Fallback XPath de selección.",
    ),
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
)
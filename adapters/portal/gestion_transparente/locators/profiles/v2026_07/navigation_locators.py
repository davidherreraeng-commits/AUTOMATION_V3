<<<<<<< HEAD
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


NAVIGATION_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="portal.login.username",
        by=By.CSS_SELECTOR,
        value="input[name='usuario']",
        priority=10,
        description="Campo de usuario mediante name.",
    ),
    LocatorSpec(
        key="portal.login.username",
        by=By.XPATH,
        value=(
            "//label[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
            "'abcdefghijklmnopqrstuvwxyzáéíóú'),"
            "'usuario'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Campo de usuario mediante su etiqueta.",
    ),
    LocatorSpec(
        key="portal.login.password",
        by=By.CSS_SELECTOR,
        value="input[type='password']",
        priority=10,
        description="Campo de contraseña.",
    ),
    LocatorSpec(
        key="portal.login.submit",
        by=By.CSS_SELECTOR,
        value="button[type='submit']",
        priority=10,
        description="Botón principal de ingreso.",
    ),
    LocatorSpec(
        key="portal.login.submit",
        by=By.XPATH,
        value=(
            "//button[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'ingresar'"
            ")]"
        ),
        priority=20,
        description="Fallback mediante el texto Ingresar.",
    ),
    LocatorSpec(
        key="navigation.contracting_menu",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Contratación']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=10,
        description="Menú principal Contratación.",
    ),
    LocatorSpec(
        key="navigation.enter_contract",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Ingresar Contrato']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=10,
        description="Submenú Ingresar Contrato.",
    ),
    LocatorSpec(
        key="assistant.open",
        by=By.XPATH,
        value=(
            "//*[@role='button']"
            "[.//*[normalize-space()='Asistente de Contratación']]"
        ),
        priority=10,
        description="Acceso Material UI al asistente.",
    ),
    LocatorSpec(
        key="assistant.open",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Asistente de Contratación']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=20,
        description="Fallback desde el texto del asistente.",
    ),
    LocatorSpec(
        key="assistant.container",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'INFORMACIÓN GENERAL / NUEVO CONTRATO']"
        ),
        priority=10,
        description="Subtítulo exclusivo del nuevo contrato.",
    ),
    LocatorSpec(
        key="assistant.container",
        by=By.XPATH,
        value="//h5[normalize-space()='Contratación']",
        priority=20,
        description="Encabezado de la pantalla contractual.",
    ),
=======
from __future__ import annotations

from selenium.webdriver.common.by import By

from adapters.portal.gestion_transparente.locators import (
    LocatorSpec,
)


NAVIGATION_LOCATORS: tuple[LocatorSpec, ...] = (
    LocatorSpec(
        key="portal.login.username",
        by=By.CSS_SELECTOR,
        value="input[name='usuario']",
        priority=10,
        description="Campo de usuario mediante name.",
    ),
    LocatorSpec(
        key="portal.login.username",
        by=By.XPATH,
        value=(
            "//label[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚ',"
            "'abcdefghijklmnopqrstuvwxyzáéíóú'),"
            "'usuario'"
            ")]/following::input[1]"
        ),
        priority=20,
        description="Campo de usuario mediante su etiqueta.",
    ),
    LocatorSpec(
        key="portal.login.password",
        by=By.CSS_SELECTOR,
        value="input[type='password']",
        priority=10,
        description="Campo de contraseña.",
    ),
    LocatorSpec(
        key="portal.login.submit",
        by=By.CSS_SELECTOR,
        value="button[type='submit']",
        priority=10,
        description="Botón principal de ingreso.",
    ),
    LocatorSpec(
        key="portal.login.submit",
        by=By.XPATH,
        value=(
            "//button[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'ingresar'"
            ")]"
        ),
        priority=20,
        description="Fallback mediante el texto Ingresar.",
    ),
    LocatorSpec(
        key="navigation.contracting_menu",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Contratación']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=10,
        description="Menú principal Contratación.",
    ),
    LocatorSpec(
        key="navigation.enter_contract",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Ingresar Contrato']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=10,
        description="Submenú Ingresar Contrato.",
    ),
    LocatorSpec(
        key="assistant.open",
        by=By.XPATH,
        value=(
            "//*[@role='button']"
            "[.//*[normalize-space()='Asistente de Contratación']]"
        ),
        priority=10,
        description="Acceso Material UI al asistente.",
    ),
    LocatorSpec(
        key="assistant.open",
        by=By.XPATH,
        value=(
            "//*[normalize-space()='Asistente de Contratación']"
            "/ancestor::*[@role='button'][1]"
        ),
        priority=20,
        description="Fallback desde el texto del asistente.",
    ),
    LocatorSpec(
        key="assistant.container",
        by=By.XPATH,
        value=(
            "//p[normalize-space()="
            "'INFORMACIÓN GENERAL / NUEVO CONTRATO']"
        ),
        priority=10,
        description="Subtítulo exclusivo del nuevo contrato.",
    ),
    LocatorSpec(
        key="assistant.container",
        by=By.XPATH,
        value="//h5[normalize-space()='Contratación']",
        priority=20,
        description="Encabezado de la pantalla contractual.",
    ),
>>>>>>> a7ce04f247464ff73e13784380e29c4f979d817d
)
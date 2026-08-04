# Hotfix 6C-2 — navegación lateral consciente del estado

Corrige el probe que pulsaba siempre `Contratación` e `Ingresar Contrato`.
Gestión Transparente puede conservar esos menús abiertos; el clic ciego los
cerraba y provocaba `PORTAL_NAVIGATION_TIMEOUT`.

La corrección:

- comprueba primero si el siguiente nivel ya es visible;
- no pulsa menús ya desplegados;
- usa clic nativo, ActionChains y JavaScript como fallbacks;
- exige una postcondición visible después de cada clic;
- devuelve códigos de error específicos por nivel;
- sigue sin abrir el formulario ni modificar información.

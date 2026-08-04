# Hotfix 6C-2 — doble de prueba compatible con ActionChains

El test utilizaba `FakeElement`, pero `ActionChains.move_to_element()` acepta
únicamente instancias reales de `WebElement`. Por eso fallaba con
`AttributeError` antes de poder verificar el timeout específico.

La corrección sustituye `_perform_click` solamente dentro de esa prueba para
validar la orquestación de los tres modos de clic. No modifica el código
productivo del probe ni la navegación real en Gestión Transparente.

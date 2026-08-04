from __future__ import annotations


class BatchPortalProbeError(RuntimeError):
    """Error base de la comprobación segura del portal."""


class BatchPortalProbeBlockedError(BatchPortalProbeError):
    """El lote o las credenciales no cumplen condiciones para la prueba."""


class BatchPortalProbeConfigurationError(BatchPortalProbeError):
    """La infraestructura de cifrado o prueba no está disponible."""

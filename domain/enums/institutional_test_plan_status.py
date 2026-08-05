from __future__ import annotations

from enum import Enum


class InstitutionalTestPlanStatus(str, Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    ARMED = "ARMED"
    CONSUMED = "CONSUMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"

from interfaces.api.routes.batches import router as batches_router
from interfaces.api.routes.auth import router as auth_router
from interfaces.api.routes.files import router as files_router
from interfaces.api.routes.portal_credentials import (
    router as portal_credentials_router,
)
from interfaces.api.routes.users import router as users_router

__all__ = [
    "batches_router",
    "auth_router",
    "files_router",
    "portal_credentials_router",
    "users_router",
]

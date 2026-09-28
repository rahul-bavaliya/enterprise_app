from fastapi import APIRouter

from app.api.routes import (
    branches,
    customers,
    fleet,
    items,
    login,
    parts,
    private,
    users,
    utils,
    work_orders,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(branches.router)
api_router.include_router(work_orders.router)
api_router.include_router(parts.router)
api_router.include_router(customers.router)
api_router.include_router(fleet.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)

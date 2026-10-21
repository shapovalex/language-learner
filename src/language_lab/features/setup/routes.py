"""Setup's HTTP routes, under /api/setup."""

from fastapi import APIRouter

from language_lab.features.setup.service import Plan, Readiness, SetupService


def setup_router(service: SetupService) -> APIRouter:
    router = APIRouter(prefix="/api/setup")

    @router.get("/readiness")
    async def readiness() -> Readiness:
        return await service.readiness()

    @router.get("/plan")
    async def plan() -> Plan:
        return await service.plan()

    return router

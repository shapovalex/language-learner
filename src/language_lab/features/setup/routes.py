"""Setup's HTTP routes, under /api/setup."""

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, Field

from language_lab.features.setup.service import (
    ApplyResult,
    ApplyStatus,
    Plan,
    Readiness,
    SetupService,
)


class ApplyRequest(BaseModel):
    plan_hash: str = Field(alias="planHash")  # camelCase on the wire
    repairs: list[str] = []  # the checked opt-in repair rows' keys (entry 11)


def setup_router(service: SetupService) -> APIRouter:
    router = APIRouter(prefix="/api/setup")

    @router.get("/readiness")
    async def readiness() -> Readiness:
        return await service.readiness()

    @router.get("/plan")
    async def plan(repair: list[str] = Query([])) -> Plan:  # noqa: B008 -- FastAPI's idiom
        return await service.plan(repair)

    @router.post("/apply")
    async def apply(body: ApplyRequest) -> ApplyResult:
        return await service.apply(body.plan_hash, body.repairs)

    @router.get("/apply/status")
    async def apply_status() -> ApplyStatus:
        return service.apply_status()

    @router.post("/full-sync/uploaded", status_code=204)
    async def full_sync_uploaded() -> Response:
        service.full_sync_uploaded()
        return Response(status_code=204)

    return router

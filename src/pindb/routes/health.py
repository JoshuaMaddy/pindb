"""Liveness probe for container orchestration. No DB, no auth."""

from fastapi import APIRouter, Response

router = APIRouter(tags=["health"])


@router.get("/healthz", include_in_schema=False)
def healthz() -> Response:
    return Response(status_code=200, content="ok")

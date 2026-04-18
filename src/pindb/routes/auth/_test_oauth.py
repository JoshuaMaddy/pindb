"""Test-only OAuth provider used by the e2e / integration suites.

Gated by :data:`CONFIGURATION.allow_test_oauth_provider` — the router is
only mounted when this flag is set. MUST never be enabled in production.

Flow:
  1. The test harness POSTs JSON to ``/auth/_test-oauth/register`` with an
     ``identity_id`` and ``OAuthIdentity`` fields.
  2. ``GET /auth/_test-oauth/start?identity_id=X&link=0|1`` runs the same
     ``process_identity`` machinery a real OAuth callback would, so the
     login/link/onboarding branches are all exercised without touching a
     third-party provider.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import HTTPException, Request
from fastapi.responses import Response
from fastapi.routing import APIRouter

from pindb.auth import CurrentUser
from pindb.config import CONFIGURATION
from pindb.database.user_auth_provider import OAuthProvider
from pindb.routes.auth._oauth import OAuthIdentity

router = APIRouter(prefix="/auth/_test-oauth", tags=["auth-test"])

_REGISTERED: dict[str, OAuthIdentity] = {}


def register_identity(identity_id: str, identity: OAuthIdentity) -> None:
    _REGISTERED[identity_id] = identity


def consume_identity(identity_id: str) -> OAuthIdentity:
    try:
        return _REGISTERED[identity_id]
    except KeyError as exc:
        raise HTTPException(
            status_code=400, detail=f"Unknown test identity: {identity_id}"
        ) from exc


def _require_enabled() -> None:
    if not CONFIGURATION.allow_test_oauth_provider:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/register", response_model=None)
async def register(request: Request) -> dict[str, Any]:
    _require_enabled()
    body: dict[str, Any] = cast(dict[str, Any], await request.json())
    identity_id = str(body.pop("identity_id"))
    identity = OAuthIdentity(
        provider=OAuthProvider(body["provider"]),
        provider_user_id=str(body["provider_user_id"]),
        email=body.get("email"),
        email_verified=bool(body.get("email_verified", False)),
        username_hint=str(body.get("username_hint", "user")),
        provider_username=body.get("provider_username"),
    )
    register_identity(identity_id, identity)
    return {"identity_id": identity_id}


@router.get("/start", response_model=None)
def start(
    request: Request,
    current_user: CurrentUser,
    identity_id: str,
    link: int = 0,
) -> Response:
    _require_enabled()
    from pindb.routes.auth.router import process_identity

    identity = consume_identity(identity_id)
    return process_identity(
        request,
        identity,
        current_user,
        link_intent_override=bool(link) if link else None,
    )

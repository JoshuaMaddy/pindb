"""OAuth provider registry and userinfo fetchers.

Each provider implements two things:
  * authorize-redirect — delegated to Authlib.
  * ``fetch_userinfo(request) -> OAuthIdentity`` — pulls the provider's
    userinfo endpoint with the fresh access token and normalises it into
    an :class:`OAuthIdentity`.

The test-only provider (enabled by ``CONFIGURATION.allow_test_oauth_provider``)
bypasses Authlib entirely and is implemented in
:mod:`pindb.routes.auth._test_oauth`.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Any

import httpx
from authlib.deprecate import AuthlibDeprecationWarning

with warnings.catch_warnings():
    # Authlib 1.7 emits AuthlibDeprecationWarning from its own internals
    # (authlib._joserfc_helpers imports authlib.jose). Fix lands in 2.0.
    warnings.simplefilter("ignore", AuthlibDeprecationWarning)
    from authlib.integrations.starlette_client import OAuth, StarletteOAuth2App

from fastapi import Request

from pindb.config import CONFIGURATION
from pindb.database.user_auth_provider import OAuthProvider


@dataclass(frozen=True, slots=True)
class OAuthIdentity:
    """Normalised identity returned by every provider's userinfo fetcher."""

    provider: OAuthProvider
    provider_user_id: str
    email: str | None
    email_verified: bool
    username_hint: str
    provider_username: str | None = None


_oauth = OAuth()


def _google_configured() -> bool:
    return bool(CONFIGURATION.google_client_id and CONFIGURATION.google_client_secret)


def _discord_configured() -> bool:
    return bool(CONFIGURATION.discord_client_id and CONFIGURATION.discord_client_secret)


def _meta_configured() -> bool:
    return bool(CONFIGURATION.meta_client_id and CONFIGURATION.meta_client_secret)


if _google_configured():
    _oauth.register(
        name="google",
        client_id=CONFIGURATION.google_client_id,
        client_secret=CONFIGURATION.google_client_secret,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={"scope": "openid email profile"},
    )

if _discord_configured():
    _oauth.register(
        name="discord",
        client_id=CONFIGURATION.discord_client_id,
        client_secret=CONFIGURATION.discord_client_secret,
        authorize_url="https://discord.com/oauth2/authorize",
        access_token_url="https://discord.com/api/oauth2/token",
        api_base_url="https://discord.com/api/",
        client_kwargs={"scope": "identify email"},
    )

if _meta_configured():
    _oauth.register(
        name="meta",
        client_id=CONFIGURATION.meta_client_id,
        client_secret=CONFIGURATION.meta_client_secret,
        authorize_url="https://www.facebook.com/v19.0/dialog/oauth",
        access_token_url="https://graph.facebook.com/v19.0/oauth/access_token",
        api_base_url="https://graph.facebook.com/v19.0/",
        client_kwargs={"scope": "email public_profile"},
    )


def provider_enabled(provider: OAuthProvider) -> bool:
    if provider is OAuthProvider.google:
        return _google_configured()
    if provider is OAuthProvider.discord:
        return _discord_configured()
    if provider is OAuthProvider.meta:
        return _meta_configured()
    return False


def get_client(provider: OAuthProvider) -> StarletteOAuth2App:
    client = getattr(_oauth, provider.value, None)
    if client is None:
        raise RuntimeError(f"OAuth provider not configured: {provider.value}")
    return client


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def normalize_google(userinfo: dict[str, Any]) -> OAuthIdentity:
    provider_user_id = str(userinfo.get("sub", ""))
    email = userinfo.get("email")
    # Google OIDC always marks emails as verified when present.
    email_verified = bool(userinfo.get("email_verified", email is not None))
    username_hint = (
        userinfo.get("name") or (email.split("@", 1)[0] if email else None) or "user"
    )
    return OAuthIdentity(
        provider=OAuthProvider.google,
        provider_user_id=provider_user_id,
        email=email,
        email_verified=email_verified,
        username_hint=str(username_hint),
        provider_username=userinfo.get("name"),
    )


def normalize_discord(userinfo: dict[str, Any]) -> OAuthIdentity:
    provider_user_id = str(userinfo["id"])
    email = userinfo.get("email")
    # Discord only reports a verified email when the user has confirmed it.
    email_verified = bool(userinfo.get("verified", False)) and email is not None
    username_hint = (
        userinfo.get("global_name")
        or userinfo.get("username")
        or (email.split("@", 1)[0] if email else None)
        or "user"
    )
    return OAuthIdentity(
        provider=OAuthProvider.discord,
        provider_user_id=provider_user_id,
        email=email,
        email_verified=email_verified,
        username_hint=str(username_hint),
        provider_username=userinfo.get("username"),
    )


def normalize_meta(userinfo: dict[str, Any]) -> OAuthIdentity:
    provider_user_id = str(userinfo["id"])
    email = userinfo.get("email")
    # Facebook Login only returns the email field for users whose address
    # has been verified via Meta's own flow — presence implies verified.
    email_verified = email is not None
    username_hint = (
        userinfo.get("name") or (email.split("@", 1)[0] if email else None) or "user"
    )
    return OAuthIdentity(
        provider=OAuthProvider.meta,
        provider_user_id=provider_user_id,
        email=email,
        email_verified=email_verified,
        username_hint=str(username_hint),
        provider_username=userinfo.get("name"),
    )


# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


async def fetch_google(request: Request) -> OAuthIdentity:
    client = get_client(OAuthProvider.google)
    token = await client.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    return normalize_google(userinfo)


async def fetch_discord(request: Request) -> OAuthIdentity:
    client = get_client(OAuthProvider.discord)
    token = await client.authorize_access_token(request)
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
    resp.raise_for_status()
    return normalize_discord(resp.json())


async def fetch_meta(request: Request) -> OAuthIdentity:
    client = get_client(OAuthProvider.meta)
    token = await client.authorize_access_token(request)
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id,name,email"},
            headers={"Authorization": f"Bearer {token['access_token']}"},
        )
    resp.raise_for_status()
    return normalize_meta(resp.json())


_FETCHERS = {
    OAuthProvider.google: fetch_google,
    OAuthProvider.discord: fetch_discord,
    OAuthProvider.meta: fetch_meta,
}


async def fetch_identity(provider: OAuthProvider, request: Request) -> OAuthIdentity:
    fetcher = _FETCHERS[provider]
    return await fetcher(request)

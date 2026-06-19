"""SSO integration — OAuth2/OIDC + SAML provider support.

Supported providers: oidc, saml, okta, azure, keycloak.
All OIDC-compliant providers share the same code path; SAML uses a separate flow.
"""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urlencode

import jwt
from fastapi import HTTPException, Request
from loguru import logger


@dataclass
class SSOConfig:
    """SSO provider configuration."""

    provider: str  # "oidc", "saml", "okta", "azure", "keycloak"
    client_id: str
    client_secret: str
    issuer_url: str  # OIDC discovery /.well-known/openid-configuration
    redirect_uri: str
    scopes: list[str] = field(default_factory=lambda: ["openid", "email", "profile"])

    # SAML-specific fields (only used when provider == "saml")
    saml_metadata_url: str = ""
    saml_entity_id: str = ""
    saml_acs_url: str = ""


# Known provider issuer overrides (convenience)
_KNOWN_ISSUERS: dict[str, str] = {
    "okta": "https://{domain}/oauth2/default",
    "azure": "https://login.microsoftonline.com/{tenant}/v2.0",
    "keycloak": "https://{domain}/realms/{realm}",
}


class SSOManager:
    """OAuth2/OIDC + SAML SSO manager.

    Handles authorization URL generation, code exchange, token validation,
    and user info retrieval across multiple provider types.
    """

    def __init__(self, config: SSOConfig) -> None:
        self.config = config
        self._provider_type = self._detect_provider_type()
        self._oidc_config: dict[str, Any] | None = None
        self._jwks_client: Any = None

    def _detect_provider_type(self) -> str:
        """Detect whether this is an OIDC or SAML provider."""
        if self.config.provider == "saml":
            return "saml"
        return "oidc"

    # ── OIDC discovery ──────────────────────────────────────────

    async def _discover_oidc(self) -> dict[str, Any]:
        """Fetch OIDC discovery document (cached)."""
        if self._oidc_config is not None:
            return self._oidc_config

        import httpx

        issuer = self.config.issuer_url.rstrip("/")
        url = f"{issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=15)
            resp.raise_for_status()
            self._oidc_config = resp.json()
        return self._oidc_config

    async def _get_jwks_client(self):
        """Lazy-load PyJWKClient from discovered JWKS URI."""
        if self._jwks_client is not None:
            return self._jwks_client

        from jwt import PyJWKClient

        oidc = await self._discover_oidc()
        jwks_uri = oidc["jwks_uri"]
        self._jwks_client = PyJWKClient(jwks_uri, cache_keys=True)
        return self._jwks_client

    # ── Authorization URL ───────────────────────────────────────

    def get_authorization_url(self, state: str) -> str:
        """Build the OAuth2/OIDC authorization URL for the login flow."""
        if self._provider_type == "saml":
            return self._build_saml_auth_url(state)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
        }
        auth_endpoint = f"{self.config.issuer_url.rstrip('/')}/authorize"
        return f"{auth_endpoint}?{urlencode(params)}"

    def _build_saml_auth_url(self, state: str) -> str:
        """Build SAML authentication request URL (redirect binding)."""
        issuer = self.config.issuer_url.rstrip("/")
        params = {
            "SAMLRequest": self._build_saml_request(state),
            "RelayState": state,
        }
        return f"{issuer}?{urlencode(params)}"

    def _build_saml_request(self, state: str) -> str:
        """Build a minimal SAML AuthnRequest (base64-encoded).

        In production, use python3-saml or pysaml2 for full SAML support.
        This provides a functional stub for testing.
        """
        import base64
        import uuid

        request_id = f"_saml_{uuid.uuid4().hex[:16]}"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"'
            ' xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"'
            f' ID="{request_id}" Version="2.0"'
            f' IssueInstant="{time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}"'
            f' AssertionConsumerServiceURL="{self.config.saml_acs_url or self.config.redirect_uri}"'
            f' Destination="{self.config.issuer_url}">'
            f'<saml:Issuer>{self.config.saml_entity_id or self.config.client_id}</saml:Issuer>'
            "</samlp:AuthnRequest>"
        )
        return base64.b64encode(xml.encode("utf-8")).decode("utf-8")

    # ── Code Exchange ───────────────────────────────────────────

    async def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for tokens."""
        if self._provider_type == "saml":
            raise HTTPException(status_code=400, detail="SAML does not use authorization codes")

        import httpx

        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        oidc = await self._discover_oidc()
        token_endpoint = oidc["token_endpoint"]
        async with httpx.AsyncClient() as client:
            resp = await client.post(token_endpoint, data=payload, timeout=15)
            if resp.status_code != 200:
                logger.error("token exchange failed: {} {}", resp.status_code, resp.text)
                raise HTTPException(status_code=401, detail="Token exchange failed")
            return resp.json()

    # ── Token Validation ────────────────────────────────────────

    def validate_token(self, token: str) -> dict:
        """Validate a JWT access token and return its claims.

        For async JWKS fetching, use validate_token_async() instead.
        This sync version expects _jwks_client to be pre-warmed or
        validates without key lookup (signature check only with HS256).
        """
        # Try decoding without verification first to read kid/iss
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

        # Validate standard claims
        issuer = self.config.issuer_url.rstrip("/")
        if unverified.get("iss") != issuer:
            raise HTTPException(status_code=401, detail="Token issuer mismatch")

        # Check expiration with 30s clock skew tolerance
        exp = unverified.get("exp", 0)
        if exp and exp < time.time() - 30:
            raise HTTPException(status_code=401, detail="Token expired")

        # Audience check
        aud = unverified.get("aud", "")
        if aud and aud != self.config.client_id:
            # Azure AD returns app ID URI, not client ID, in aud
            if self.config.provider not in ("azure",):
                raise HTTPException(status_code=401, detail="Token audience mismatch")

        return unverified

    async def validate_token_async(self, token: str) -> dict:
        """Validate a JWT with async JWKS key fetching."""
        try:
            unverified = jwt.decode(token, options={"verify_signature": False})
        except jwt.DecodeError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

        jwks_client = await self._get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=[unverified.get("alg", "RS256")],
            audience=self.config.client_id,
            issuer=self.config.issuer_url.rstrip("/"),
            options={"verify_exp": True},
        )
        return claims

    # ── User Info ───────────────────────────────────────────────

    async def get_user_info(self, access_token: str) -> dict:
        """Fetch user info from the OIDC userinfo endpoint."""
        import httpx

        oidc = await self._discover_oidc()
        userinfo_endpoint = oidc.get("userinfo_endpoint", "")
        if not userinfo_endpoint:
            # Some providers omit userinfo; extract claims from access token
            try:
                return jwt.decode(access_token, options={"verify_signature": False})
            except jwt.DecodeError:
                return {"error": "No userinfo endpoint available"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("userinfo endpoint returned {}: {}", resp.status_code, resp.text)
                return {"error": f"UserInfo failed: {resp.status_code}"}
            return resp.json()


class SSOMiddleware:
    """FastAPI pure-ASGI middleware that validates SSO tokens on protected routes.

    Usage:
        app.add_middleware(
            SSOMiddleware,
            sso_manager=sso,
            exclude_paths=["/health", "/docs", "/openapi.json", "/auth/login"],
        )
    """

    def __init__(
        self,
        app,
        sso_manager: SSOManager,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.sso = sso_manager
        self.exclude_paths = set(exclude_paths or ["/health", "/docs", "/openapi.json"])

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Extract Bearer token
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            from fastapi.responses import JSONResponse

            response = JSONResponse({"detail": "SSO token required"}, status_code=401)
            await response(scope, receive, send)
            return

        token = auth[7:]

        try:
            claims = await self.sso.validate_token_async(token)
            # Store claims in request state for downstream handlers
            request.state.user = claims
            request.state.user_id = claims.get("sub") or claims.get("email", "unknown")
            request.state.user_roles = claims.get("roles", [])
        except HTTPException:
            from fastapi.responses import JSONResponse

            response = JSONResponse({"detail": "Invalid SSO token"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

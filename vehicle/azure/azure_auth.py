"""
Minimal Azure AD authentication middleware:
- Validates incoming Bearer JWT (if present / required)
- Attaches decoded token to request.state.user
- Skips auth gracefully if not configured (unless AZURE_AUTH_REQUIRED=true)
"""

import os
import logging
from typing import Optional, Dict, Any
from jwt import PyJWKClient
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class AzureADMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tenant_id: Optional[str] = None, client_id: Optional[str] = None, audience: Optional[str] = None):
        super().__init__(app)
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.audience = audience or os.getenv("AZURE_AUDIENCE", self.client_id)
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0" if self.tenant_id else None
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys" if self.tenant_id else None
        self.jwk_client = PyJWKClient(self.jwks_uri) if self.jwks_uri else None
        self.exclude_paths = [
            "/",
            "/health",
            "/api/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/api/dev/seed",
            "/api/dev/seed/bulk",
            "/api/dev/seed/status"
        ]
        if not (self.tenant_id and self.client_id):
            logger.warning("AzureADMiddleware: incomplete configuration; auth will be optional.")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.exclude_paths):
            return await call_next(request)

        # If not configured properly
        if not (self.tenant_id and self.client_id and self.issuer and self.jwks_uri):
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Azure AD auth not configured")
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Authorization header required")
            return await call_next(request)

        # Parse Bearer token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except ValueError:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid authorization header")
            return await call_next(request)

        decoded = await self._validate_token(token)
        if not decoded:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return await call_next(request)

        # Attach user to request
        request.state.user = decoded
        return await call_next(request)

    async def _validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.jwk_client:
                return None
            signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
            )
            return decoded
        except Exception as e:
            logger.debug(f"Token validation failed: {e}")
            return None

class AzureADBearer(HTTPBearer):
    """
    Optional per-route auth dependency.

    NOT required if global AzureADMiddleware + AZURE_AUTH_REQUIRED=true
    already protects all routes.

    Keep/use when you need:
      - Selective protection (set AZURE_AUTH_REQUIRED=false globally; add Depends(AzureADBearer()))
      - Easier unit tests (mock dependency instead of middleware)

    Returns decoded claims dict or raises (401/500) when auth is required;
    returns None in optional mode if token missing/invalid.

    Usage:
    Optional dependency usage:
        from .azure_auth import AzureADBearer
        get_user = AzureADBearer()
        @app.get("/secure")
        async def secure(user=Depends(get_user)):
            return {"user": user}
    Returns decoded token dict or raises if AZURE_AUTH_REQUIRED=true.
    """
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.audience = os.getenv("AZURE_AUDIENCE", self.client_id)
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0" if self.tenant_id else None
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys" if self.tenant_id else None
        self.jwk_client = PyJWKClient(self.jwks_uri) if self.jwks_uri else None

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Authorization required")
            return None
        if credentials.scheme.lower() != "bearer":
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid auth scheme")
            return None
        if not (self.tenant_id and self.client_id and self.issuer and self.jwks_uri and self.jwk_client):
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Azure AD auth not configured")
            return None
        token = credentials.credentials
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
            decoded = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
            )
            return decoded
        except Exception as e:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            logger.debug(f"Bearer validation failed (optional): {e}")
            return None
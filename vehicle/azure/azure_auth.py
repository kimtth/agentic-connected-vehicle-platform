"""
Minimal Azure AD authentication middleware:
- Only /api* routes are authenticated; all other paths skip auth entirely
- Validates incoming Bearer JWT (if present / required) for /api routes
- Attaches decoded token to request.state.user
- NEVER redirects - only returns JSON 401 for /api paths when auth fails
"""

import os
import logging
from typing import Optional
from jwt import PyJWKClient, ExpiredSignatureError
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class AzureADMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tenant_id: Optional[str] = None):
        super().__init__(app)
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"

        # Support both v1 and v2 issuers - ensure trailing slash for v1
        self.issuer_v2 = (
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            if self.tenant_id
            else None
        )
        # self.issuer_v1 = f"https://sts.windows.net/{self.tenant_id}/" if self.tenant_id else None

        # The common endpoint works for multi-tenant apps
        # The tenant-specific endpoint is https://login.microsoftonline.com/{tenant_id}/discovery/keys
        #  > Where can I find the JWKS Uri for Azure AD?
        #  > https://learn.microsoft.com/en-us/answers/questions/1163810/where-can-i-find-the-jwks-uri-for-azure-ad
        self.jwks_uri = "https://login.microsoftonline.com/common/discovery/keys"
        self.jwk_client = PyJWKClient(self.jwks_uri)
        # Accept Microsoft Graph audience (primary) + optional custom API audiences
        raw_audience = os.getenv("AZURE_CLIENT_ID")
        graph_api_audience = "00000003-0000-0000-c000-000000000000"  # Microsoft Graph

        if raw_audience:
            if raw_audience.startswith("api://"):
                guid = raw_audience.replace("api://", "")
                self.audiences = [raw_audience, graph_api_audience, guid]
            else:
                self.audiences = [
                    raw_audience,
                    f"api://{raw_audience}",
                    graph_api_audience,
                ]
        else:
            self.audiences = [graph_api_audience]

        logger.info(
            "AzureADMiddleware: configured with %d audience(s) - primary: %s",
            len(self.audiences),
            self.audiences[0] if self.audiences else "none",
        )

        self.exclude_exact = {
            "/",
            "/health",
            "/api/info",
            "/api/health",
            "/api/debug/cosmos",
            "/openapi.json",
            "/favicon.ico",
        }

        self.exclude_prefixes = (
            "/docs",
            "/static",
            "/redoc",
            "/api/dev/seed",  # includes /api/dev/seed, /bulk, /status, etc.
        )

        if not self.tenant_id:
            logger.warning(
                "AzureADMiddleware: incomplete configuration; auth will be optional."
            )

    def _attempt_token_retrieval(self, request: Request) -> Optional[str]:
        """
        Fallback token acquisition when Authorization header absent.
        Order:
          1. X-Auth-Token header (for legacy support)
          2. X-Authorization header (alternative header)
          3. access_token query parameter (for SSE/EventSource)
          4. Cookies: access_token, auth_token, token
          5. DEV_BEARER_TOKEN environment variable (dev only)
        Returns "Bearer <token>" or None.
        """
        # Check alternative headers first
        raw = request.headers.get("X-Auth-Token") or request.headers.get(
            "X-Authorization"
        )

        if not raw:
            # Check query parameters (for EventSource compatibility)
            raw = request.query_params.get("access_token")

        if not raw:
            # Check cookies
            raw = (
                request.cookies.get("access_token")
                or request.cookies.get("auth_token")
                or request.cookies.get("token")
            )

        if not raw:
            # Dev fallback: only if DEV_BEARER_TOKEN is explicitly set
            raw = os.getenv("DEV_BEARER_TOKEN")

        if raw:
            # Normalize to Bearer format
            raw = raw.strip()
            if raw.lower().startswith("bearer "):
                return raw
            return f"Bearer {raw}"

        return None

    def _get_signing_key(self, token: str) -> Optional[str]:
        """Get signing key from JWKS endpoint."""
        try:
            key_obj = self.jwk_client.get_signing_key_from_jwt(token)
            return key_obj.key
        except Exception as exc:
            if self.auth_required:
                logger.error(
                    "AzureADMiddleware: failed to get signing key from %s - %s",
                    self.jwks_uri,
                    str(exc),
                )
            return None

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        # API_TEST_MODE: skip all auth checks: DO NOT USE IN PRODUCTION
        if os.getenv("API_TEST_MODE") == "true":
            return await call_next(request)

        # All non-/api paths skip auth unconditionally (prevents 307 loops)
        if not path.startswith("/api"):
            return await call_next(request)

        # 1) CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Exact-path bypass (e.g. /api/health, /api/info, etc.)
        if path in self.exclude_exact:
            return await call_next(request)

        # Allow specific /api dev seed prefixes
        if any(
            path.startswith(p) for p in self.exclude_prefixes if p.startswith("/api/")
        ):
            return await call_next(request)

        # Config check
        if not (self.tenant_id and self.issuer_v2 and self.jwks_uri):
            if self.auth_required:
                return JSONResponse(
                    status_code=500, content={"detail": "Azure AD auth not configured"}
                )
            return await call_next(request)

        # Primary: check standard Authorization header
        auth_header = request.headers.get("Authorization") or request.headers.get(
            "authorization"
        )

        # Fallback: try alternative acquisition methods
        if not auth_header:
            auth_header = self._attempt_token_retrieval(request)

        if not auth_header:
            if self.auth_required:
                # ONLY JSON 401 for /api - never redirect
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Authorization required",
                        "hint": "Include Bearer token in Authorization header",
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # Optional mode: continue without auth
            return await call_next(request)

        # Parse Bearer token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except ValueError:
            if self.auth_required:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Invalid authorization header format",
                        "hint": "Use: Authorization: Bearer <token>",
                    },
                )
            return await call_next(request)

        # Validate token
        decoded = await self._validate_token(token)
        if not decoded:
            if self.auth_required:
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Invalid or expired token",
                        "hint": "Token validation failed - may be expired or have wrong audience/issuer",
                    },
                )
            return await call_next(request)

        # Attach user info to request state
        request.state.user = decoded

        return await call_next(request)

    async def _validate_token(self, token: str) -> Optional[dict]:
        try:
            # Decode without verification to inspect token claims
            try:
                unverified = jwt.decode(token, options={"verify_signature": False})
                token_iss = unverified.get("iss", "")
                token_aud = unverified.get("aud")
                token_ver = unverified.get("ver", "unknown")
            except Exception:
                return None

            # Get signing key
            signing_key = self._get_signing_key(token)
            if not signing_key:
                return None

            # Verify signature WITH proper issuer/audience validation
            # Try each valid issuer/audience combination until one succeeds
            last_error = None
            # for expected_issuer in [self.issuer_v1, self.issuer_v2]:
            for expected_issuer in [self.issuer_v2]:
                if not expected_issuer:
                    continue

                for audience in self.audiences:
                    try:
                        if expected_issuer == self.issuer_v2:
                            decode_options = {
                                "verify_aud": True,
                                "verify_iss": True,
                                "verify_exp": True,
                            }
                        # else:
                        # Microsoft Authentication Library (MSAL) for frontend always uses the v2.0 endpoint (https://login.microsoftonline.com/{tenant}/v2.0) under the hood.
                        # Therefore, This library can verify the token generated by MSAL with the v2.0 endpoint (expected_issuer).
                        # However, if you need to verify tokens issued by the v1.0 endpoint, you may need to disable some checks, or use legacy ADAL (Azure AD Authentication Library).
                        # decode_options = {
                        #     "verify_signature": False,
                        # }
                        decoded = jwt.decode(
                            token,
                            signing_key,
                            algorithms=["RS256"],
                            audience=audience,
                            issuer=expected_issuer,
                            options=decode_options,
                        )
                        # Success - return decoded token
                        logger.debug(
                            "AzureADMiddleware: token validated - issuer=%s audience=%s",
                            expected_issuer,
                            audience,
                        )
                        return decoded
                    except (jwt.InvalidAudienceError, jwt.InvalidIssuerError):
                        # Try next combination (expected for multi-audience setup)
                        continue
                    except ExpiredSignatureError:
                        # Token expired - don't try other combinations
                        logger.warning("AzureADMiddleware: token expired")
                        return None
                    except jwt.InvalidSignatureError as e:
                        # Signature error - only log once and stop trying
                        logger.error(
                            "AzureADMiddleware: signature verification failed - jwks_uri='%s' token_ver='%s' token_iss='%s' token_aud='%s'",
                            self.jwks_uri,
                            token_ver,
                            token_iss,
                            token_aud,
                        )
                        return None
                    except Exception as e:
                        # Capture last error for logging if all combinations fail
                        last_error = (expected_issuer, audience, e)
                        continue

            # No valid issuer/audience combination found - log details
            if last_error:
                exp_iss, exp_aud, exc = last_error
                logger.warning(
                    "AzureADMiddleware: no valid issuer/audience match - token_iss='%s' token_aud='%s' expected_audiences=%s error='%s'",
                    token_iss,
                    token_aud,
                    self.audiences,
                    str(exc),
                )

            return None

        except Exception as e:
            logger.error("AzureADMiddleware: validation failure: %s", str(e))
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
        from .azure_auth import AzureADBearer
        get_user = AzureADBearer()
        @app.get("/secure")
        async def secure(user=Depends(get_user)):
            return {"user": user}
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        # MSAL will use the v2.0 protocol under the hood. Therefore, This library can assume the frontend will use v2.0
        self.issuer_v2 = (
            f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            if self.tenant_id
            else None
        )
        self.issuer_v1 = (
            f"https://sts.windows.net/{self.tenant_id}/" if self.tenant_id else None
        )

        # Use /common/discovery/keys
        self.jwks_uri = "https://login.microsoftonline.com/common/discovery/keys"
        self.jwk_client = PyJWKClient(self.jwks_uri)

        # Accept Microsoft Graph audience (primary) + optional custom API audiences
        raw_audience = os.getenv("AZURE_CLIENT_ID")
        graph_api_audience = "00000003-0000-0000-c000-000000000000"  # Microsoft Graph

        if raw_audience:
            if raw_audience.startswith("api://"):
                guid = raw_audience.replace("api://", "")
                # Graph first, then custom API formats
                self.audiences = [graph_api_audience, raw_audience, guid]
            else:
                # Graph first, then GUID and api://GUID formats
                self.audiences = [
                    graph_api_audience,
                    raw_audience,
                    f"api://{raw_audience}",
                ]
        else:
            self.audiences = [graph_api_audience]

    def _get_signing_key(self, token: str) -> Optional[str]:
        """Get signing key from JWKS endpoint."""
        try:
            key_obj = self.jwk_client.get_signing_key_from_jwt(token)
            return key_obj.key
        except Exception as exc:
            if self.auth_required:
                logger.error(
                    "AzureADBearer: failed to get signing key from %s - %s",
                    self.jwks_uri,
                    str(exc),
                )
            return None

    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            if self.auth_required:
                raise HTTPException(
                    status_code=401,
                    detail="Authorization required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        if credentials.scheme.lower() != "bearer":
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid auth scheme")
            return None

        if not (
            self.tenant_id and self.issuer_v2 and self.jwks_uri and self.jwk_client
        ):
            if self.auth_required:
                raise HTTPException(
                    status_code=500, detail="Azure AD auth not configured"
                )
            return None

        token = credentials.credentials

        signing_key = self._get_signing_key(token)
        if not signing_key:
            if self.auth_required:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        try:
            # Try validation with each audience and both issuer formats
            for audience in self.audiences:
                try:
                    decoded = jwt.decode(
                        token,
                        signing_key,
                        algorithms=["RS256"],
                        audience=audience,
                        issuer=self.issuer_v2,
                        options={
                            "verify_aud": True,
                            "verify_iss": True,
                            "verify_exp": True,
                        },
                    )
                    return decoded
                except (jwt.InvalidAudienceError, jwt.InvalidIssuerError):
                    continue  # Try next combination

        except ExpiredSignatureError:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Token expired")
        except Exception:
            if self.auth_required:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return None

"""
Minimal Azure AD authentication middleware:
- Validates incoming Bearer JWT (if present / required)
- Attaches decoded token to request.state.user
- Skips auth gracefully if not configured (unless AZURE_AUTH_REQUIRED=true)
"""

import os
import logging
from typing import Optional
from jwt import PyJWKClient, ExpiredSignatureError
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, RedirectResponse

logger = logging.getLogger(__name__)

class AzureADMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, tenant_id: Optional[str] = None):
        super().__init__(app)
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        self.auth_debug = os.getenv("AZURE_AUTH_DEBUG", "false").lower() == "true"
        # Support both v1 and v2 issuers
        self.issuer_v2 = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0" if self.tenant_id else None
        self.issuer_v1 = f"https://sts.windows.net/{self.tenant_id}/" if self.tenant_id else None
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys" if self.tenant_id else None
        self.jwk_client = PyJWKClient(self.jwks_uri) if self.jwks_uri else None
        
        # Accept both GUID and api://GUID formats
        raw_audience = os.getenv("AZURE_CLIENT_ID")
        if raw_audience:
            # If it's api://GUID, extract just the GUID
            if raw_audience.startswith("api://"):
                guid = raw_audience.replace("api://", "")
                # Accept both formats
                self.audiences = [raw_audience, guid]
            else:
                # If it's just a GUID, accept both formats
                self.audiences = [raw_audience, f"api://{raw_audience}"]
        else:
            self.audiences = []
            
        self.exclude_exact = {
            # "/" removed so root path is authenticated
            "/health",
            "/api/info"
            "/api/health",
            "/openapi.json",
            "/favicon.ico",
        }
        self.exclude_prefixes = (
            "/docs",
            "/redoc",
            "/api/dev/seed"     # includes /api/dev/seed, /bulk, /status, etc.
        )

        if os.getenv('ENV_TYPE') == 'development':
            # Dev: In development, disable auth for all paths.
            self.exclude_prefixes = ("/",)

        self.signin_redirect_url = os.getenv("SIGNIN_REDIRECT_URL", "/")
        if not self.tenant_id:
            logger.warning("AzureADMiddleware: incomplete configuration; auth will be optional.")

    def _attempt_token_retrieval(self, request: Request) -> Optional[str]:
        """
        Fallback token acquisition when Authorization header absent.
        Order:
          1. X-Auth-Token header
          2. access_token query parameter
          3. Cookies: access_token, auth_token, token
          4. DEV_BEARER_TOKEN environment variable
        Returns "Bearer <token>" or None.
        """
        raw = (
            request.headers.get("X-Auth-Token")
            or request.query_params.get("access_token")
            or request.cookies.get("access_token")
            or request.cookies.get("auth_token")
            or request.cookies.get("token")
            or os.getenv("DEV_BEARER_TOKEN")
        )
        if raw:
            return f"Bearer {raw.strip()}"
        return None

    async def dispatch(self, request: Request, call_next):
        # Normalize and check exclusions safely
        path = request.url.path or "/"
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        # 1) Bypass CORS preflight early
        if request.method == "OPTIONS":
            return await call_next(request)

        # 2) Bypass excluded paths/prefixes
        if (path in self.exclude_exact) or any(path.startswith(p) for p in self.exclude_prefixes):
            return await call_next(request)

        # If not configured properly
        if not (self.tenant_id and self.issuer_v2 and self.jwks_uri):
            if self.auth_required:
                # Return JSONResponse to avoid exception bubbling in other middlewares
                return JSONResponse(status_code=500, content={"detail": "Azure AD auth not configured"})
            return await call_next(request)

        # Broaden header search (some proxies / libs might rename / downcase)
        auth_header = (
            request.headers.get("Authorization")
            or request.headers.get("authorization")
            or request.headers.get("X-Authorization")
            or request.headers.get("X-Auth-Token")  # direct header (before fallback)
        )
        if not auth_header:
            # Existing fallback (query, cookies, env, etc.)
            auth_header = self._attempt_token_retrieval(request)

        if self.auth_debug:
            logger.debug(
                "AzureADMiddleware: path=%s auth_present=%s incoming_headers=%s",
                request.url.path,
                bool(auth_header),
                {k: v for k, v in request.headers.items() if k.lower() in ("authorization","x-authorization","x-auth-token")}
            )

        if not auth_header:
            if self.auth_required:
                # API paths should return JSON 401, not redirect (for CORS compatibility)
                if path.startswith("/api"):
                    return JSONResponse(
                        status_code=401, 
                        content={"detail": "Authorization required"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                # Non-API paths can redirect to login
                return RedirectResponse(url=self.signin_redirect_url, status_code=307)
            return await call_next(request)

        # Parse Bearer token
        try:
            scheme, token = auth_header.split(" ", 1)
            if scheme.lower() != "bearer":
                raise ValueError("Invalid auth scheme")
        except ValueError:
            if self.auth_required:
                return JSONResponse(status_code=401, content={"detail": "Invalid authorization header"})
            return await call_next(request)

        decoded = await self._validate_token(token)
        if not decoded:
            if self.auth_required:
                return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})
            return await call_next(request)

        # Attach user to request
        request.state.user = decoded
        return await call_next(request)

    async def _validate_token(self, token: str) -> Optional[dict]:
        try:
            if not self.jwk_client:
                return None
            
            # Get signing key
            signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
            
            # Decode without verification to determine issuer version
            try:
                unverified = jwt.decode(token, options={"verify_signature": False})
                token_iss = unverified.get("iss", "")
            except Exception:
                return None
            
            # Select appropriate issuer based on token
            expected_issuer = self.issuer_v2 if "/v2.0" in token_iss else self.issuer_v1
            
            # Try validation with each valid audience
            for audience in self.audiences:
                try:
                    return jwt.decode(
                        token,
                        signing_key,
                        algorithms=["RS256"],
                        audience=audience,
                        issuer=expected_issuer,
                        options={"verify_aud": True, "verify_iss": True, "verify_exp": True},
                    )
                except jwt.InvalidAudienceError:
                    continue  # Try next audience
                except Exception as e:
                    if self.auth_debug:
                        logger.debug("AzureADMiddleware: token validation error for audience %s: %s", audience, e)
                    break
            
            return None
            
        except Exception as e:
            if self.auth_debug:
                logger.debug("AzureADMiddleware: general validation failure: %s", e)
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
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        self.issuer_v2 = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0" if self.tenant_id else None
        self.issuer_v1 = f"https://sts.windows.net/{self.tenant_id}/" if self.tenant_id else None
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys" if self.tenant_id else None
        self.jwk_client = PyJWKClient(self.jwks_uri) if self.jwks_uri else None
        
        # Accept both GUID and api://GUID formats
        raw_audience = os.getenv("AZURE_CLIENT_ID")
        if raw_audience:
            if raw_audience.startswith("api://"):
                guid = raw_audience.replace("api://", "")
                self.audiences = [raw_audience, guid]
            else:
                self.audiences = [raw_audience, f"api://{raw_audience}"]
        else:
            self.audiences = []

    async def __call__(self, request: Request) -> Optional[dict]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Authorization required")
            return None
            
        if credentials.scheme.lower() != "bearer":
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid auth scheme")
            return None
            
        if not (self.tenant_id and self.issuer_v2 and self.jwks_uri and self.jwk_client):
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Azure AD auth not configured")
            return None
        
        token = credentials.credentials
        
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token).key
            
            # Try validation with each audience (v2 issuer by default for bearer)
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
                except jwt.InvalidAudienceError:
                    continue  # Try next audience
                
        except ExpiredSignatureError:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Token expired")
        except Exception:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
        return None
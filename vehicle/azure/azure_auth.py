"""
Azure Active Directory authentication middleware for the connected vehicle platform.
"""

import os
import logging
import jwt
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import aiohttp
import json
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenCache:
    """Simple in-memory token cache for JWKS and validated tokens"""
    
    def __init__(self):
        self.jwks_cache = None
        self.jwks_cache_time = None
        self.jwks_cache_ttl = 3600  # 1 hour
        self.token_cache = {}
        self.token_cache_ttl = 300  # 5 minutes
    
    def get_jwks(self):
        """Get cached JWKS if valid"""
        if (self.jwks_cache and self.jwks_cache_time and 
            datetime.now() - self.jwks_cache_time < timedelta(seconds=self.jwks_cache_ttl)):
            return self.jwks_cache
        return None
    
    def set_jwks(self, jwks):
        """Cache JWKS"""
        self.jwks_cache = jwks
        self.jwks_cache_time = datetime.now()
    
    def get_token(self, token_hash: str):
        """Get cached token validation result"""
        cached = self.token_cache.get(token_hash)
        if cached and datetime.now() - cached['time'] < timedelta(seconds=self.token_cache_ttl):
            return cached['result']
        return None
    
    def set_token(self, token_hash: str, result: Dict):
        """Cache token validation result"""
        self.token_cache[token_hash] = {
            'result': result,
            'time': datetime.now()
        }
        
        # Clean old entries
        cutoff = datetime.now() - timedelta(seconds=self.token_cache_ttl)
        self.token_cache = {k: v for k, v in self.token_cache.items() if v['time'] > cutoff}

class AzureADMiddleware(BaseHTTPMiddleware):
    """Enhanced middleware for Azure AD authentication with caching and better error handling"""
    
    def __init__(self, app, tenant_id=None, client_id=None, audience=None):
        """Initialize the Azure AD middleware with enhanced configuration"""
        super().__init__(app)
        
        # Configuration with validation
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.audience = audience or os.getenv("AZURE_AUDIENCE", self.client_id)
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        
        # Validate configuration
        if not self._validate_config():
            logger.warning("Azure AD configuration incomplete - authentication will be optional")
        
        # Configure endpoints
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        
        # Initialize cache
        self.cache = TokenCache()
        
        # Paths that don't require authentication
        self.exclude_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        # Performance monitoring
        self.auth_metrics = {
            "total_requests": 0,
            "authenticated_requests": 0,
            "failed_authentications": 0,
            "cache_hits": 0
        }
        
        logger.info("Azure AD Middleware initialized with enhanced features")
    
    def _validate_config(self) -> bool:
        """Validate Azure AD configuration"""
        if not self.tenant_id:
            logger.warning("AZURE_TENANT_ID not configured")
            return False
        if not self.client_id:
            logger.warning("AZURE_CLIENT_ID not configured")
            return False
        return True
    
    async def _load_jwks(self) -> Optional[Dict]:
        """Load JWKS with caching and error handling"""
        # Check cache first
        cached_jwks = self.cache.get_jwks()
        if cached_jwks:
            return cached_jwks
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.jwks_uri) as response:
                    if response.status == 200:
                        jwks = await response.json()
                        self.cache.set_jwks(jwks)
                        logger.debug("JWKS loaded and cached successfully")
                        return jwks
                    else:
                        logger.error(f"Failed to load JWKS: HTTP {response.status}")
                        return None
        except asyncio.TimeoutError:
            logger.error("Timeout loading JWKS")
            return None
        except Exception as e:
            logger.error(f"Failed to load JWKS: {str(e)}")
            return None
    
    async def dispatch(self, request: Request, call_next):
        """Enhanced request processing with metrics and caching"""
        self.auth_metrics["total_requests"] += 1
        
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Skip authentication if not properly configured
        if not self._validate_config():
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Azure AD not properly configured")
            else:
                logger.debug("Azure AD not configured, skipping authentication")
                return await call_next(request)
        
        # Process authentication
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                if self.auth_required:
                    self.auth_metrics["failed_authentications"] += 1
                    raise HTTPException(status_code=401, detail="Authorization header required")
                else:
                    logger.debug("No authorization header, proceeding without authentication")
                    return await call_next(request)
            
            # Extract and validate token
            try:
                scheme, token = auth_header.split(" ", 1)
                if scheme.lower() != "bearer":
                    raise ValueError("Invalid scheme")
            except ValueError:
                self.auth_metrics["failed_authentications"] += 1
                if self.auth_required:
                    raise HTTPException(status_code=401, detail="Invalid authorization header format")
                else:
                    logger.warning("Invalid authorization header format, proceeding without authentication")
                    return await call_next(request)
            
            # Validate token with caching
            decoded_token = await self._validate_token_cached(token)
            if decoded_token:
                request.state.user = decoded_token
                self.auth_metrics["authenticated_requests"] += 1
                logger.debug(f"Authenticated user: {decoded_token.get('preferred_username', 'unknown')}")
            elif self.auth_required:
                self.auth_metrics["failed_authentications"] += 1
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            self.auth_metrics["failed_authentications"] += 1
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Authentication service error")
        
        return await call_next(request)
    
    async def _validate_token_cached(self, token: str) -> Optional[Dict]:
        """Validate token with caching for performance"""
        # Create a hash for caching (don't cache the actual token for security)
        token_hash = str(hash(token))
        
        # Check cache first
        cached_result = self.cache.get_token(token_hash)
        if cached_result is not None:
            self.auth_metrics["cache_hits"] += 1
            return cached_result
        
        # Validate token
        try:
            result = await self._validate_token(token)
            # Cache the result (but not sensitive data)
            cache_data = {
                'sub': result.get('sub'),
                'preferred_username': result.get('preferred_username'),
                'exp': result.get('exp')
            } if result else None
            
            self.cache.set_token(token_hash, cache_data)
            return result
        except Exception as e:
            logger.debug(f"Token validation failed: {str(e)}")
            self.cache.set_token(token_hash, None)
            return None
    
    async def _validate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token with proper error handling"""
        try:
            # Load JWKS
            jwks = await self._load_jwks()
            if not jwks:
                raise ValueError("Unable to load JWKS")
            
            # Decode token header
            try:
                header = jwt.get_unverified_header(token)
                kid = header.get("kid")
                if not kid:
                    raise ValueError("Token missing key ID")
            except jwt.DecodeError as e:
                raise ValueError(f"Invalid token format: {str(e)}")
            
            # Find matching key
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise ValueError(f"No matching key found for kid: {kid}")
            
            # Validate token with proper options
            decoded = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_signature": True
                }
            )
            
            return decoded
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidAudienceError:
            raise ValueError("Invalid token audience")
        except jwt.InvalidIssuerError:
            raise ValueError("Invalid token issuer")
        except jwt.InvalidSignatureError:
            raise ValueError("Invalid token signature")
        except Exception as e:
            raise ValueError(f"Token validation failed: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authentication metrics for monitoring"""
        total = self.auth_metrics["total_requests"]
        return {
            **self.auth_metrics,
            "success_rate": self.auth_metrics["authenticated_requests"] / total if total > 0 else 0,
            "cache_hit_rate": self.auth_metrics["cache_hits"] / total if total > 0 else 0
        }

class AzureADBearer(HTTPBearer):
    """Enhanced Bearer token validator for Azure AD with caching"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        
        # Use the same configuration validation as middleware
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.audience = os.getenv("AZURE_AUDIENCE", self.client_id)
        self.auth_required = os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true"
        
        if not all([self.tenant_id, self.client_id]):
            logger.warning("Azure AD Bearer: Configuration incomplete")
        
        # Initialize shared cache and middleware for consistency
        self.middleware = AzureADMiddleware(
            None, self.tenant_id, self.client_id, self.audience
        )
    
    async def __call__(self, request: Request) -> Optional[Dict]:
        """Process authentication request with enhanced error handling"""
        # Skip if not configured properly
        if not all([self.tenant_id, self.client_id]):
            if self.auth_required:
                raise HTTPException(status_code=500, detail="Azure AD not configured")
            return None
        
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if credentials.scheme != "Bearer":
                if self.auth_required:
                    raise HTTPException(status_code=401, detail="Invalid authentication scheme")
                return None
            
            # Use the middleware's validation logic for consistency
            decoded_token = await self.middleware._validate_token_cached(credentials.credentials)
            
            if decoded_token:
                return decoded_token
            elif self.auth_required:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            else:
                return None
        else:
            if self.auth_required:
                raise HTTPException(status_code=401, detail="Authentication required")
            return None

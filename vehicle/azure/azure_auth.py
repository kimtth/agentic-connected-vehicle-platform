"""
Azure Active Directory authentication middleware for the connected vehicle platform.
"""

import os
import logging
import jwt
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureADMiddleware(BaseHTTPMiddleware):
    """Middleware for Azure AD authentication"""
    
    def __init__(self, app, tenant_id=None, client_id=None, audience=None):
        """Initialize the Azure AD middleware"""
        super().__init__(app)
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.audience = audience or os.getenv("AZURE_AUDIENCE", self.client_id)
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        
        # Configure JWKS URI for token validation
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.jwks = None
        
        # Paths that don't require authentication
        self.exclude_paths = [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        
        # Load JWKS
        self._load_jwks()
        
        logger.info("Azure AD Middleware initialized")
    
    def _load_jwks(self):
        """Load the JSON Web Key Set for token validation"""
        try:
            response = requests.get(self.jwks_uri)
            response.raise_for_status()
            self.jwks = response.json()
            logger.info("JWKS loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load JWKS: {str(e)}")
            self.jwks = None
    
    async def dispatch(self, request: Request, call_next):
        """Process the request"""
        # Skip authentication for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Skip authentication if Azure AD is not configured
        if not all([self.tenant_id, self.client_id, self.jwks]):
            logger.warning("Azure AD not properly configured, skipping authentication")
            return await call_next(request)
        
        # Extract the token
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header missing")
            
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            
            # Validate the token
            try:
                decoded_token = self._validate_token(token)
                # Add the token claims to the request state
                request.state.user = decoded_token
            except Exception as e:
                logger.error(f"Token validation failed: {str(e)}")
                raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        except HTTPException as http_ex:
            if os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true":
                raise http_ex
            else:
                logger.warning(f"Authentication failed but AZURE_AUTH_REQUIRED=false: {str(http_ex.detail)}")
        
        # Continue processing the request
        return await call_next(request)
    
    def _validate_token(self, token):
        """Validate the JWT token"""
        if not self.jwks:
            raise ValueError("JWKS not loaded")
        
        # Decode the token header to get the key ID (kid)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        if not kid:
            raise ValueError("Token header does not contain a key ID (kid)")
        
        # Find the matching key in the JWKS
        key = None
        for jwk in self.jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        
        if not key:
            raise ValueError(f"No matching key found for kid: {kid}")
        
        # Validate the token
        decoded = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"verify_exp": True}
        )
        
        return decoded

class AzureADBearer(HTTPBearer):
    """Bearer token validator for Azure AD"""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.audience = os.getenv("AZURE_AUDIENCE", self.client_id)
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        
        # Configure JWKS URI for token validation
        self.jwks_uri = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        self.jwks = None
        
        # Load JWKS
        self._load_jwks()
    
    def _load_jwks(self):
        """Load the JSON Web Key Set for token validation"""
        try:
            response = requests.get(self.jwks_uri)
            response.raise_for_status()
            self.jwks = response.json()
        except Exception as e:
            logger.error(f"Failed to load JWKS: {str(e)}")
            self.jwks = None
    
    async def __call__(self, request: Request):
        """Process the request"""
        # Skip validation if Azure AD is not configured
        if not all([self.tenant_id, self.client_id, self.jwks]):
            logger.warning("Azure AD not properly configured, skipping authentication")
            return None
        
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme")
            
            # Validate the token
            try:
                decoded_token = self._validate_token(credentials.credentials)
                return decoded_token
            except Exception as e:
                logger.error(f"Token validation failed: {str(e)}")
                if os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true":
                    raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
                else:
                    logger.warning(f"Authentication failed but AZURE_AUTH_REQUIRED=false")
                    return None
        else:
            if os.getenv("AZURE_AUTH_REQUIRED", "false").lower() == "true":
                raise HTTPException(status_code=401, detail="Invalid token")
            else:
                logger.warning("No credentials provided but AZURE_AUTH_REQUIRED=false")
                return None
    
    def _validate_token(self, token):
        """Validate the JWT token"""
        if not self.jwks:
            raise ValueError("JWKS not loaded")
        
        # Decode the token header to get the key ID (kid)
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        if not kid:
            raise ValueError("Token header does not contain a key ID (kid)")
        
        # Find the matching key in the JWKS
        key = None
        for jwk in self.jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwk
                break
        
        if not key:
            raise ValueError(f"No matching key found for kid: {kid}")
        
        # Validate the token
        decoded = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
            options={"verify_exp": True}
        )
        
        return decoded

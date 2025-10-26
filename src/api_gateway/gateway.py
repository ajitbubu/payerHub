"""
API Gateway for PayerHub Integration
FastAPI-based gateway with rate limiting, authentication, and routing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import jwt

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models
class DocumentUpload(BaseModel):
    document_type: str = Field(..., description="Type of document (PRIOR_AUTH, ELIGIBILITY, etc.)")
    patient_id: str = Field(..., description="Patient identifier")
    organization_id: str = Field(..., description="Organization identifier")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")


class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ErrorResponse(BaseModel):
    error: str
    detail: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class FHIRResourceRequest(BaseModel):
    patient_id: str
    resource_type: str
    resource_data: Dict[str, Any]


# Initialize FastAPI app
app = FastAPI(
    title="PayerHub Integration API",
    description="Event-driven API for payer data integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security
security = HTTPBearer()

# Redis for caching and rate limiting
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)


class AuthManager:
    """Authentication and authorization manager"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.algorithm = "HS256"
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def create_token(self, user_id: str, organization_id: str, expires_delta: timedelta = None) -> str:
        """Create JWT token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        payload = {
            "sub": user_id,
            "org_id": organization_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)


# Initialize auth manager
auth_manager = AuthManager(secret_key="your-secret-key-here")  # Use environment variable in production


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    return auth_manager.verify_token(token)


class RateLimiter:
    """Custom rate limiter with Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def check_rate_limit(self, user_id: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if user has exceeded rate limit"""
        key = f"rate_limit:{user_id}"
        
        # Get current count
        count = self.redis.get(key)
        
        if count is None:
            # First request in window
            self.redis.setex(key, window, 1)
            return True
        
        count = int(count)
        if count >= limit:
            return False
        
        # Increment counter
        self.redis.incr(key)
        return True


rate_limiter = RateLimiter(redis_client)


# API Endpoints

@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "service": "PayerHub Integration API",
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    health_status = {
        "api": "healthy",
        "redis": "unknown",
        "kafka": "unknown",
        "database": "unknown"
    }
    
    # Check Redis
    try:
        redis_client.ping()
        health_status["redis"] = "healthy"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    return health_status


@app.post("/api/v1/auth/token", response_model=APIResponse, tags=["Authentication"])
async def create_auth_token(user_id: str, organization_id: str):
    """Generate authentication token"""
    try:
        token = auth_manager.create_token(user_id, organization_id)
        
        return APIResponse(
            success=True,
            message="Token created successfully",
            data={"token": token, "expires_in": "24h"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/upload", response_model=APIResponse, tags=["Documents"])
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    document_info: str = Header(..., description="JSON string of DocumentUpload"),
    current_user: Dict = Depends(get_current_user)
):
    """
    Upload document for processing
    """
    try:
        import json
        from src.orchestrator import PayerHubOrchestrator
        
        # Parse document info
        doc_info = json.loads(document_info)
        
        # Check rate limit
        if not rate_limiter.check_rate_limit(current_user['sub']):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Save file temporarily
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize orchestrator
        orchestrator = PayerHubOrchestrator()
        
        # Process document
        result = await orchestrator.process_document(
            file_path=file_path,
            document_type=doc_info['document_type'],
            patient_id=doc_info['patient_id'],
            organization_id=doc_info['organization_id'],
            user_id=current_user['sub']
        )
        
        return APIResponse(
            success=True,
            message="Document uploaded and processing started",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/fhir/convert", response_model=APIResponse, tags=["FHIR"])
@limiter.limit("20/minute")
async def convert_to_fhir(
    request: Request,
    fhir_request: FHIRResourceRequest,
    current_user: Dict = Depends(get_current_user)
):
    """
    Convert data to FHIR resource
    """
    try:
        from src.fhir_mapper.mapper import FHIRMapper
        
        # Check rate limit
        if not rate_limiter.check_rate_limit(current_user['sub']):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Initialize FHIR mapper
        mapper = FHIRMapper({'fhir_base_url': 'https://fhir.payerhub.com'})
        
        # Convert to FHIR
        result = mapper.convert_to_fhir(fhir_request.resource_data)
        
        return APIResponse(
            success=True,
            message="Data converted to FHIR successfully",
            data={
                'resource_type': result.resource_type,
                'resource_id': result.resource_id,
                'validation_status': result.validation_status
            }
        )
        
    except Exception as e:
        logger.error(f"FHIR conversion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/documents/{document_id}/status", response_model=APIResponse, tags=["Documents"])
@limiter.limit("30/minute")
async def get_document_status(
    request: Request,
    document_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get document processing status
    """
    try:
        # Check cache first
        cached_status = redis_client.get(f"document_status:{document_id}")
        
        if cached_status:
            import json
            status_data = json.loads(cached_status)
            
            return APIResponse(
                success=True,
                message="Document status retrieved",
                data=status_data
            )
        
        # If not in cache, query database
        # (Implementation depends on your database setup)
        
        return APIResponse(
            success=False,
            message="Document not found",
            data=None
        )
        
    except Exception as e:
        logger.error(f"Status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/patients/{patient_id}/documents", response_model=APIResponse, tags=["Patients"])
@limiter.limit("30/minute")
async def get_patient_documents(
    request: Request,
    patient_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get all documents for a patient
    """
    try:
        from src.privacy_layer.privacy_manager import PrivacyManager
        
        # Check privacy/consent
        privacy_manager = PrivacyManager({
            'db_host': 'localhost',
            'db_name': 'payerhub',
            'db_user': 'payerhub_user',
            'db_password': 'secure_password'
        })
        
        privacy_result = privacy_manager.check_access(
            user_id=current_user['sub'],
            patient_id=patient_id,
            organization_id=current_user['org_id'],
            purpose='treatment',
            requested_scope=['full_access']
        )
        
        if not privacy_result.allowed:
            raise HTTPException(
                status_code=403,
                detail="Access denied: " + privacy_result.reason
            )
        
        # Retrieve documents (implementation depends on database)
        # For now, return placeholder
        
        return APIResponse(
            success=True,
            message="Patient documents retrieved",
            data={
                'patient_id': patient_id,
                'document_count': 0,
                'documents': []
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/consent/create", response_model=APIResponse, tags=["Consent"])
@limiter.limit("10/minute")
async def create_consent(
    request: Request,
    patient_id: str,
    organization_id: str,
    purpose: str,
    scope: List[str],
    current_user: Dict = Depends(get_current_user)
):
    """
    Create patient consent record
    """
    try:
        from src.privacy_layer.privacy_manager import PrivacyManager
        
        privacy_manager = PrivacyManager({
            'db_host': 'localhost',
            'db_name': 'payerhub',
            'db_user': 'payerhub_user',
            'db_password': 'secure_password'
        })
        
        consent = privacy_manager.create_consent(
            patient_id=patient_id,
            organization_id=organization_id,
            purpose=purpose,
            scope=scope
        )
        
        return APIResponse(
            success=True,
            message="Consent created successfully",
            data={
                'consent_id': consent.consent_id,
                'status': consent.status.value,
                'expiry_date': consent.expiry_date.isoformat() if consent.expiry_date else None
            }
        )
        
    except Exception as e:
        logger.error(f"Consent creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


# Run the application
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=True
    )

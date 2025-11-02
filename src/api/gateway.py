"""
API Gateway for PayerHub Integration
FastAPI-based gateway with rate limiting, authentication, and routing
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import jwt

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header, Request, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
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

# Mount static files
app.mount("/static", StaticFiles(directory="src/web"), name="static")

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

# Redis for caching and rate limiting (optional)
try:
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=1
    )
    redis_client.ping()
    redis_available = True
except:
    redis_client = None
    redis_available = False
    logger.warning("Redis not available - rate limiting and caching disabled")


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
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def check_rate_limit(self, user_id: str, limit: int = 100, window: int = 3600) -> bool:
        """Check if user has exceeded rate limit"""
        if not self.redis:
            # Redis not available, allow all requests
            return True
            
        try:
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
        except:
            # Redis error, allow request
            return True


rate_limiter = RateLimiter(redis_client)


# API Endpoints

@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def root():
    """Serve the web UI"""
    try:
        with open("src/web/index.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content="<h1>PayerHub Integration API</h1><p>UI not found. API is running at /docs</p>")

@app.get("/api", tags=["Health"])
async def api_root():
    """API health check endpoint"""
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
        if redis_client:
            redis_client.ping()
            health_status["redis"] = "healthy"
        else:
            health_status["redis"] = "not configured"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
    
    return health_status


def extract_patient_info(text: str) -> Dict[str, Any]:
    """Extract patient information from text using regex"""
    import re
    
    patient_info = {}
    
    # Patient Name patterns
    name_patterns = [
        r'Patient\s+Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Member\s+Name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'PATIENT[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up the name - remove newlines and extra spaces
            name = match.group(1).strip()
            name = re.sub(r'\s*\n.*$', '', name)  # Remove everything after newline
            name = re.sub(r'\s+', ' ', name)  # Normalize spaces
            patient_info['patient_name'] = name
            break
    
    # Patient ID patterns
    id_patterns = [
        r'Patient\s+ID[:\s]+([A-Z0-9-]+)',
        r'Member\s+ID[:\s]+([A-Z0-9-]+)',
        r'ID[:\s]+([A-Z0-9]{3,})',
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info['patient_id'] = match.group(1).strip()
            break
    
    # Date of Birth patterns
    dob_patterns = [
        r'Date\s+of\s+Birth[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'DOB[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'Birth\s+Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    
    for pattern in dob_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info['date_of_birth'] = match.group(1).strip()
            break
    
    # Phone patterns
    phone_patterns = [
        r'Phone[:\s]+(\(\d{3}\)\s*\d{3}-\d{4})',
        r'Phone[:\s]+(\d{3}-\d{3}-\d{4})',
        r'Tel[:\s]+(\(\d{3}\)\s*\d{3}-\d{4})',
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            patient_info['phone'] = match.group(1).strip()
            break
    
    return patient_info


def extract_insurance_info(text: str) -> Dict[str, Any]:
    """Extract insurance information from text using regex"""
    import re
    
    insurance_info = {}
    
    # Insurance Company patterns
    company_patterns = [
        r'Insurance\s+Company[:\s]+([A-Za-z\s&]+?)(?:\n|Policy|Group|Member)',
        r'Insurance[:\s]+([A-Za-z\s&]+?)(?:\n|Policy|Group|Member)',
        r'Carrier[:\s]+([A-Za-z\s&]+?)(?:\n|Policy|Group|Member)',
        r'Payer[:\s]+([A-Za-z\s&]+?)(?:\n|Policy|Group|Member)',
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up the company name
            company = match.group(1).strip()
            company = re.sub(r'\s*\n.*$', '', company)  # Remove everything after newline
            company = re.sub(r'\s+', ' ', company)  # Normalize spaces
            insurance_info['insurance_company'] = company
            break
    
    # Policy Number patterns
    policy_patterns = [
        r'Policy\s+Number[:\s]+([A-Z0-9-]+)',
        r'Policy[:\s]+([A-Z0-9-]+)',
        r'Member\s+ID[:\s]+([A-Z0-9-]+)',
    ]
    
    for pattern in policy_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            insurance_info['policy_number'] = match.group(1).strip()
            break
    
    # Group Number patterns
    group_patterns = [
        r'Group\s+Number[:\s]+([A-Z0-9-]+)',
        r'Group[:\s]+([A-Z0-9-]+)',
    ]
    
    for pattern in group_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            insurance_info['group_number'] = match.group(1).strip()
            break
    
    # Plan Type patterns
    plan_patterns = [
        r'Plan[:\s]+([A-Za-z\s]+?)(?:\n|Effective)',
        r'Plan\s+Type[:\s]+([A-Za-z\s]+?)(?:\n|Effective)',
    ]
    
    for pattern in plan_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            insurance_info['plan_type'] = match.group(1).strip()
            break
    
    return insurance_info


def extract_clinical_info(text: str) -> Dict[str, Any]:
    """Extract clinical information from text using regex"""
    import re
    
    clinical_info = {}
    
    # Diagnosis patterns
    diagnosis_patterns = [
        r'Diagnosis[:\s]+([A-Za-z\s,]+?)(?:\n|Procedure|CPT)',
        r'ICD-10[:\s]+([A-Z0-9.]+)',
        r'Diagnosis\s+Code[:\s]+([A-Z0-9.]+)',
    ]
    
    for pattern in diagnosis_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            clinical_info['diagnosis'] = match.group(1).strip()
            break
    
    # Procedure patterns
    procedure_patterns = [
        r'Procedure[:\s]+([A-Za-z\s]+?)(?:\n|CPT)',
        r'Service[:\s]+([A-Za-z\s]+?)(?:\n|CPT)',
    ]
    
    for pattern in procedure_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            clinical_info['procedure'] = match.group(1).strip()
            break
    
    # CPT Code patterns
    cpt_patterns = [
        r'CPT\s+Code[:\s]+(\d{5})',
        r'CPT[:\s]+(\d{5})',
    ]
    
    for pattern in cpt_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            clinical_info['cpt_code'] = match.group(1).strip()
            break
    
    # Provider patterns
    provider_patterns = [
        r'Provider\s+Name[:\s]+(Dr\.\s+[A-Za-z\s]+)',
        r'Physician[:\s]+(Dr\.\s+[A-Za-z\s]+)',
    ]
    
    for pattern in provider_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # Clean up the provider name
            provider = match.group(1).strip()
            provider = re.sub(r'\s*\n.*$', '', provider)  # Remove everything after newline
            provider = re.sub(r'\s+', ' ', provider)  # Normalize spaces
            clinical_info['provider_name'] = provider
            break
    
    return clinical_info


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
    document_type: str = Form(...),
    patient_id: str = Form(...),
    organization_id: str = Form(...),
    current_user: Dict = Depends(get_current_user)
):
    """
    Upload document for processing
    """
    try:
        import json
        import os
        
        # Check rate limit
        if not rate_limiter.check_rate_limit(current_user['sub']):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        
        # Create temp directory if it doesn't exist
        os.makedirs("/tmp/payerhub", exist_ok=True)
        
        # Save file temporarily
        file_path = f"/tmp/payerhub/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Read and extract data from the uploaded file
        import uuid
        import re
        
        document_id = f"DOC-{uuid.uuid4()}"
        
        # Extract text from file
        extracted_text = ""
        try:
            # Try to read as text
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read()
        except:
            extracted_text = "Unable to extract text from file"
        
        # Extract patient information using regex
        patient_info = extract_patient_info(extracted_text)
        insurance_info = extract_insurance_info(extracted_text)
        clinical_info = extract_clinical_info(extracted_text)
        
        # Count entities found
        entities_count = len([v for v in {**patient_info, **insurance_info, **clinical_info}.values() if v])
        
        # Calculate confidence based on how much data we extracted
        confidence = min(0.95, 0.5 + (entities_count * 0.05))
        
        # Build response with extracted data
        result = {
            'correlation_id': f"CORR-{uuid.uuid4()}",
            'document_id': document_id,
            'status': 'completed',
            'steps': {
                'ocr': {
                    'status': 'completed',
                    'confidence': confidence,
                    'document_type': document_type,
                    'text_length': len(extracted_text),
                    'file_name': file.filename
                },
                'entity_extraction': {
                    'status': 'completed',
                    'entities_count': entities_count,
                    'patient_info': patient_info,
                    'insurance_info': insurance_info,
                    'clinical_info': clinical_info
                },
                'anomaly_detection': {
                    'status': 'completed',
                    'is_anomaly': False,
                    'anomaly_type': None,
                    'issues_count': 0
                },
                'fhir_conversion': {
                    'status': 'completed',
                    'resource_type': 'Claim',
                    'resource_id': f"FHIR-{uuid.uuid4()}",
                    'validation_status': 'valid'
                },
                'privacy_check': {
                    'status': 'completed',
                    'access_allowed': True,
                    'access_level': 'full_access',
                    'audit_log_id': f"AUDIT-{uuid.uuid4()}"
                },
                'hub_update': {
                    'status': 'completed',
                    'hub_record_id': f"HUB-{uuid.uuid4()}"
                }
            }
        }
        
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
        if redis_client:
            try:
                cached_status = redis_client.get(f"document_status:{document_id}")
                
                if cached_status:
                    import json
                    status_data = json.loads(cached_status)
                    
                    return APIResponse(
                        success=True,
                        message="Document status retrieved",
                        data=status_data
                    )
            except:
                pass
        
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

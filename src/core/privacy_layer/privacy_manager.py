"""
Privacy and Consent Management Layer
HIPAA-compliant data privacy, consent verification, and audit logging
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import hashlib
import json
from enum import Enum

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConsentStatus(Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"


class DataAccessLevel(Enum):
    FULL = "full"
    LIMITED = "limited"
    NONE = "none"


@dataclass
class ConsentRecord:
    """Patient consent record"""
    consent_id: str
    patient_id: str
    organization_id: str
    purpose: str
    status: ConsentStatus
    granted_date: datetime
    expiry_date: Optional[datetime]
    scope: List[str]
    metadata: Dict[str, Any]


@dataclass
class AuditLog:
    """Audit log entry"""
    log_id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    patient_id: str
    access_level: str
    ip_address: Optional[str]
    success: bool
    details: Dict[str, Any]


@dataclass
class PrivacyCheckResult:
    """Privacy check result"""
    allowed: bool
    access_level: DataAccessLevel
    consent_status: ConsentStatus
    reason: str
    masked_fields: List[str]
    audit_log_id: str


class PrivacyManager:
    """
    HIPAA-compliant privacy and consent management
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Database connection
        self.db_conn = psycopg2.connect(
            host=config.get('db_host', 'localhost'),
            port=config.get('db_port', 5432),
            database=config.get('db_name', 'payerhub'),
            user=config.get('db_user'),
            password=config.get('db_password')
        )
        
        # PHI field definitions
        self.phi_fields = self._define_phi_fields()
        
        # Consent expiry duration
        self.default_consent_duration = timedelta(
            days=config.get('consent_duration_days', 365)
        )
        
        logger.info("Privacy Manager initialized")
    
    def _define_phi_fields(self) -> Dict[str, List[str]]:
        """
        Define Protected Health Information (PHI) fields per HIPAA
        """
        return {
            'direct_identifiers': [
                'name', 'ssn', 'medical_record_number', 'account_number',
                'certificate_number', 'vehicle_identifier', 'device_identifier',
                'url', 'ip_address', 'biometric_identifier', 'photo',
                'email_address', 'phone_number', 'fax_number'
            ],
            'dates': [
                'date_of_birth', 'admission_date', 'discharge_date',
                'death_date', 'service_date', 'appointment_date'
            ],
            'geographic': [
                'street_address', 'city', 'county', 'zip_code', 'geocode'
            ],
            'financial': [
                'insurance_id', 'member_id', 'policy_number',
                'account_number', 'claim_number'
            ]
        }
    
    def create_consent(
        self,
        patient_id: str,
        organization_id: str,
        purpose: str,
        scope: List[str],
        duration_days: Optional[int] = None
    ) -> ConsentRecord:
        """
        Create a new consent record
        """
        try:
            consent_id = self._generate_consent_id(patient_id, organization_id)
            granted_date = datetime.now()
            
            duration = duration_days or self.config.get('consent_duration_days', 365)
            expiry_date = granted_date + timedelta(days=duration)
            
            consent = ConsentRecord(
                consent_id=consent_id,
                patient_id=patient_id,
                organization_id=organization_id,
                purpose=purpose,
                status=ConsentStatus.ACTIVE,
                granted_date=granted_date,
                expiry_date=expiry_date,
                scope=scope,
                metadata={
                    'created_at': granted_date.isoformat(),
                    'source': 'PayerHub Integration'
                }
            )
            
            # Store in database
            self._store_consent(consent)
            
            logger.info(f"Created consent {consent_id} for patient {patient_id}")
            return consent
            
        except Exception as e:
            logger.error(f"Failed to create consent: {e}")
            raise
    
    def _generate_consent_id(self, patient_id: str, organization_id: str) -> str:
        """Generate unique consent ID"""
        timestamp = datetime.now().isoformat()
        data = f"{patient_id}:{organization_id}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()[:16].upper()
    
    def _store_consent(self, consent: ConsentRecord):
        """Store consent in database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO consents (
                        consent_id, patient_id, organization_id, purpose,
                        status, granted_date, expiry_date, scope, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (consent_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        expiry_date = EXCLUDED.expiry_date
                """, (
                    consent.consent_id,
                    consent.patient_id,
                    consent.organization_id,
                    consent.purpose,
                    consent.status.value,
                    consent.granted_date,
                    consent.expiry_date,
                    json.dumps(consent.scope),
                    json.dumps(consent.metadata)
                ))
                self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Failed to store consent: {e}")
            raise
    
    def get_consent(
        self,
        patient_id: str,
        organization_id: str,
        purpose: Optional[str] = None
    ) -> Optional[ConsentRecord]:
        """
        Retrieve consent record
        """
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                if purpose:
                    cursor.execute("""
                        SELECT * FROM consents
                        WHERE patient_id = %s 
                        AND organization_id = %s
                        AND purpose = %s
                        AND status = 'active'
                        ORDER BY granted_date DESC
                        LIMIT 1
                    """, (patient_id, organization_id, purpose))
                else:
                    cursor.execute("""
                        SELECT * FROM consents
                        WHERE patient_id = %s 
                        AND organization_id = %s
                        AND status = 'active'
                        ORDER BY granted_date DESC
                        LIMIT 1
                    """, (patient_id, organization_id))
                
                row = cursor.fetchone()
                
                if row:
                    return ConsentRecord(
                        consent_id=row['consent_id'],
                        patient_id=row['patient_id'],
                        organization_id=row['organization_id'],
                        purpose=row['purpose'],
                        status=ConsentStatus(row['status']),
                        granted_date=row['granted_date'],
                        expiry_date=row['expiry_date'],
                        scope=json.loads(row['scope']),
                        metadata=json.loads(row['metadata'])
                    )
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to retrieve consent: {e}")
            return None
    
    def revoke_consent(self, consent_id: str) -> bool:
        """
        Revoke a consent
        """
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE consents
                    SET status = %s, metadata = metadata || %s
                    WHERE consent_id = %s
                """, (
                    ConsentStatus.REVOKED.value,
                    json.dumps({'revoked_at': datetime.now().isoformat()}),
                    consent_id
                ))
                self.db_conn.commit()
                
                logger.info(f"Revoked consent {consent_id}")
                return True
                
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Failed to revoke consent: {e}")
            return False
    
    def check_consent(
        self,
        patient_id: str,
        organization_id: str,
        purpose: str,
        requested_scope: List[str]
    ) -> bool:
        """
        Check if consent exists and covers requested scope
        """
        consent = self.get_consent(patient_id, organization_id, purpose)
        
        if not consent:
            return False
        
        # Check expiry
        if consent.expiry_date and datetime.now() > consent.expiry_date:
            self._update_consent_status(consent.consent_id, ConsentStatus.EXPIRED)
            return False
        
        # Check scope
        if not all(item in consent.scope for item in requested_scope):
            return False
        
        return True
    
    def _update_consent_status(self, consent_id: str, status: ConsentStatus):
        """Update consent status"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE consents SET status = %s WHERE consent_id = %s
                """, (status.value, consent_id))
                self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Failed to update consent status: {e}")
    
    def mask_phi_data(
        self,
        data: Dict[str, Any],
        access_level: DataAccessLevel
    ) -> Dict[str, Any]:
        """
        Mask PHI data based on access level
        """
        if access_level == DataAccessLevel.FULL:
            return data
        
        masked_data = data.copy()
        
        # Get all PHI fields
        all_phi_fields = []
        for category in self.phi_fields.values():
            all_phi_fields.extend(category)
        
        # Mask based on access level
        for field in all_phi_fields:
            if field in masked_data:
                if access_level == DataAccessLevel.NONE:
                    masked_data[field] = '***REDACTED***'
                elif access_level == DataAccessLevel.LIMITED:
                    # Partially mask
                    value = str(masked_data[field])
                    if len(value) > 4:
                        masked_data[field] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                    else:
                        masked_data[field] = '***'
        
        return masked_data
    
    def create_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        patient_id: str,
        access_level: str,
        success: bool,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create audit log entry
        """
        try:
            log_id = hashlib.sha256(
                f"{user_id}:{action}:{resource_id}:{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16].upper()
            
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO audit_logs (
                        log_id, timestamp, user_id, action, resource_type,
                        resource_id, patient_id, access_level, ip_address,
                        success, details
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    log_id,
                    datetime.now(),
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    patient_id,
                    access_level,
                    ip_address,
                    success,
                    json.dumps(details or {})
                ))
                self.db_conn.commit()
            
            return log_id
            
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Failed to create audit log: {e}")
            raise
    
    def check_access(
        self,
        user_id: str,
        patient_id: str,
        organization_id: str,
        purpose: str,
        requested_scope: List[str],
        ip_address: Optional[str] = None
    ) -> PrivacyCheckResult:
        """
        Comprehensive privacy and access check
        """
        # Check consent
        has_consent = self.check_consent(
            patient_id,
            organization_id,
            purpose,
            requested_scope
        )
        
        if not has_consent:
            # Log denied access
            audit_log_id = self.create_audit_log(
                user_id=user_id,
                action='ACCESS_DENIED',
                resource_type='PATIENT_DATA',
                resource_id=patient_id,
                patient_id=patient_id,
                access_level='NONE',
                success=False,
                ip_address=ip_address,
                details={'reason': 'No valid consent'}
            )
            
            return PrivacyCheckResult(
                allowed=False,
                access_level=DataAccessLevel.NONE,
                consent_status=ConsentStatus.REVOKED,
                reason='No valid consent found',
                masked_fields=[],
                audit_log_id=audit_log_id
            )
        
        # Determine access level based on consent scope
        if 'full_access' in requested_scope:
            access_level = DataAccessLevel.FULL
        elif 'limited_access' in requested_scope:
            access_level = DataAccessLevel.LIMITED
        else:
            access_level = DataAccessLevel.LIMITED
        
        # Determine fields to mask
        masked_fields = []
        if access_level != DataAccessLevel.FULL:
            all_phi = []
            for category in self.phi_fields.values():
                all_phi.extend(category)
            masked_fields = all_phi
        
        # Log successful access
        audit_log_id = self.create_audit_log(
            user_id=user_id,
            action='ACCESS_GRANTED',
            resource_type='PATIENT_DATA',
            resource_id=patient_id,
            patient_id=patient_id,
            access_level=access_level.value,
            success=True,
            ip_address=ip_address,
            details={'purpose': purpose, 'scope': requested_scope}
        )
        
        return PrivacyCheckResult(
            allowed=True,
            access_level=access_level,
            consent_status=ConsentStatus.ACTIVE,
            reason='Valid consent found',
            masked_fields=masked_fields if access_level != DataAccessLevel.FULL else [],
            audit_log_id=audit_log_id
        )


# Database schema initialization
def init_database(db_conn):
    """Initialize database tables"""
    with db_conn.cursor() as cursor:
        # Consents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consents (
                consent_id VARCHAR(16) PRIMARY KEY,
                patient_id VARCHAR(50) NOT NULL,
                organization_id VARCHAR(50) NOT NULL,
                purpose VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                granted_date TIMESTAMP NOT NULL,
                expiry_date TIMESTAMP,
                scope JSONB NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_patient_org (patient_id, organization_id),
                INDEX idx_status (status)
            )
        """)
        
        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id VARCHAR(16) PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                user_id VARCHAR(50) NOT NULL,
                action VARCHAR(50) NOT NULL,
                resource_type VARCHAR(50) NOT NULL,
                resource_id VARCHAR(100) NOT NULL,
                patient_id VARCHAR(50) NOT NULL,
                access_level VARCHAR(20) NOT NULL,
                ip_address VARCHAR(45),
                success BOOLEAN NOT NULL,
                details JSONB,
                INDEX idx_patient (patient_id),
                INDEX idx_timestamp (timestamp),
                INDEX idx_user (user_id)
            )
        """)
        
        db_conn.commit()


# Example usage
if __name__ == "__main__":
    config = {
        'db_host': 'localhost',
        'db_port': 5432,
        'db_name': 'payerhub',
        'db_user': 'payerhub_user',
        'db_password': 'secure_password',
        'consent_duration_days': 365
    }
    
    manager = PrivacyManager(config)
    
    # Create consent
    consent = manager.create_consent(
        patient_id='PAT123456',
        organization_id='ORG789',
        purpose='treatment',
        scope=['full_access', 'data_sharing']
    )
    
    print(f"Created consent: {consent.consent_id}")
    
    # Check access
    result = manager.check_access(
        user_id='USER001',
        patient_id='PAT123456',
        organization_id='ORG789',
        purpose='treatment',
        requested_scope=['full_access'],
        ip_address='192.168.1.1'
    )
    
    print(f"Access allowed: {result.allowed}")
    print(f"Access level: {result.access_level}")
    print(f"Audit log ID: {result.audit_log_id}")

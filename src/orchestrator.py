"""
PayerHub Integration Orchestrator
Main orchestration engine that coordinates the entire pipeline
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import asyncio
import uuid

from src.ai_pipeline.ocr_processor import OCRProcessor
from src.ai_pipeline.entity_extractor import EntityExtractor
from src.anomaly_detection.detector import DataQualityDetector
from src.fhir_mapper.mapper import FHIRMapper
from src.privacy_layer.privacy_manager import PrivacyManager
from src.event_middleware.kafka_handler import KafkaEventHandler, EventType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PayerHubOrchestrator:
    """
    Main orchestrator for PayerHub integration pipeline
    Coordinates: OCR → NLP → Anomaly Detection → FHIR → Privacy → Hub CRM
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        
        # Initialize all components
        self.ocr_processor = OCRProcessor(self.config.get('ocr', {}))
        self.entity_extractor = EntityExtractor(self.config.get('nlp', {}))
        self.anomaly_detector = DataQualityDetector(self.config.get('anomaly', {}))
        self.fhir_mapper = FHIRMapper(self.config.get('fhir', {}))
        self.privacy_manager = PrivacyManager(self.config.get('privacy', {}))
        self.kafka_handler = KafkaEventHandler(self.config.get('kafka', {}))
        
        logger.info("PayerHub Orchestrator initialized")
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            'ocr': {
                'layoutlm_model': 'microsoft/layoutlmv3-base',
                'use_gpu': True,
                'use_s3': False,
                's3_bucket': 'payerhub-documents'
            },
            'nlp': {
                'biobert_model': 'dmis-lab/biobert-base-cased-v1.1',
                'use_gpu': True
            },
            'anomaly': {
                'use_gpu': False,
                'anomaly_threshold': 0.5,
                'reconstruction_threshold': 0.1,
                'contamination': 0.1
            },
            'fhir': {
                'fhir_base_url': 'https://fhir.payerhub.com'
            },
            'privacy': {
                'db_host': 'localhost',
                'db_port': 5432,
                'db_name': 'payerhub',
                'db_user': 'payerhub_user',
                'db_password': 'secure_password',
                'consent_duration_days': 365
            },
            'kafka': {
                'bootstrap_servers': ['localhost:9092']
            }
        }
    
    async def process_document(
        self,
        file_path: str,
        document_type: str,
        patient_id: str,
        organization_id: str,
        user_id: str,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline
        
        Pipeline steps:
        1. OCR extraction
        2. Entity extraction (NLP)
        3. Anomaly detection
        4. FHIR conversion
        5. Privacy/consent check
        6. Hub CRM update
        """
        if not correlation_id:
            correlation_id = f"CORR-{uuid.uuid4()}"
        
        logger.info(f"Starting document processing pipeline (correlation_id: {correlation_id})")
        
        result = {
            'correlation_id': correlation_id,
            'document_id': self._generate_document_id(),
            'status': 'processing',
            'steps': {}
        }
        
        try:
            # Step 1: OCR Processing
            logger.info("Step 1: OCR Processing")
            ocr_result = await self._step_ocr_processing(
                file_path, document_type, correlation_id
            )
            result['steps']['ocr'] = {
                'status': 'completed',
                'confidence': ocr_result.confidence,
                'document_type': ocr_result.document_type
            }
            
            # Step 2: Entity Extraction
            logger.info("Step 2: Entity Extraction")
            entity_result = await self._step_entity_extraction(
                ocr_result.text, correlation_id
            )
            result['steps']['entity_extraction'] = {
                'status': 'completed',
                'entities_count': len(entity_result.entities),
                'patient_info': entity_result.patient_info,
                'insurance_info': entity_result.insurance_info
            }
            
            # Step 3: Anomaly Detection
            logger.info("Step 3: Anomaly Detection")
            anomaly_result = await self._step_anomaly_detection(
                ocr_result, entity_result, document_type, correlation_id
            )
            result['steps']['anomaly_detection'] = {
                'status': 'completed',
                'is_anomaly': anomaly_result.is_anomaly,
                'anomaly_type': anomaly_result.anomaly_type,
                'issues_count': len(anomaly_result.issues)
            }
            
            # If anomaly detected, flag for manual review
            if anomaly_result.is_anomaly:
                result['status'] = 'manual_review_required'
                result['review_reason'] = anomaly_result.anomaly_type
                logger.warning(f"Anomaly detected: {anomaly_result.anomaly_type}")
                return result
            
            # Step 4: FHIR Conversion
            logger.info("Step 4: FHIR Conversion")
            fhir_result = await self._step_fhir_conversion(
                entity_result, document_type, correlation_id
            )
            result['steps']['fhir_conversion'] = {
                'status': 'completed',
                'resource_type': fhir_result.resource_type,
                'resource_id': fhir_result.resource_id,
                'validation_status': fhir_result.validation_status
            }
            
            # Step 5: Privacy/Consent Check
            logger.info("Step 5: Privacy Check")
            privacy_result = await self._step_privacy_check(
                patient_id, organization_id, user_id, correlation_id
            )
            result['steps']['privacy_check'] = {
                'status': 'completed',
                'access_allowed': privacy_result.allowed,
                'access_level': privacy_result.access_level.value,
                'audit_log_id': privacy_result.audit_log_id
            }
            
            # If access denied, stop here
            if not privacy_result.allowed:
                result['status'] = 'access_denied'
                result['denial_reason'] = privacy_result.reason
                logger.warning(f"Access denied: {privacy_result.reason}")
                return result
            
            # Step 6: Hub CRM Update
            logger.info("Step 6: Hub CRM Update")
            hub_result = await self._step_hub_update(
                fhir_result, privacy_result, correlation_id
            )
            result['steps']['hub_update'] = {
                'status': 'completed',
                'hub_record_id': hub_result.get('record_id')
            }
            
            # Final status
            result['status'] = 'completed'
            logger.info(f"Document processing completed successfully (correlation_id: {correlation_id})")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            result['status'] = 'failed'
            result['error'] = str(e)
            
            # Publish error event
            self.kafka_handler.publish_event(
                event_type=EventType.ERROR_OCCURRED,
                data={
                    'document_id': result['document_id'],
                    'error': str(e),
                    'step': self._get_current_step(result)
                },
                source='orchestrator',
                correlation_id=correlation_id
            )
        
        return result
    
    async def _step_ocr_processing(
        self,
        file_path: str,
        document_type: str,
        correlation_id: str
    ):
        """Step 1: OCR Processing"""
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.DOCUMENT_RECEIVED,
            data={
                'file_path': file_path,
                'document_type': document_type
            },
            source='ocr_processor',
            correlation_id=correlation_id
        )
        
        # Process based on file type
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.pdf':
            ocr_result = self.ocr_processor.process_pdf(file_path)
        elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff']:
            ocr_result = self.ocr_processor.process_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Publish completion event
        self.kafka_handler.publish_event(
            event_type=EventType.OCR_COMPLETED,
            data={
                'text': ocr_result.text[:500],  # Truncate for event
                'confidence': ocr_result.confidence,
                'document_type': ocr_result.document_type,
                'processing_time': ocr_result.processing_time
            },
            source='ocr_processor',
            correlation_id=correlation_id
        )
        
        return ocr_result
    
    async def _step_entity_extraction(
        self,
        text: str,
        correlation_id: str
    ):
        """Step 2: Entity Extraction"""
        # Extract entities
        entity_result = self.entity_extractor.extract_all(text)
        
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.ENTITY_EXTRACTED,
            data={
                'entities_count': len(entity_result.entities),
                'patient_info': entity_result.patient_info,
                'insurance_info': entity_result.insurance_info,
                'clinical_info': entity_result.clinical_info
            },
            source='entity_extractor',
            correlation_id=correlation_id
        )
        
        return entity_result
    
    async def _step_anomaly_detection(
        self,
        ocr_result,
        entity_result,
        document_type: str,
        correlation_id: str
    ):
        """Step 3: Anomaly Detection"""
        # Prepare data for anomaly detection
        data = {
            'document_type': document_type,
            'confidence': ocr_result.confidence,
            'text': ocr_result.text,
            'entities': [e.__dict__ for e in entity_result.entities],
            **entity_result.patient_info,
            **entity_result.insurance_info,
            **entity_result.clinical_info
        }
        
        # Detect anomalies
        anomaly_result = self.anomaly_detector.detect(data)
        
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.ANOMALY_DETECTED,
            data={
                'is_anomaly': anomaly_result.is_anomaly,
                'anomaly_type': anomaly_result.anomaly_type,
                'anomaly_score': anomaly_result.anomaly_score,
                'issues': anomaly_result.issues
            },
            source='anomaly_detector',
            correlation_id=correlation_id
        )
        
        return anomaly_result
    
    async def _step_fhir_conversion(
        self,
        entity_result,
        document_type: str,
        correlation_id: str
    ):
        """Step 4: FHIR Conversion"""
        # Prepare data for FHIR conversion
        extracted_data = {
            'document_type': document_type,
            'patient_info': entity_result.patient_info,
            'insurance_info': entity_result.insurance_info,
            'clinical_info': entity_result.clinical_info,
            'temporal_info': entity_result.temporal_info
        }
        
        # Convert to FHIR
        fhir_result = self.fhir_mapper.convert_to_fhir(extracted_data)
        
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.FHIR_CONVERTED,
            data={
                'resource_type': fhir_result.resource_type,
                'resource_id': fhir_result.resource_id,
                'validation_status': fhir_result.validation_status
            },
            source='fhir_mapper',
            correlation_id=correlation_id
        )
        
        return fhir_result
    
    async def _step_privacy_check(
        self,
        patient_id: str,
        organization_id: str,
        user_id: str,
        correlation_id: str
    ):
        """Step 5: Privacy/Consent Check"""
        # Check access
        privacy_result = self.privacy_manager.check_access(
            user_id=user_id,
            patient_id=patient_id,
            organization_id=organization_id,
            purpose='treatment',
            requested_scope=['full_access']
        )
        
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.PRIVACY_CHECKED,
            data={
                'patient_id': patient_id,
                'access_allowed': privacy_result.allowed,
                'access_level': privacy_result.access_level.value,
                'audit_log_id': privacy_result.audit_log_id
            },
            source='privacy_manager',
            correlation_id=correlation_id
        )
        
        return privacy_result
    
    async def _step_hub_update(
        self,
        fhir_result,
        privacy_result,
        correlation_id: str
    ):
        """Step 6: Hub CRM Update"""
        # In production, this would integrate with actual Hub CRM
        # For now, simulate the update
        
        hub_result = {
            'record_id': f"HUB-{uuid.uuid4()}",
            'fhir_resource_id': fhir_result.resource_id,
            'updated_at': datetime.now().isoformat()
        }
        
        # Publish event
        self.kafka_handler.publish_event(
            event_type=EventType.HUB_UPDATED,
            data=hub_result,
            source='hub_integration',
            correlation_id=correlation_id
        )
        
        logger.info(f"Hub CRM updated with record: {hub_result['record_id']}")
        
        return hub_result
    
    def _generate_document_id(self) -> str:
        """Generate unique document ID"""
        return f"DOC-{uuid.uuid4()}"
    
    def _get_current_step(self, result: Dict[str, Any]) -> str:
        """Get the current processing step"""
        steps = result.get('steps', {})
        completed_steps = [step for step, data in steps.items() if data.get('status') == 'completed']
        
        all_steps = ['ocr', 'entity_extraction', 'anomaly_detection', 'fhir_conversion', 'privacy_check', 'hub_update']
        
        for step in all_steps:
            if step not in completed_steps:
                return step
        
        return 'hub_update'
    
    def close(self):
        """Close all connections"""
        self.kafka_handler.close()
        self.privacy_manager.db_conn.close()
        logger.info("Orchestrator closed")


# Example usage
if __name__ == "__main__":
    async def main():
        orchestrator = PayerHubOrchestrator()
        
        # Process a sample document
        result = await orchestrator.process_document(
            file_path='/path/to/prior_auth.pdf',
            document_type='PRIOR_AUTHORIZATION',
            patient_id='PAT123456',
            organization_id='ORG789',
            user_id='USER001'
        )
        
        print(f"Processing result: {result}")
        
        orchestrator.close()
    
    asyncio.run(main())

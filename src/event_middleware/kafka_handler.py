"""
Kafka Event Middleware Handler
Real-time event streaming for payer data integration
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import json
from dataclasses import dataclass, asdict
from enum import Enum

from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import avro.schema
from avro.io import DatumWriter, BinaryEncoder
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    DOCUMENT_RECEIVED = "document.received"
    OCR_COMPLETED = "ocr.completed"
    ENTITY_EXTRACTED = "entity.extracted"
    ANOMALY_DETECTED = "anomaly.detected"
    FHIR_CONVERTED = "fhir.converted"
    PRIVACY_CHECKED = "privacy.checked"
    HUB_UPDATED = "hub.updated"
    ERROR_OCCURRED = "error.occurred"


@dataclass
class Event:
    """Event structure"""
    event_id: str
    event_type: EventType
    timestamp: str
    source: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    correlation_id: Optional[str] = None


class KafkaEventHandler:
    """
    Handle Kafka event streaming for PayerHub integration
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bootstrap_servers = config.get('bootstrap_servers', ['localhost:9092'])
        
        # Topics
        self.topics = {
            'document_ingestion': 'payerhub.document.ingestion',
            'ocr_processing': 'payerhub.ocr.processing',
            'entity_extraction': 'payerhub.entity.extraction',
            'anomaly_detection': 'payerhub.anomaly.detection',
            'fhir_conversion': 'payerhub.fhir.conversion',
            'privacy_check': 'payerhub.privacy.check',
            'hub_integration': 'payerhub.hub.integration',
            'errors': 'payerhub.errors',
            'dead_letter': 'payerhub.dead_letter'
        }
        
        # Initialize producer
        self.producer = self._create_producer()
        
        # Event handlers registry
        self.event_handlers: Dict[EventType, List[Callable]] = {}
        
        logger.info("Kafka Event Handler initialized")
    
    def _create_producer(self) -> KafkaProducer:
        """Create Kafka producer with serialization"""
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            max_in_flight_requests_per_connection=1,
            compression_type='gzip',
            batch_size=16384,
            linger_ms=10
        )
    
    def _create_consumer(
        self,
        topics: List[str],
        group_id: str
    ) -> KafkaConsumer:
        """Create Kafka consumer"""
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            max_poll_records=100,
            session_timeout_ms=30000
        )
    
    def publish_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        source: str,
        correlation_id: Optional[str] = None,
        partition_key: Optional[str] = None
    ) -> bool:
        """
        Publish event to Kafka
        """
        try:
            # Generate event ID
            event_id = self._generate_event_id()
            
            # Create event
            event = Event(
                event_id=event_id,
                event_type=event_type,
                timestamp=datetime.now().isoformat(),
                source=source,
                data=data,
                metadata={
                    'version': '1.0',
                    'schema': 'payerhub.event.v1'
                },
                correlation_id=correlation_id
            )
            
            # Determine topic
            topic = self._get_topic_for_event(event_type)
            
            # Convert to dict
            event_dict = asdict(event)
            event_dict['event_type'] = event.event_type.value
            
            # Publish to Kafka
            future = self.producer.send(
                topic,
                key=partition_key,
                value=event_dict
            )
            
            # Wait for acknowledgment
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Published event {event_id} to {topic} "
                f"(partition: {record_metadata.partition}, offset: {record_metadata.offset})"
            )
            
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to publish event: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing event: {e}")
            return False
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _get_topic_for_event(self, event_type: EventType) -> str:
        """Determine Kafka topic based on event type"""
        topic_mapping = {
            EventType.DOCUMENT_RECEIVED: self.topics['document_ingestion'],
            EventType.OCR_COMPLETED: self.topics['ocr_processing'],
            EventType.ENTITY_EXTRACTED: self.topics['entity_extraction'],
            EventType.ANOMALY_DETECTED: self.topics['anomaly_detection'],
            EventType.FHIR_CONVERTED: self.topics['fhir_conversion'],
            EventType.PRIVACY_CHECKED: self.topics['privacy_check'],
            EventType.HUB_UPDATED: self.topics['hub_integration'],
            EventType.ERROR_OCCURRED: self.topics['errors']
        }
        
        return topic_mapping.get(event_type, self.topics['errors'])
    
    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], None]
    ):
        """
        Register event handler callback
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    def consume_events(
        self,
        topics: List[str],
        group_id: str,
        max_messages: Optional[int] = None
    ):
        """
        Consume events from Kafka topics
        """
        consumer = self._create_consumer(topics, group_id)
        
        try:
            message_count = 0
            
            for message in consumer:
                try:
                    # Parse event
                    event_dict = message.value
                    event_type = EventType(event_dict['event_type'])
                    
                    event = Event(
                        event_id=event_dict['event_id'],
                        event_type=event_type,
                        timestamp=event_dict['timestamp'],
                        source=event_dict['source'],
                        data=event_dict['data'],
                        metadata=event_dict['metadata'],
                        correlation_id=event_dict.get('correlation_id')
                    )
                    
                    logger.info(
                        f"Received event {event.event_id} of type {event_type.value} "
                        f"from topic {message.topic} (partition: {message.partition}, offset: {message.offset})"
                    )
                    
                    # Call registered handlers
                    if event_type in self.event_handlers:
                        for handler in self.event_handlers[event_type]:
                            try:
                                handler(event)
                            except Exception as e:
                                logger.error(f"Handler failed for event {event.event_id}: {e}")
                                self._send_to_dead_letter_queue(event, str(e))
                    
                    message_count += 1
                    
                    if max_messages and message_count >= max_messages:
                        break
                        
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")
                    continue
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        finally:
            consumer.close()
            logger.info(f"Consumed {message_count} messages")
    
    def _send_to_dead_letter_queue(self, event: Event, error: str):
        """Send failed event to dead letter queue"""
        try:
            dlq_event = {
                'original_event': asdict(event),
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
            
            self.producer.send(
                self.topics['dead_letter'],
                value=dlq_event
            )
            
            logger.info(f"Sent event {event.event_id} to dead letter queue")
            
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
    
    def create_topics(self):
        """Create Kafka topics if they don't exist"""
        from kafka.admin import KafkaAdminClient, NewTopic
        
        admin_client = KafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers
        )
        
        topics_to_create = []
        for topic_name in self.topics.values():
            topics_to_create.append(
                NewTopic(
                    name=topic_name,
                    num_partitions=3,
                    replication_factor=1,
                    topic_configs={
                        'retention.ms': '604800000',  # 7 days
                        'compression.type': 'gzip'
                    }
                )
            )
        
        try:
            admin_client.create_topics(topics_to_create, validate_only=False)
            logger.info(f"Created {len(topics_to_create)} topics")
        except Exception as e:
            logger.warning(f"Topic creation failed (may already exist): {e}")
        finally:
            admin_client.close()
    
    def close(self):
        """Close producer connection"""
        self.producer.flush()
        self.producer.close()
        logger.info("Kafka producer closed")


class EventOrchestrator:
    """
    Orchestrate event flow through the pipeline
    """
    
    def __init__(self, kafka_handler: KafkaEventHandler):
        self.kafka = kafka_handler
        
    def process_document_pipeline(
        self,
        document_id: str,
        document_path: str,
        document_type: str
    ) -> str:
        """
        Trigger complete document processing pipeline
        """
        # Generate correlation ID for tracking
        correlation_id = self._generate_correlation_id()
        
        # Step 1: Publish document received event
        self.kafka.publish_event(
            event_type=EventType.DOCUMENT_RECEIVED,
            data={
                'document_id': document_id,
                'document_path': document_path,
                'document_type': document_type
            },
            source='document_ingestion_service',
            correlation_id=correlation_id,
            partition_key=document_id
        )
        
        logger.info(
            f"Started document pipeline for {document_id} "
            f"(correlation_id: {correlation_id})"
        )
        
        return correlation_id
    
    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for event tracking"""
        import uuid
        return f"CORR-{uuid.uuid4()}"
    
    def setup_pipeline_handlers(self):
        """
        Setup event handlers for the complete pipeline
        """
        # OCR completion handler
        def handle_ocr_completed(event: Event):
            logger.info(f"OCR completed for document {event.data.get('document_id')}")
            
            # Trigger entity extraction
            self.kafka.publish_event(
                event_type=EventType.ENTITY_EXTRACTED,
                data={
                    'document_id': event.data.get('document_id'),
                    'extracted_text': event.data.get('text'),
                    'confidence': event.data.get('confidence')
                },
                source='entity_extraction_service',
                correlation_id=event.correlation_id
            )
        
        # Entity extraction handler
        def handle_entity_extracted(event: Event):
            logger.info(f"Entities extracted for document {event.data.get('document_id')}")
            
            # Trigger anomaly detection
            self.kafka.publish_event(
                event_type=EventType.ANOMALY_DETECTED,
                data=event.data,
                source='anomaly_detection_service',
                correlation_id=event.correlation_id
            )
        
        # Anomaly detection handler
        def handle_anomaly_detected(event: Event):
            logger.info(f"Anomaly check completed for document {event.data.get('document_id')}")
            
            if not event.data.get('is_anomaly'):
                # Trigger FHIR conversion
                self.kafka.publish_event(
                    event_type=EventType.FHIR_CONVERTED,
                    data=event.data,
                    source='fhir_conversion_service',
                    correlation_id=event.correlation_id
                )
        
        # FHIR conversion handler
        def handle_fhir_converted(event: Event):
            logger.info(f"FHIR conversion completed for document {event.data.get('document_id')}")
            
            # Trigger privacy check
            self.kafka.publish_event(
                event_type=EventType.PRIVACY_CHECKED,
                data=event.data,
                source='privacy_service',
                correlation_id=event.correlation_id
            )
        
        # Privacy check handler
        def handle_privacy_checked(event: Event):
            logger.info(f"Privacy check completed for document {event.data.get('document_id')}")
            
            if event.data.get('access_allowed'):
                # Trigger hub update
                self.kafka.publish_event(
                    event_type=EventType.HUB_UPDATED,
                    data=event.data,
                    source='hub_integration_service',
                    correlation_id=event.correlation_id
                )
        
        # Register all handlers
        self.kafka.register_handler(EventType.OCR_COMPLETED, handle_ocr_completed)
        self.kafka.register_handler(EventType.ENTITY_EXTRACTED, handle_entity_extracted)
        self.kafka.register_handler(EventType.ANOMALY_DETECTED, handle_anomaly_detected)
        self.kafka.register_handler(EventType.FHIR_CONVERTED, handle_fhir_converted)
        self.kafka.register_handler(EventType.PRIVACY_CHECKED, handle_privacy_checked)
        
        logger.info("Pipeline handlers configured")


# Example usage
if __name__ == "__main__":
    config = {
        'bootstrap_servers': ['localhost:9092']
    }
    
    # Initialize Kafka handler
    kafka_handler = KafkaEventHandler(config)
    
    # Create topics
    kafka_handler.create_topics()
    
    # Initialize orchestrator
    orchestrator = EventOrchestrator(kafka_handler)
    orchestrator.setup_pipeline_handlers()
    
    # Process a document
    correlation_id = orchestrator.process_document_pipeline(
        document_id='DOC123',
        document_path='/path/to/document.pdf',
        document_type='PRIOR_AUTHORIZATION'
    )
    
    print(f"Pipeline started with correlation ID: {correlation_id}")
    
    # Start consuming events
    # kafka_handler.consume_events(
    #     topics=list(kafka_handler.topics.values()),
    #     group_id='payerhub-consumer-group'
    # )

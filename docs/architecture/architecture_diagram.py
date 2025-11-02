"""
PayerHub Integration Architecture Diagram Generator
Creates a comprehensive visual representation of the event-driven payer data integration system
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.database import PostgreSQL, MongoDB
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Kafka
from diagrams.programming.framework import FastAPI
from diagrams.programming.language import Python
from diagrams.custom import Custom
from diagrams.onprem.compute import Server
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.generic.storage import Storage
from diagrams.generic.blank import Blank

# Custom node colors
graph_attr = {
    "fontsize": "16",
    "bgcolor": "white",
    "pad": "0.5",
    "splines": "ortho"
}

with Diagram("PayerHub Integration - Event-Driven Architecture", 
             show=False, 
             filename="diagrams/payerhub_architecture",
             direction="LR",
             graph_attr=graph_attr):
    
    # External Systems
    with Cluster("Payer Systems"):
        payer_api = Server("Payer APIs\n(FHIR/REST)")
        payer_fax = Storage("Fax/PDF\nDocuments")
        payer_email = Storage("Email\nAttachments")
    
    # API Gateway Layer
    with Cluster("API Gateway Layer"):
        api_gateway = Nginx("API Gateway\n(Rate Limiting,\nAuth)")
        load_balancer = Nginx("Load Balancer")
    
    # Ingestion Layer
    with Cluster("Data Ingestion Layer"):
        document_ingestion = FastAPI("Document\nIngestion\nService")
        api_connector = FastAPI("FHIR API\nConnector")
    
    # AI/ML Processing Layer
    with Cluster("AI/ML Data Processing"):
        with Cluster("OCR & Extraction"):
            ocr_service = Python("OCR Engine\n(Tesseract,\nLayoutLM)")
            nlp_service = Python("NLP Service\n(BioBERT,\nClinicalBERT)")
        
        with Cluster("Entity Recognition"):
            ner_service = Python("NER Service\n(Patient, Payer,\nDrug, Dates)")
            entity_linker = Python("Entity Linker\n(SNOMED,\nLOINC)")
        
        with Cluster("Data Quality"):
            anomaly_detector = Python("Anomaly\nDetector\n(Isolation\nForest)")
            validation_service = Python("Schema\nValidator")
    
    # Event Stream Processing
    with Cluster("Event Middleware"):
        kafka_cluster = Kafka("Kafka\n(Event Streaming)")
        redis_cache = Redis("Redis\n(Session Cache)")
    
    # FHIR Transformation Layer
    with Cluster("FHIR Transformation"):
        fhir_mapper = Python("FHIR Mapper\n(Convert to\nFHIR Resources)")
        fhir_validator = Python("FHIR Validator")
    
    # Privacy & Consent Layer
    with Cluster("Privacy & Compliance"):
        privacy_manager = Server("Privacy\nManager\n(HIPAA)")
        consent_service = Server("Consent\nService")
        audit_logger = Server("Audit Logger")
    
    # Hub CRM Integration
    with Cluster("Patient Service Hub"):
        hub_crm = Server("Hub CRM\n(Salesforce/\nCustom)")
        case_manager_ui = Server("Case Manager\nDashboard")
        notification_service = Server("Notification\nService")
    
    # Data Storage
    with Cluster("Data Storage"):
        postgres = PostgreSQL("PostgreSQL\n(Structured Data)")
        mongo = MongoDB("MongoDB\n(Documents)")
        s3_storage = Storage("S3/Blob\n(Raw Documents)")
    
    # Monitoring & Observability
    with Cluster("Monitoring"):
        prometheus = Prometheus("Prometheus")
        grafana = Grafana("Grafana")
    
    # ML Model Repository
    ml_registry = Storage("ML Model\nRegistry\n(MLflow)")
    
    # Flow Connections
    # Payer to Gateway
    payer_api >> Edge(label="FHIR API") >> api_gateway
    payer_fax >> Edge(label="PDF/TIFF") >> api_gateway
    payer_email >> Edge(label="Attachments") >> api_gateway
    
    # Gateway to Ingestion
    api_gateway >> load_balancer
    load_balancer >> document_ingestion
    load_balancer >> api_connector
    
    # Ingestion to AI Processing
    document_ingestion >> Edge(label="Raw Docs") >> ocr_service
    api_connector >> Edge(label="FHIR Data") >> validation_service
    
    # AI Processing Flow
    ocr_service >> Edge(label="Extracted Text") >> nlp_service
    nlp_service >> Edge(label="Entities") >> ner_service
    ner_service >> entity_linker
    
    entity_linker >> Edge(label="Structured Data") >> anomaly_detector
    document_ingestion >> validation_service
    
    # Anomaly Detection to Event Stream
    anomaly_detector >> Edge(label="Validated Data") >> kafka_cluster
    validation_service >> kafka_cluster
    
    # Kafka to FHIR Transformation
    kafka_cluster >> Edge(label="Events") >> fhir_mapper
    fhir_mapper >> fhir_validator
    
    # FHIR to Privacy Layer
    fhir_validator >> Edge(label="FHIR Resources") >> privacy_manager
    privacy_manager >> consent_service
    
    # Privacy to Hub CRM
    consent_service >> Edge(label="Authorized Data") >> hub_crm
    hub_crm >> case_manager_ui
    hub_crm >> notification_service
    
    # Storage Connections
    document_ingestion >> s3_storage
    fhir_mapper >> postgres
    anomaly_detector >> mongo
    
    # Cache Connection
    api_connector >> redis_cache
    hub_crm >> redis_cache
    
    # Audit Logging
    privacy_manager >> audit_logger
    audit_logger >> postgres
    
    # ML Registry
    anomaly_detector >> ml_registry
    ner_service >> ml_registry
    
    # Monitoring
    [document_ingestion, api_connector, fhir_mapper, hub_crm] >> prometheus
    prometheus >> grafana

print("Architecture diagram generated successfully!")
print("Output: diagrams/payerhub_architecture.png")

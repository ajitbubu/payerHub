# PayerHub Integration Platform

## Event-Driven Real-Time Integration of Payer Data with Patient Service Hubs

A comprehensive, production-ready platform for automating the integration of insurance payer data with patient service hubs using AI/ML, FHIR standards, and event-driven architecture.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Usage](#usage)
9. [API Documentation](#api-documentation)
10. [Pipeline Components](#pipeline-components)
11. [Deployment](#deployment)
12. [Monitoring](#monitoring)
13. [Security & Compliance](#security--compliance)
14. [Contributing](#contributing)
15. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

### The Problem

Patient service hubs (used by pharmaceutical manufacturers and specialty pharmacies) currently rely on manual processes to:
- Verify insurance eligibility
- Track prior authorization status
- Monitor claims and appeals
- Coordinate specialty pharmacy services

This involves phone calls, faxes, portal lookups, and manual data entry - leading to delays, errors, and poor patient experiences.

### The Solution

PayerHub Integration automates this workflow using:

1. **AI/ML Pipeline**: OCR + NLP to extract data from unstructured documents
2. **FHIR Conversion**: Standardized healthcare data format
3. **Event-Driven Architecture**: Real-time processing with Kafka
4. **Privacy Layer**: HIPAA-compliant consent and access management
5. **Anomaly Detection**: Data quality validation

---

## 🏗 Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Payer Systems  │
│  (API/Fax/PDF)  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway Layer                         │
│              (FastAPI, Rate Limiting, Authentication)            │
└────────┬────────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                    Data Ingestion Layer                         │
│          (Document Upload, File Processing, Routing)            │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                   AI/ML Processing Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ OCR Engine   │→ │ NLP/NER      │→ │ Entity       │        │
│  │ (LayoutLM)   │  │ (BioBERT)    │  │ Linker       │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                  Anomaly Detection Layer                        │
│        (Isolation Forest, Autoencoder, Rule-Based)             │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                   Event Middleware (Kafka)                      │
│              (Real-time Event Streaming & Routing)              │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                  FHIR Transformation Layer                      │
│      (Convert to FHIR R4 Resources: Claim, Coverage, etc.)     │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│               Privacy & Consent Management                      │
│         (HIPAA Compliance, Audit Logging, Access Control)      │
└────────┬───────────────────────────────────────────────────────┘
         │
         ↓
┌────────────────────────────────────────────────────────────────┐
│                    Hub CRM Integration                          │
│          (Salesforce, Custom CRM, Case Management)             │
└────────────────────────────────────────────────────────────────┘
```

### Generate Architecture Diagram

```bash
python docs/architecture/architecture_diagram.py
```

This will generate a detailed visual diagram in `docs/architecture/payerhub_architecture.png`.

---

## 📁 Project Structure

```
payerHub/
├── src/                       # Source code
│   ├── api/                  # API Gateway (FastAPI)
│   ├── core/                 # Core business logic
│   │   ├── ai_pipeline/     # OCR & NLP processing
│   │   ├── anomaly_detection/ # Data quality validation
│   │   ├── fhir_mapper/     # FHIR conversion
│   │   └── privacy_layer/   # Privacy & consent management
│   ├── integrations/         # External integrations (payers, hubs)
│   ├── infrastructure/       # Event streaming (Kafka)
│   └── web/                  # Web UI
├── tests/                     # Test files
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── e2e/                  # End-to-end tests
├── docs/                      # Documentation
│   ├── architecture/         # Architecture diagrams
│   ├── guides/               # User & developer guides
│   ├── api/                  # API documentation
│   └── papers/               # Research papers
├── scripts/                   # Utility scripts
├── config/                    # Configuration files
├── deployments/              # Deployment configurations
│   ├── docker/              # Docker files
│   └── kubernetes/          # K8s manifests
├── data/                      # Sample data
│   └── samples/             # Sample documents
├── .env.example              # Environment variables template
├── docker-compose.yml        # Docker Compose configuration
├── requirements.txt          # Python dependencies
├── setup.py                  # Package setup
└── README.md                 # This file
```

---

## ✨ Features

### Core Capabilities

- **Document Processing**
  - OCR extraction from PDFs, faxes, images
  - Advanced layout understanding (LayoutLMv3)
  - Multi-page document processing

- **NLP & Entity Extraction**
  - BioBERT for biomedical text
  - Clinical entity recognition
  - SNOMED/LOINC code linking
  - Patient, insurance, and clinical data extraction

- **Data Quality & Validation**
  - ML-based anomaly detection
  - Rule-based validation
  - Cross-field consistency checks
  - Automatic flagging for manual review

- **FHIR Standards**
  - FHIR R4 resource creation
  - Support for: Claim, Coverage, Patient, Organization
  - Prior authorization handling
  - Eligibility verification

- **Privacy & Security**
  - HIPAA-compliant consent management
  - Role-based access control
  - Complete audit logging
  - PHI masking and de-identification

- **Event-Driven Architecture**
  - Real-time Kafka event streaming
  - Asynchronous processing
  - Retry and dead-letter queue handling
  - Correlation ID tracking

---

## 📦 Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **Tesseract OCR** (for document processing)
- **PostgreSQL 15+** (for structured data)
- **Redis 7+** (for caching)
- **Kafka 3+** (for event streaming)
- **8GB+ RAM** (for ML models)
- **GPU** (optional, for faster processing)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd payerHub
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy models
python -m spacy download en_core_web_sm
```

### 3. Start Infrastructure with Docker

```bash
# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

This will start:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Kafka & Zookeeper (port 9092)
- MongoDB (port 27017)
- Prometheus (port 9090)
- Grafana (port 3000)
- Kafka UI (port 8080)
- MinIO (port 9000)

### 4. Initialize Database

```bash
# Create tables
python scripts/init_database.py
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

---

## ⚙ Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://payerhub_user:password@localhost:5432/payerhub

# AI/ML Models
USE_GPU=false  # Set to true if GPU available
OCR_MODEL=microsoft/layoutlmv3-base
NLP_MODEL=dmis-lab/biobert-base-cased-v1.1

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Security
JWT_SECRET_KEY=<your-secret-key>
```

### Model Configuration

Edit `src/orchestrator.py` to customize AI/ML models:

```python
config = {
    'ocr': {
        'layoutlm_model': 'microsoft/layoutlmv3-base',
        'use_gpu': True  # Enable if GPU available
    },
    'nlp': {
        'biobert_model': 'dmis-lab/biobert-base-cased-v1.1',
        'use_gpu': True
    }
}
```

---

## 📖 Usage

### Starting the API Server

```bash
# Development mode (with auto-reload)
uvicorn src.api_gateway.gateway:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn src.api_gateway.gateway:app --workers 4 --host 0.0.0.0 --port 8000
```

### API Endpoints

Base URL: `http://localhost:8000`

#### Authentication

```bash
# Get authentication token
curl -X POST "http://localhost:8000/api/v1/auth/token" \
  -d "user_id=USER001&organization_id=ORG789"
```

#### Upload Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -H "document_info: {\"document_type\":\"PRIOR_AUTHORIZATION\",\"patient_id\":\"PAT123\",\"organization_id\":\"ORG789\"}" \
  -F "file=@prior_auth.pdf"
```

#### Check Processing Status

```bash
curl -X GET "http://localhost:8000/api/v1/documents/DOC123/status" \
  -H "Authorization: Bearer <token>"
```

### Python SDK Usage

```python
from src.orchestrator import PayerHubOrchestrator
import asyncio

async def process_document():
    orchestrator = PayerHubOrchestrator()
    
    result = await orchestrator.process_document(
        file_path='/path/to/document.pdf',
        document_type='PRIOR_AUTHORIZATION',
        patient_id='PAT123456',
        organization_id='ORG789',
        user_id='USER001'
    )
    
    print(f"Status: {result['status']}")
    print(f"Correlation ID: {result['correlation_id']}")
    
    orchestrator.close()

asyncio.run(process_document())
```

---

## 🔄 Pipeline Components

### 1. OCR Processor (`src/ai_pipeline/ocr_processor.py`)

Extracts text from unstructured documents.

**Features:**
- Tesseract + LayoutLMv3 integration
- Image preprocessing (denoising, thresholding)
- Multi-page PDF support
- Confidence scoring

**Usage:**
```python
from src.ai_pipeline.ocr_processor import OCRProcessor

processor = OCRProcessor(config)
result = processor.process_pdf('/path/to/document.pdf')

print(f"Confidence: {result.confidence}")
print(f"Document Type: {result.document_type}")
print(f"Extracted Text: {result.text[:500]}")
```

### 2. Entity Extractor (`src/ai_pipeline/entity_extractor.py`)

Extracts structured entities from text using NLP.

**Features:**
- BioBERT for medical entities
- spaCy for general entities
- SciSpacy for UMLS linking
- Regex patterns for codes (ICD, CPT, NDC)

**Usage:**
```python
from src.ai_pipeline.entity_extractor import EntityExtractor

extractor = EntityExtractor(config)
result = extractor.extract_all(text)

print(f"Patient Info: {result.patient_info}")
print(f"Insurance Info: {result.insurance_info}")
print(f"Clinical Info: {result.clinical_info}")
```

### 3. Anomaly Detector (`src/anomaly_detection/detector.py`)

Validates data quality and detects anomalies.

**Features:**
- Isolation Forest
- Autoencoder neural network
- Rule-based validation
- Cross-field consistency checks

**Usage:**
```python
from src.anomaly_detection.detector import DataQualityDetector

detector = DataQualityDetector(config)
result = detector.detect(data)

if result.is_anomaly:
    print(f"Anomaly Type: {result.anomaly_type}")
    print(f"Issues: {result.issues}")
```

### 4. FHIR Mapper (`src/fhir_mapper/mapper.py`)

Converts extracted data to FHIR R4 resources.

**Features:**
- Support for Claim, Coverage, Patient, Organization
- Prior authorization handling
- Eligibility verification
- FHIR validation

**Usage:**
```python
from src.fhir_mapper.mapper import FHIRMapper

mapper = FHIRMapper(config)
result = mapper.convert_to_fhir(extracted_data)

print(f"Resource Type: {result.resource_type}")
print(f"Resource ID: {result.resource_id}")
print(f"FHIR JSON: {result.fhir_resource.json()}")
```

### 5. Privacy Manager (`src/privacy_layer/privacy_manager.py`)

Manages consent and access control.

**Features:**
- HIPAA-compliant consent tracking
- PHI masking
- Audit logging
- Role-based access control

**Usage:**
```python
from src.privacy_layer.privacy_manager import PrivacyManager

manager = PrivacyManager(config)

# Create consent
consent = manager.create_consent(
    patient_id='PAT123',
    organization_id='ORG789',
    purpose='treatment',
    scope=['full_access']
)

# Check access
result = manager.check_access(
    user_id='USER001',
    patient_id='PAT123',
    organization_id='ORG789',
    purpose='treatment',
    requested_scope=['full_access']
)

print(f"Access Allowed: {result.allowed}")
```

### 6. Kafka Event Handler (`src/event_middleware/kafka_handler.py`)

Handles event streaming and orchestration.

**Features:**
- Event publishing and consumption
- Correlation ID tracking
- Dead letter queue
- Event handlers registry

**Usage:**
```python
from src.event_middleware.kafka_handler import KafkaEventHandler, EventType

handler = KafkaEventHandler(config)

# Publish event
handler.publish_event(
    event_type=EventType.DOCUMENT_RECEIVED,
    data={'document_id': 'DOC123'},
    source='api_gateway'
)

# Register handler
def handle_event(event):
    print(f"Received: {event.event_type}")

handler.register_handler(EventType.OCR_COMPLETED, handle_event)
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build image
docker build -t payerhub:latest .

# Run container
docker run -d \
  --name payerhub-api \
  -p 8000:8000 \
  --env-file .env \
  payerhub:latest
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests.

```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods
```

### Production Checklist

- [ ] Set strong JWT secret key
- [ ] Configure SSL/TLS certificates
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Set up monitoring alerts
- [ ] Enable rate limiting
- [ ] Review security settings
- [ ] Test disaster recovery

---

## 📊 Monitoring

### Prometheus Metrics

Access Prometheus at: `http://localhost:9090`

Key metrics:
- API request rate
- Processing latency
- Error rates
- Kafka lag
- Database connections

### Grafana Dashboards

Access Grafana at: `http://localhost:3000` (admin/admin)

Pre-configured dashboards:
- API Performance
- Pipeline Metrics
- Infrastructure Health
- Error Tracking

### Kafka Monitoring

Access Kafka UI at: `http://localhost:8080`

Monitor:
- Topic messages
- Consumer lag
- Broker status

---

## 🔒 Security & Compliance

### HIPAA Compliance

- **Encryption at Rest**: PostgreSQL + MinIO encryption
- **Encryption in Transit**: TLS for all connections
- **Access Control**: JWT-based authentication
- **Audit Logging**: Complete audit trail in database
- **Data Minimization**: PHI masking based on access level
- **Consent Management**: Explicit patient consent tracking

### Security Best Practices

1. Rotate JWT secrets regularly
2. Use separate database credentials per service
3. Enable network segmentation
4. Implement IP whitelisting
5. Regular security audits
6. Monitor audit logs

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest`
5. Commit: `git commit -m "Add amazing feature"`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

---

## 🐛 Troubleshooting

### Common Issues

#### OCR not working
```bash
# Install Tesseract
# macOS:
brew install tesseract

# Ubuntu:
sudo apt-get install tesseract-ocr
```

#### Kafka connection failed
```bash
# Check Kafka is running
docker-compose ps kafka

# View logs
docker-compose logs kafka
```

#### GPU not detected
```bash
# Install CUDA toolkit
# Verify GPU access
python -c "import torch; print(torch.cuda.is_available())"
```

### Logs

```bash
# View API logs
docker-compose logs -f api-gateway

# View all logs
docker-compose logs -f
```

---

## 📞 Support

For issues, questions, or contributions:
- Create an issue in the repository
- Contact: engineering@payerhub.com

---

## 📄 License

[Add your license here]

---

## 🙏 Acknowledgments

- FHIR standard by HL7
- BioBERT by DMIS Lab
- LayoutLM by Microsoft Research
- Open source community

---

**Built with ❤️ for healthcare interoperability**

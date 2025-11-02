# PayerHub Refactoring Plan

## Current Issues
- Too many markdown files in root directory
- Documentation scattered across multiple files
- Scripts mixed with documentation
- No clear separation of concerns

## Proposed Structure

```
payerHub/
├── .github/                    # GitHub workflows and templates
├── docs/                       # All documentation
│   ├── architecture/          # Architecture diagrams and docs
│   ├── guides/                # User and developer guides
│   ├── api/                   # API documentation
│   └── papers/                # Research papers
├── src/                       # Source code
│   ├── api/                   # API layer (renamed from api_gateway)
│   ├── core/                  # Core business logic
│   │   ├── ai_pipeline/
│   │   ├── anomaly_detection/
│   │   ├── fhir_mapper/
│   │   └── privacy_layer/
│   ├── integrations/          # External integrations (renamed from connectors)
│   ├── infrastructure/        # Infrastructure code (renamed from event_middleware)
│   └── web/                   # Web UI (moved from static/)
├── tests/                     # Test files
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                   # Utility scripts
├── config/                    # Configuration files
├── deployments/               # Deployment configs
│   ├── docker/
│   └── kubernetes/
├── data/                      # Sample data (renamed from sample_documents)
│   └── samples/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
└── setup.py
```

## Changes to Make

### 1. Consolidate Documentation
- Move all .md files from root to docs/guides/
- Organize architecture diagrams
- Create clear documentation structure

### 2. Reorganize Source Code
- Rename api_gateway → api
- Group connectors under integrations/
- Move static/ → src/web/
- Create core/ for business logic

### 3. Clean Up Root Directory
- Keep only essential files in root
- Move scripts to scripts/
- Move docker files to deployments/

### 4. Improve Test Structure
- Create test subdirectories
- Add test fixtures

### 5. Add Missing Files
- setup.py for package installation
- CONTRIBUTING.md
- CHANGELOG.md
- LICENSE

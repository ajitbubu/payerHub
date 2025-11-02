# PayerHub Quick Start Guide

## What We've Set Up

Your PayerHub Integration Platform is now running! Here's what's been configured:

### ✅ Completed Setup

1. **Git Repository** - Initialized and pushed to GitHub
2. **Environment Configuration** - `.env` file created with all necessary variables
3. **Python Virtual Environment** - Created with Python 3.9
4. **Core Dependencies** - Installed FastAPI, Uvicorn, Pydantic, and other essentials
5. **API Gateway** - Running on http://localhost:8000

### 🚀 Running Application

The API server is currently running at:
- **API Base URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 📊 Current Status

```bash
# Check API health
curl http://localhost:8000/health

# View API info
curl http://localhost:8000/
```

**Health Status:**
- ✅ API Gateway: Running
- ⚠️  Redis: Not running (optional for basic testing)
- ⚠️  Kafka: Not running (optional for basic testing)
- ⚠️  PostgreSQL: Not running (optional for basic testing)

### 🔧 Quick Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the API server
python3 run_api.py

# Or use uvicorn directly
uvicorn src.api_gateway.gateway:app --reload --host 0.0.0.0 --port 8000

# Test the API
curl http://localhost:8000/
curl http://localhost:8000/health
```

### 📝 Available API Endpoints

1. **Health & Status**
   - `GET /` - Service info
   - `GET /health` - Health check

2. **Authentication**
   - `POST /api/v1/auth/token` - Get auth token

3. **Documents**
   - `POST /api/v1/documents/upload` - Upload document for processing
   - `GET /api/v1/documents/{id}/status` - Check processing status

4. **FHIR**
   - `POST /api/v1/fhir/convert` - Convert data to FHIR format

5. **Patients**
   - `GET /api/v1/patients/{id}/documents` - Get patient documents

6. **Consent**
   - `POST /api/v1/consent/create` - Create consent record

### 🐳 Starting Full Infrastructure (Optional)

To run with all services (PostgreSQL, Redis, Kafka, etc.):

```bash
# Start all Docker services
docker-compose up -d

# Check services status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 📚 Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation where you can:
- View all endpoints
- Test API calls directly
- See request/response schemas
- Try authentication flows

### 🧪 Testing the API

#### 1. Get Authentication Token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/token?user_id=USER001&organization_id=ORG789"
```

#### 2. Use Token for Authenticated Requests

```bash
# Save token
TOKEN="your-token-here"

# Make authenticated request
curl -X GET "http://localhost:8000/api/v1/patients/PAT123/documents" \
  -H "Authorization: Bearer $TOKEN"
```

### 📦 Project Structure

```
payerHub/
├── src/
│   ├── ai_pipeline/          # OCR & NLP processing
│   ├── anomaly_detection/    # Data quality checks
│   ├── api_gateway/          # FastAPI gateway (RUNNING)
│   ├── connectors/           # Payer & Hub integrations
│   ├── event_middleware/     # Kafka event handling
│   ├── fhir_mapper/          # FHIR conversion
│   ├── privacy_layer/        # Consent & privacy
│   └── orchestrator.py       # Main pipeline orchestrator
├── config/                   # Configuration files
├── docs/                     # Documentation
├── examples/                 # Example workflows
├── tests/                    # Test files
├── .env                      # Environment variables
├── docker-compose.yml        # Docker services
├── requirements.txt          # Python dependencies
└── run_api.py               # Simple API runner
```

### 🔍 Next Steps

1. **Start Full Infrastructure** (if needed):
   ```bash
   docker-compose up -d postgres redis kafka
   ```

2. **Install ML Dependencies** (for full AI/ML features):
   ```bash
   pip install torch transformers pytesseract pdf2image opencv-python
   ```

3. **Configure Payer Connectors**:
   - Update `.env` with actual API credentials
   - Configure `config/connectors.yml`

4. **Test Document Processing**:
   - Upload a sample PDF through the API
   - Monitor processing pipeline

### 🛠️ Troubleshooting

**API won't start:**
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill process if needed
kill -9 <PID>
```

**Missing dependencies:**
```bash
# Reinstall requirements
pip install -r requirements.txt
```

**Docker services not starting:**
```bash
# Check Docker is running
docker ps

# View service logs
docker-compose logs <service-name>
```

### 📞 Support

- Check the main README.md for detailed documentation
- View API docs at http://localhost:8000/docs
- Check logs in the terminal where the API is running

---

**Status**: ✅ API Gateway Running Successfully!
**Last Updated**: October 26, 2025

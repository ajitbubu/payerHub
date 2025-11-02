# Getting Started with PayerHub

This guide will help you get PayerHub up and running quickly.

## Prerequisites

- Python 3.9 or higher
- Docker and Docker Compose (optional, for full stack)
- 8GB+ RAM
- Git

## Quick Start (API Only)

### 1. Clone the Repository

```bash
git clone https://github.com/ajitbubu/payerHub.git
cd payerHub
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional for basic testing)
nano .env
```

### 4. Run the API

```bash
python run_api.py
```

The API will be available at:
- API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Web UI: http://localhost:8001

## Full Stack Setup (with Docker)

### 1. Start Infrastructure Services

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

This starts:
- PostgreSQL (database)
- Redis (caching)
- Kafka (event streaming)
- MongoDB (document storage)
- Prometheus (monitoring)
- Grafana (visualization)

### 2. Run the API

```bash
python run_api.py
```

## Testing the API

### Using the Web UI

1. Open http://localhost:8001 in your browser
2. Upload a sample document from `data/samples/`
3. View processing results

### Using cURL

```bash
# Health check
curl http://localhost:8001/health

# Get auth token
curl -X POST "http://localhost:8001/api/v1/auth/token?user_id=USER001&organization_id=ORG789"

# Upload document
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data/samples/sample_prior_auth.txt" \
  -F "document_type=PRIOR_AUTHORIZATION" \
  -F "patient_id=PAT123" \
  -F "organization_id=ORG789"
```

### Using the Interactive API Docs

Visit http://localhost:8001/docs for Swagger UI where you can:
- Explore all endpoints
- Test API calls interactively
- View request/response schemas

## Next Steps

- Read the [Architecture Guide](../architecture/README.md)
- Explore [API Documentation](../api/README.md)
- Check out [Example Workflows](../../examples/)
- Review [Configuration Options](CONFIGURATION.md)

## Troubleshooting

### Port Already in Use

```bash
# Check what's using port 8001
lsof -i :8001

# Kill the process
kill -9 <PID>
```

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

### Docker Services Not Starting

```bash
# View logs
docker-compose logs <service-name>

# Restart services
docker-compose restart
```

## Getting Help

- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review [FAQ](FAQ.md)
- Open an issue on GitHub

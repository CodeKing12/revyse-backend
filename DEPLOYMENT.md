# Revyse Backend - Deployment Guide

## Quick Start with Docker (Recommended)

### 1. Prerequisites
- Docker and Docker Compose installed
- API keys for Google Gemini or OpenRouter

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/CodeKing12/revyse-backend.git
cd revyse-backend

# Create environment file
cp .env.example .env

# Edit .env with your API keys and secrets
nano .env
```

### 3. Deploy
```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Verify OCR is Working
```bash
curl http://localhost:8000/admin/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "ai_service": "available",
    "ai_provider": "gemini",
    "file_service": "available"
  },
  "ocr_capabilities": {
    "pdf2image_available": true,
    "pytesseract_available": true,
    "local_ocr_ready": true,
    "ai_vision_available": true,
    "recommendation": "Local OCR ready (FREE)"
  }
}
```

---

## Manual Server Setup (Ubuntu/Debian)

### 1. Install System Dependencies
```bash
# Update packages
sudo apt-get update

# Install Python 3.11
sudo apt-get install python3.11 python3.11-venv python3-pip

# Install OCR dependencies (FREE)
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils

# Install PostgreSQL (optional, can use external DB)
sudo apt-get install postgresql postgresql-contrib
```

### 2. Setup Application
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install pdf2image pytesseract

# Setup environment
cp .env.example .env
nano .env  # Edit with your values
```

### 3. Run with Gunicorn (Production)
```bash
pip install gunicorn

# Run with 4 workers
gunicorn app.core.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## Cloud Platform Deployments

### Railway / Render / Fly.io
These platforms support Docker, so the Dockerfile will work automatically.

Add these environment variables in the platform's dashboard:
- `GOOGLE_API_KEY` or `OPENROUTER_API_KEY`
- `SECRET_KEY`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

### Heroku
Add buildpacks for Tesseract:
```bash
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-apt
```

Create `Aptfile`:
```
tesseract-ocr
tesseract-ocr-eng
poppler-utils
```

### AWS / GCP / Azure
Use the Docker image or install Tesseract via your infrastructure-as-code:

**Terraform (AWS EC2):**
```hcl
resource "aws_instance" "api" {
  user_data = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y tesseract-ocr poppler-utils
  EOF
}
```

---

## OCR Fallback Behavior

The system handles OCR with a smart fallback chain:

| Priority | Method | Cost | Requirement |
|----------|--------|------|-------------|
| 1 | PyPDF2 (text layer) | FREE | None |
| 2 | Tesseract OCR | FREE | Tesseract installed |
| 3 | Gemini AI Vision | ~$0.0001/page | GOOGLE_API_KEY |

If Tesseract isn't available, the system automatically falls back to Gemini Vision.

---

## Troubleshooting

### "Tesseract not found"
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Check installation
tesseract --version
```

### "pdf2image: Unable to get page count"
```bash
# Install poppler (required for PDF to image conversion)
sudo apt-get install poppler-utils

# Verify
pdftoppm -v
```

### OCR returns empty text
- Check if the PDF is actually scanned (not just empty)
- Try increasing DPI in `_extract_pdf_with_ocr` (default: 200)
- Ensure the correct language pack is installed: `tesseract-ocr-eng`

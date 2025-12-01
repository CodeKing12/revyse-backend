# Production Dockerfile for Revyse Backend
# Includes Tesseract OCR and Poppler for scanned PDF support

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for OCR
# - tesseract-ocr: For text recognition from images
# - poppler-utils: For converting PDF pages to images (pdf2image)
# - libpq-dev: For PostgreSQL support
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install OCR-specific packages
RUN pip install --no-cache-dir pdf2image pytesseract

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p /app/uploads

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/admin/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.core.main:app", "--host", "0.0.0.0", "--port", "8000"]

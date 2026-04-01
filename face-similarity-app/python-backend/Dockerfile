FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Create temp_uploads directory
RUN mkdir -p temp_uploads

# Expose port
EXPOSE 5001

# Run with gunicorn
# --workers 1       : Single worker — TF/ONNX models are large; multiple workers multiply RAM usage
# --threads 4       : Handle concurrent requests within the single worker
# --timeout 600     : 10 min — face comparison + model init can be slow
# --graceful-timeout 120 : Give worker time to finish in-flight requests on shutdown
# --preload         : Load app (and trigger startup thread) before forking workers
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "4", "--timeout", "600", "--graceful-timeout", "120", "--worker-class", "gthread", "--preload", "app_v2:app"]

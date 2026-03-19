FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for audio processing + curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libportaudio2 \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Default command: run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

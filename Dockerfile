FROM python:3.13-slim

WORKDIR /app

# Install system dependencies for scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY config.py .
COPY pipeline/ ./pipeline/
COPY ml/ ./ml/
COPY api/ ./api/
COPY models/ ./models/

# Expose FastAPI port
EXPOSE 8000

# Run the API
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

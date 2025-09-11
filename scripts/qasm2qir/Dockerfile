FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies (may be needed for qiskit-aer)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY qasm2qir.py .

# Cloud Run expects listening on 0.0.0.0:8080
ENV PORT=8080
CMD ["python", "qasm2qir.py"]

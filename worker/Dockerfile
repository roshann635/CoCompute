FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Install worker requirements (headless mode)
COPY worker/requirements.txt requirements.txt
RUN pip install --no-cache-dir psutil==6.0.0 websockets==13.0 httpx==0.27.0

# Copy shared sdk, master utilities for integrity/auth, and worker application
COPY shared/ ./shared/
COPY master/ ./master/
COPY worker/ ./worker/
COPY worker/app/ ./app/

ENV PYTHONPATH=/app
ENV MASTER_IP=master
ENV MASTER_PORT=8000
ENV WORKER_API_KEY=cocompute-worker-key
ENV COCOMPUTE_WORKER_SECRET=cocompute-default-cluster-secret-2026

CMD ["python", "-m", "app.main"]

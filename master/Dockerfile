FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for psycopg2 and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY master/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared sdk, master application, and package root
COPY shared/ ./shared/
COPY master/ ./master/
COPY master/app/ ./app/

ENV PYTHONPATH=/app

EXPOSE 8000 9999/udp

# Persistent storage for job result files
RUN mkdir -p /app/storage/results
VOLUME /app/storage

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=15s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

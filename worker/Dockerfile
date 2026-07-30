FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Worker needs access to Docker socket for sandboxed execution
# Mount /var/run/docker.sock from host when running via docker-compose

CMD ["python", "-m", "app.main"]

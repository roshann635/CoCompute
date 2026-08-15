# CoCompute Task Image: Distributed Inference
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir torch torchvision pynvml numpy
COPY . /app/
ENTRYPOINT ["python", "execute.py"]

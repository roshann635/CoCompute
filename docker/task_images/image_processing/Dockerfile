# CoCompute Task Image: Image Processing
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir Pillow numpy
COPY . /app/
ENTRYPOINT ["python", "execute.py"]

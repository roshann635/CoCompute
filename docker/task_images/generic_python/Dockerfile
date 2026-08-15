# CoCompute Task Image: Generic Python Custom Task
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy scipy Pillow
COPY . /app/
ENTRYPOINT ["python", "execute.py"]

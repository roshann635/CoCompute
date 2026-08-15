# CoCompute Task Image: Matrix Multiplication
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir numpy scipy
COPY . /app/
ENTRYPOINT ["python", "execute.py"]

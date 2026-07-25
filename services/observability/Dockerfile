FROM python:3.12-slim
WORKDIR /app
COPY services/observability/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/observability/src/ ./src/
CMD ["uvicorn", "src.metrics:app", "--host", "0.0.0.0", "--port", "8500"]

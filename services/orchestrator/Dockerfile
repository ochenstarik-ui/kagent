FROM python:3.12-slim
WORKDIR /app
COPY services/orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/orchestrator/src/ ./src/
CMD ["uvicorn", "src.orchestrator:app", "--host", "0.0.0.0", "--port", "8600"]

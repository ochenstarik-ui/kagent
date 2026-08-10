FROM python:3.12-slim
WORKDIR /app
COPY services/pipeline/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/py_events/ ./packages/py_events/
COPY services/nats/src/events.py ./services/nats/src/events.py
COPY services/pipeline/src/ ./src/
CMD ["uvicorn", "src.pipeline:app", "--host", "0.0.0.0", "--port", "8400"]

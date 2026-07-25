FROM python:3.12-slim
WORKDIR /app
COPY services/reasoning-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/reasoning-engine/src/ ./src/
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8200"]

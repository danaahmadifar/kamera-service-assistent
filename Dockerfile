FROM python:3.14.7-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY camera_service/ ./camera_service/
COPY reference_docs/ ./reference_docs/
COPY data/ ./data/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "camera_service.api:app", "--host", "0.0.0.0", "--port", "8000"]

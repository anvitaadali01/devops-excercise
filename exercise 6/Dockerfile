FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --no-create-home --uid 10001 metrics

COPY delivery_metrics.py .
USER 10001:10001

EXPOSE 8000
CMD ["python", "delivery_metrics.py"]

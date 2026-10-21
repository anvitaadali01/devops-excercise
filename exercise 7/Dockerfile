FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --no-create-home --uid 10001 appuser

COPY app.py .
USER 10001:10001

ENTRYPOINT ["python", "app.py"]
CMD ["--name", "World"]

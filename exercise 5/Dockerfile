FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "Flask>=3.0,<4.0"

WORKDIR /app
COPY app.py /app/app.py
RUN useradd --no-create-home --uid 10001 appuser
USER 10001:10001

EXPOSE 5000
CMD ["/usr/local/bin/python3.11", "/app/app.py"]

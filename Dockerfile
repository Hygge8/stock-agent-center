FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install -U pip setuptools wheel && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/database /app/reports /app/logs

EXPOSE 9000

CMD ["python", "-m", "api.main"]

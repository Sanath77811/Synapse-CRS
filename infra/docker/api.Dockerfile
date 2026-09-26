FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages/contracts/src:/app/packages/policy/src:/app/packages/audit/src:/app/packages/cases/src:/app/apps/api/src

WORKDIR /app

RUN useradd --create-home --uid 10001 synapse

COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r /app/requirements.lock

COPY packages /app/packages
COPY apps /app/apps
COPY schemas /app/schemas
COPY infra/docker/entrypoint.sh /entrypoint.sh

RUN chmod 0555 /entrypoint.sh \
    && chown -R synapse:synapse /app

USER synapse
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]

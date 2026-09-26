PYTHONPATH := packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:apps/api/src
export PYTHONPATH

.PHONY: install test lint format api migrate

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.lock

test:
	.venv/bin/pytest

lint:
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format:
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

api:
	.venv/bin/uvicorn synapse_api.main:app --host 127.0.0.1 --port 8000

migrate:
	.venv/bin/alembic -c apps/api/alembic.ini upgrade head

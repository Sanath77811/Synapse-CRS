PYTHONPATH := packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:packages/telemetry/src:packages/agent/src:packages/correlation/src:packages/reasoning/src:packages/validation/src:apps/api/src
export PYTHONPATH

.PHONY: install test lint format api migrate demo demo-persist demo-agent demo-correlation demo-reasoning research-eval research-eval-phase11

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

demo:
	.venv/bin/python -m synapse_telemetry.demo

demo-persist:
	.venv/bin/python -m synapse_api.telemetry_persist_demo

demo-agent:
	.venv/bin/python -m synapse_agent.demo

demo-correlation:
	.venv/bin/python -m synapse_correlation.demo

demo-reasoning:
	.venv/bin/python -m synapse_reasoning.demo

research-eval:
	.venv/bin/python -m synapse_validation

research-eval-phase11:
	.venv/bin/python -m synapse_validation.phase11

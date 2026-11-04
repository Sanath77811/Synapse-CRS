# Correlation demonstration

`make demo-correlation` starts the existing API in-process, enrolls a lab agent, **constructs synthetic telemetry** (not `/proc` samples), ingests it through `POST /api/v1/telemetry/ingest`, then runs correlation.

Those envelopes are labeled `dataset=synthetic_lab` in the demo log. They exercise the same signing and ingest path as the Linux collector, but the process and network facts are authored by the demo, not observed from this kernel.

Live collector evidence is a separate dataset. Correlate it with the same `POST .../correlation/runs` after `make demo-agent` if you want stored `/proc` rows included. Do not treat synthetic ids and live ids as one observation stream without checking `agent_id`.

## Command

PostgreSQL must already be available. The demo binds `127.0.0.1:18081`.

```bash
make demo-correlation
```

or

```bash
.venv/bin/python -m synapse_correlation.demo
```

## What it shows

1. A normal synthetic lifecycle (start, one connection, exit) that should not dominate the score.
2. A synthetic process with six connections to distinct ports (repeated network and multi-port correlations).
3. A synthetic `process_exited` with no matching start (inference, missing evidence).
4. A risk score with the published formula.
5. Finding explanation, epistemic status, and supporting event ids.

Exit code 0 means the run stored findings with a score above 0 and returned them over HTTP.

## Limits

This is not a complete reasoning engine. There is no model, no neuro-symbolic layer, and no automated response.

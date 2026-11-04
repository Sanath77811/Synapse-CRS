# Linux telemetry agent

The collector lives in `packages/agent/src/synapse_agent`.

```bash
.venv/bin/python -m synapse_agent
```

End-to-end laboratory demonstration:

```bash
make demo-agent
```

The agent polls procfs, normalizes and signs observations, and POSTs them to the existing ingest API. Enrollment remains an administrator action. Private keys stay on the monitored host.

See `docs/architecture/linux-agent.md` and `docs/guides/linux-agent-setup.md`.

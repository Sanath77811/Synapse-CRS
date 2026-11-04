# Linux agent setup

The collector runs on Linux with a readable procfs. This repository's development VM is sufficient. Root is not required for the default poll.

## Install

From the repository root, with the existing virtualenv:

```bash
.venv/bin/pip install -r requirements.lock
export PYTHONPATH=packages/contracts/src:packages/policy/src:packages/audit/src:packages/cases/src:packages/telemetry/src:packages/agent/src:apps/api/src
```

PostgreSQL and the API must already be migrated. The agent process must not receive `MIGRATION_DATABASE_URL`.

## Enroll

1. Create an authorized lab target with `telemetry.ingest` as an administrator.
2. On the monitored host, start the agent once so it writes `ed25519.pem`, or generate the key with the same `synapse_agent.keys` helper.
3. Read the public key as 64 lowercase hex characters from `SigningKey.public_key().raw_bytes().hex()` in a trusted local program. Do not upload the PEM file.
4. `POST /api/v1/targets/{target_id}/agents` with that hex and an optional `agent_id`.
5. Set `SYNAPSE_AGENT_ID` and `SYNAPSE_TARGET_ID` to the enrolled identifiers.

There is no public self-enrollment path.

## Environment

| Variable | Meaning |
|---|---|
| `SYNAPSE_AGENT_ID` | Enrolled agent UUID v4 |
| `SYNAPSE_TARGET_ID` | Bound target UUID v4 |
| `SYNAPSE_AGENT_HOME` | Directory for the key and state files |
| `SYNAPSE_INGEST_URL` | Default `http://127.0.0.1:8000/api/v1/telemetry/ingest` |
| `SYNAPSE_AGENT_POLL_SECONDS` | Poll period, default `1.0` |
| `SYNAPSE_AGENT_PROC_ROOT` | Default `/proc` |
| `SYNAPSE_AGENT_MAX_PENDING` | Pending queue bound |
| `SYNAPSE_AGENT_MAX_STATE_BYTES` | State file bound |
| `SYNAPSE_AGENT_HTTP_TIMEOUT` | Ingest timeout in seconds |

Production ingest should be `https://` at a reverse proxy. The agent process itself does not terminate TLS.

## Start

```bash
.venv/bin/python -m synapse_agent
```

SIGINT and SIGTERM finish the current drain and exit.

## Permissions

Readable `/proc/<pid>/stat` and `/proc/<pid>/status` for tasks you need to observe. Readable `/proc/net/{tcp,tcp6,udp,udp6}`. Optional readable `/proc/<pid>/fd` for inode-to-pid mapping. No extra Linux capabilities are required for that set.

If procfs is mounted hidepid=2, the agent only sees its own tasks unless it runs as a privileged user. Prefer the least privilege that still sees the authorized workload.

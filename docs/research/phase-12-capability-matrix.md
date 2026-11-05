# Phase 12 capability matrix

Cells are **documentation vs this checkout**. They are not evaluation scores.

| Capability | DMBD | WinMET | OpTC |
|---|---|---|---|
| Process creation | Documented in overview; files absent | Documented process list; files absent | Documented PROCESS actions; files absent |
| Process termination | `process_term` documented; files absent | Sandbox window; unverified locally | eCar TERMINATE documented; files absent |
| Parent-child tree | `parent_pid_hash` documented; files absent | `processtree` documented; files absent | pid/ppid + actorID; files absent |
| Stable process identity | `pid_hash` documented; files absent | in-trace `process_id`; files absent | actorID UUID documented; files absent |
| PID reuse validation | Possible if hashes differ; files absent | Unverified locally | pid not unique; files absent |
| Process-network association | `process_net_conn` documented; files absent | Trace network fields documented; files absent | FLOW+pid documented; files absent |
| Event-level labels | **No** (sample AV consensus) | **No** (trace family labels) | Contested external labeling; files absent |
| Sample-level labels | Documented benign/malicious; files absent | Malware-family traces; files absent | Not sample-oriented |
| Independent ground truth | Sample labels only; files absent | Family labels; files absent | Ground-truth file + disagreeing re-labels |
| Enterprise endpoint realism | 5-minute cyber-range executions | CAPE sandbox traces | Windows 10 testbed; 1 TB; files absent |
| Linux boot_id / start_ticks | Not present | Not present | Not present |
| Ed25519 enrolled telemetry | Not present | Not present | Not present |

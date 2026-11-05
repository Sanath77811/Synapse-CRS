# Evidence reconstruction

`reconstruct()` builds process lifetimes from `(agent_id, boot_id, pid, start_ticks)`. Network rows bind only with a unique covering lifetime.

Timeline items are `observed` (telemetry event_id present), `correlated` (Phase 8 finding), or `inferred` (for example a missing start). Inferred items never reuse a stored event_id.

Quality scores (coverage, identity, lifecycle completeness, correlation clarity, timestamp consistency) are **not** attack confidence.

Graph nodes/edges are capped (2000/5000). Relationships require stable identifiers.

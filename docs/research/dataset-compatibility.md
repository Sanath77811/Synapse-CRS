# Dataset compatibility

Status: CIC-IDS2017 **NOT EVALUATED** on this clone (dataset not present). Parser adapter: **IMPLEMENTED**. Direct feature mapping onto `synthetic_lab_features_v1`: **NOT IMPLEMENTED** (not comparable).

## Availability

This repository does not ship CIC-IDS2017. A workspace search found no CIC/IDS2017 files. Do not `git add` the raw corpus.

## Acquisition (operator-controlled)

1. Review the Canadian Institute for Cybersecurity CIC-IDS2017 page and licence.
2. Download only if you are authorized to use the dataset.
3. Place a CSV locally. Do not commit it.
4. Export `SYNAPSE_CICIDS_CSV=/absolute/path/to/file.csv`.
5. Run `make research-eval`.

The adapter refuses files larger than 8 MiB and more than 5000 rows unless those bounds are passed explicitly in tests. Excluded rows are listed with reasons. Labels are preserved and mapped only to evaluation categories `benchmark_benign_flow` and `benchmark_attack_labelled_flow`.

## Columns the adapter requires

`Destination Port`, `Flow Duration`, `Total Fwd Packets`, `Total Backward Packets`, `Label`.

Public CIC-IDS2017 files contain many additional numeric flow features. Extra columns are ignored. Missing required columns abort the load.

## Feature compatibility vs schema 1.0.0

| Synapse feature | Status | Why |
| --- | --- | --- |
| process_count | not available | Flows are not processes |
| complete_lifecycle_ratio | not available | No start/exit events |
| network_count | not comparable | Packet counts ≠ covering-network counts |
| max_network_per_process | not available | No pid+start_ticks key |
| distinct_remote_ports_max | not comparable | One destination port per flow |
| event_density | not comparable | Flow duration ≠ observation density |
| missing_start_count | not available | No process start |
| pid_reuse_finding_count | not available | Phase 8 findings are derived |
| repeated_network_finding | not available | Phase 8 findings are derived |
| rapid_burst_finding | not available | Phase 8 findings are derived |

Never fabricate agent IDs, process identities, boot IDs, event IDs, or signatures from CIC rows.

## Leakage risks

Random row splits of CIC-IDS2017 can leak related flows from the same capture. The adapter records source checksums and requires operators to use group- or time-aware splits if they add a flow-level experiment later. This phase does not score CIC rows with the Isolation Forest trained on process features.

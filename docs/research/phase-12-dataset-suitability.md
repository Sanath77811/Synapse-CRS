# Phase 12 dataset discovery and suitability

Local files: **none** for DMBD, WinMET, or OpTC. Sizes, hashes, and row counts of those corpora are **unavailable** here.

## Ranking (suitability for this milestone, not popularity)

1. **DMBD** — documented stable process hash, parent links, lifecycle fields, sample labels, official split. Windows sandbox/cyber-range, not Linux agents. Files absent.
2. **WinMET** — documented process trees in JSON; malware-only family labels; ~13 GiB compressed / ~750 GiB unpacked per Zenodo notes. Files absent.
3. **OpTC** — closest to enterprise Windows telemetry; ~1 TB; contested extra labels; files absent.

## Provenance

| Dataset | Source | Terms in this checkout |
| --- | --- | --- |
| DMBD | https://gdo-wintap.llnl.gov/data/newdocs/DMBD/ | Unverified; review LLNL terms |
| WinMET | https://zenodo.org/records/16414116 | Zenodo record; operator must accept |
| OpTC | https://fkie-cad.github.io/COMIDDS/content/datasets/optc/ | Unverified; large GDrive distribution |

Schema notes for Wintap/DMBD (`pid_hash`, `parent_pid_hash`, `process_term`) come from the published data dictionary, not from files in Git.

## Acquisition (optional)

Do not commit raw data. Point `SYNAPSE_DMBD_JSONL` at a JSONL of process rows using the adapter fields (`source_record_id`, `sample_id`, `event_type`, plus documented Wintap columns when available). The runner does not download the corpus.

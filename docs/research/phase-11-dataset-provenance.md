# CIC-IDS2017 provenance and limitations

Official source: https://www.unb.ca/cic/datasets/ids-2017.html

Citation: Sharafaldin, Lashkari, Ghorbani, ICISSP 2018.

License/usage: operators must accept CIC terms. This repository does **not** redistribute the files.

Typical machine-learning CSVs are labelled flow exports from a week of captures (Monday benign through Friday DDoS/PortScan). Labels include BENIGN and attack families such as PortScan, DoS Hulk, and DDoS.

## Availability in this checkout

Verified: the corpus is **not** in Git and was **not** downloaded by Phase 11. The only CSVs in-tree are parser/protocol **fixtures**.

Unavailable until an operator copy is hashed: exact file names, SHA-256, sizes, row counts, and timestamp coverage of that copy.

## Feature compatibility

See Phase 10 [dataset-compatibility.md](dataset-compatibility.md). Zero `synthetic_lab_features_v1` fields are directly compatible. Phase 11 therefore evaluates a **flow-only** protocol instead of mapping rows onto process reconstructions.

## Acquisition (optional, operator-controlled)

1. Review CIC terms.
2. Download only if authorized.
3. Point `SYNAPSE_CICIDS_CSV` at one CSV.
4. Run `make research-eval-phase11`.
5. Do not commit the corpus.

The loader bounds file size (32 MiB) and rows (20 000). Truncation is recorded; a truncated run is a sample, not the full dataset.

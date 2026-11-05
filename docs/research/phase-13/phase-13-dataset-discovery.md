# Phase 13 dataset discovery

Facts below are tagged **verified**, **documented**, **inference**, or **unknown**.

## Ranking

1. **DMBD** — best documented `pid_hash` / parent / lifecycle / sample labels. Trees not acquired.
2. **WinMET** — documented process trees; compressed size too large for auto-download.
3. **OpTC** — enterprise eCar; terabyte-scale; contested labels.
4. Smaller alternatives (EMBER, CIC-MalMem, Avast-CTU CAPE) either lack process graphs or were not verified/downloaded.

## Candidate A — DMBD

- Official docs: https://gdo-wintap.llnl.gov/data/newdocs/DMBD/
- Index: https://gdo168.llnl.gov/data/dmbd/ (**verified** HTTP 200)
- Labels: `truth_labels_train.json` Content-Length **1979873**; `truth_labels_test.json` **1233522** (**verified** HEAD)
- `trees_0.json` Content-Length **969100712** (**verified** Range GET). Not downloaded.
- Format: pandas-orient JSON columns `experiment`, `year`, `label` (**verified** on label files). Tree shards were only prefix-inspected; `pid_hash` was **not** observed in the first 256 KiB (**unknown** layout beyond `experiment` in that window).
- License: operator must review LLNL terms (**unknown** acceptance; not accepted on the user's behalf).
- Labels: sample-level AV consensus. **Do not** copy onto events.
- Overview claimed 40,000 / 25,416 splits (**documented**). Verified unique counts must come from the files.

## Candidate B — WinMET

- https://zenodo.org/records/16414116
- Documented ~13 GB compressed / ~750 GB unpacked.
- Live Zenodo file list was not reliably retrieved this session (**unknown** exact current files).
- Not downloaded (size bound).

## Candidate C — OpTC

- https://fkie-cad.github.io/COMIDDS/content/datasets/optc/
- Documented ~1 TB. Not downloaded.

## Candidate D — smaller alternatives

- EMBER 2018: PE static features — **unsuitable** for process reconstruction.
- CIC-MalMem-2022: memory features — **unsuitable**.
- Avast-CTU CAPEv2: possible sandbox reports; size/license **unverified**; not downloaded.

## Acquisition decision

Acquire only official DMBD **label** JSON (under 8 MiB) when present. Refuse `trees_*.json`, WinMET 7z volumes, and OpTC dumps.

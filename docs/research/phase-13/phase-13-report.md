# Phase 13 research results

Status: **EXPERIMENTAL**. Phase 10–12 generated findings are preserved.

## Scientific completion

**scientific_completion=False**
**independent_endpoint_validation_completed=False**
**dmbd_process_trees_evaluated=False**
**dmbd_labels_inspected=True**
**winmet_evaluated=False**
**optc_evaluated=False**

Blocker: No independent endpoint process dataset is present. Set SYNAPSE_DMBD_JSONL to local DMBD-like process JSONL. trees_*.json were not auto-downloaded (≈1 GB/shard). Label JSON inspection, if present, is not tree evaluation.

No independent process-tree metrics were produced.

## DMBD label files (not process trees)

```json
{
  "available": true,
  "directory": "synapse-dmbd",
  "train": {
    "path": "truth_labels_train.json",
    "sha256": "76b4f54d187f1eada9266ae578022189dad1ac27d5acdebc34d680609a9a36c2",
    "file_size_bytes": 1979873,
    "format": "pandas_orient_columns_experiment_year_label",
    "sample_count": 40000,
    "unique_sample_ids": 40000,
    "label_counts": {
      "benign": 20000,
      "malicious": 20000
    },
    "year_counts": {
      "2023": 7343,
      "2021": 4005,
      "2017": 15033,
      "2024": 7004,
      "2022": 3254,
      "2020": 2634,
      "2019": 262,
      "2018": 178,
      "2009": 3,
      "2016": 117,
      "2014": 43,
      "2013": 14,
      "2015": 94,
      "2012": 4,
      "2010": 5,
      "2007": 1,
      "2011": 4,
      "2008": 2
    },
    "label_scope": "sample",
    "label_source": "DMBD AV-consensus files as published on gdo168.llnl.gov",
    "id_prefix_sample": [
      "E53002",
      "E30273",
      "E27878"
    ],
    "notes": "These files label experiments/samples, not individual process events. They are not a substitute for trees_*.json process records."
  },
  "test": {
    "path": "truth_labels_test.json",
    "sha256": "c1152137b62100b3d7abada3b1a77dc3d800b809708eca2a3ad0712f9136f8ff",
    "file_size_bytes": 1233522,
    "format": "pandas_orient_columns_experiment_year_label",
    "sample_count": 24747,
    "unique_sample_ids": 24747,
    "label_counts": {
      "benign": 5249,
      "malicious": 19498
    },
    "year_counts": {
      "2024": 7615,
      "2017": 17131,
      "null": 1
    },
    "label_scope": "sample",
    "label_source": "DMBD AV-consensus files as published on gdo168.llnl.gov",
    "id_prefix_sample": [
      "E33423",
      "E39699",
      "E16707"
    ],
    "notes": "These files label experiments/samples, not individual process events. They are not a substitute for trees_*.json process records."
  },
  "split_comparison": {
    "train_samples": 40000,
    "test_samples": 24747,
    "documented_train": 40000,
    "documented_test": 25416,
    "train_matches_documented_count": true,
    "test_matches_documented_count": false,
    "train_test_id_overlap": 0,
    "notes": "Overview claimed 25,416 test samples. Verified unique IDs come from the inspected files. Train/test overlap must be zero for a valid split."
  },
  "not_process_trees": true,
  "independent_process_evaluation": false,
  "notes": "Official DMBD sample labels were inspected. trees_*.json were not loaded. This is not independent endpoint reconstruction or detection."
}
```

## Preserved prior findings

{
  "available": true,
  "name": "phase10",
  "experiment_id": "phase10-research-validation-v1",
  "must_not_rewrite": true
}

{
  "available": true,
  "name": "phase11",
  "experiment_id": "phase11-flow-benchmark-v1",
  "must_not_rewrite": true
}

{
  "available": true,
  "name": "phase12",
  "experiment_id": "phase12-endpoint-evidence-v1",
  "must_not_rewrite": true
}

## Limitations

- Label JSON is not process reconstruction.
- Sample AV labels are not event-level malice.
- pid_hash is not Linux boot_id/start_ticks.
- Z3 SAT is not real-world safety.
- Completeness-aware abstention is not a calibrated probability.


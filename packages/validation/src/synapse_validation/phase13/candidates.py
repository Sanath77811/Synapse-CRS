"""Phase 13 dataset discovery. Verified HEAD sizes vs documented claims."""

from __future__ import annotations

from synapse_validation.phase12.candidates import CANDIDATES as PHASE12_CANDIDATES

# Verified during Phase 13 via HTTP HEAD/Range against official hosts.
VERIFIED_DMBD = {
    "label_train_url": "https://gdo168.llnl.gov/data/dmbd/truth_labels_train.json",
    "label_test_url": "https://gdo168.llnl.gov/data/dmbd/truth_labels_test.json",
    "label_train_content_length": 1_979_873,
    "label_test_content_length": 1_233_522,
    "trees_0_url": "https://gdo168.llnl.gov/data/dmbd/trees_0.json",
    "trees_0_content_length": 969_100_712,
    "trees_not_downloaded": True,
    "index": "https://gdo168.llnl.gov/data/dmbd/",
    "docs": "https://gdo-wintap.llnl.gov/data/newdocs/DMBD/",
}

ALTERNATIVES: tuple[dict[str, object], ...] = (
    {
        "id": "ember2018",
        "name": "EMBER 2018",
        "official_source": "https://github.com/elastic/ember",
        "verified_download": False,
        "reason_skipped": (
            "Static PE feature vectors, not process-creation/termination trees. "
            "Unsuitable for reconstruction RQs."
        ),
        "rank": 99,
    },
    {
        "id": "cic-malmem-2022",
        "name": "CIC-MalMem-2022",
        "official_source": "https://www.unb.ca/cic/datasets/malmem-2022.html",
        "verified_download": False,
        "reason_skipped": "Memory-dump classification features, not host process graphs.",
        "rank": 98,
    },
    {
        "id": "avast-ctu-cape",
        "name": "Avast-CTU Public CAPEv2 Dataset",
        "official_source": "https://github.com/avast/avast-ctu-cape-dataset",
        "verified_download": False,
        "reason_skipped": (
            "Sandbox reports; size and license not verified in this session; not auto-downloaded."
        ),
        "rank": 20,
    },
)


def ranking() -> list[dict[str, object]]:
    return [
        {
            "rank": 1,
            "id": "dmbd",
            "suitability": (
                "Best documented process identity (pid_hash) plus sample labels. "
                "Process trees were not acquired (≈1 GB/shard)."
            ),
            "evidence_class": "labels_inspected_trees_absent",
        },
        {
            "rank": 2,
            "id": "winmet",
            "suitability": "Documented process trees; ~13 GB compressed / ~750 GB unpacked.",
            "evidence_class": "not_acquired_size",
        },
        {
            "rank": 3,
            "id": "optc",
            "suitability": "Enterprise eCar; ~1 TB; contested labels; not acquired.",
            "evidence_class": "not_acquired_size",
        },
        {
            "rank": 4,
            "id": "avast-ctu-cape",
            "suitability": "Possible sandbox trees; unverified locally.",
            "evidence_class": "not_acquired",
        },
    ]


def discovery_payload() -> dict[str, object]:
    return {
        "phase12_candidate_ids": [item["id"] for item in PHASE12_CANDIDATES],
        "verified_dmbd_http": VERIFIED_DMBD,
        "alternatives_considered": list(ALTERNATIVES),
        "ranking": ranking(),
        "epistemic": {
            "verified_facts": [
                "truth_labels_train.json Content-Length 1979873",
                "truth_labels_test.json Content-Length 1233522",
                "trees_0.json Content-Length 969100712 via Range",
            ],
            "documented_claims": [
                "DMBD overview 40,000 train / 25,416 test",
                "WinMET ~13 GB / ~750 GB",
                "OpTC about 1 TB",
            ],
            "inferences": [
                "trees_*.json pandas shards are too large for the 8 MiB acquisition bound"
            ],
            "unknown": [
                "WinMET exact file list this session (Zenodo API timed out previously)",
                "OpTC GDrive live file sizes",
                "LLNL license acceptance status for a given operator",
            ],
        },
    }

"""Dataset discovery. Documented claims vs unverified local files."""

from __future__ import annotations

CANDIDATES: tuple[dict[str, object], ...] = (
    {
        "id": "dmbd",
        "name": "Dynamic Malware Behavior Dataset (DMBD)",
        "official_source": "https://gdo-wintap.llnl.gov/data/newdocs/DMBD/",
        "related_schema": "https://gdo168.llnl.gov/data/newdocs/datadict/",
        "related_code": "https://github.com/llnl/Wintap-Data",
        "provenance": (
            "LLNL Wintap host logs from ~5-minute cyber-range executions. "
            "Overview page reports 65,416 samples and ~39 million events."
        ),
        "license_or_terms": "Unverified in this checkout; operators must review LLNL terms.",
        "formats_documented": "Wintap/DMBD event and label tables (not present here)",
        "download_size_verified": None,
        "unpacked_size_verified": None,
        "event_types_documented": (
            "process creation/termination",
            "image loading",
            "file creation",
            "network connections",
            "registry modifications",
        ),
        "process_identity_documented": (
            "pid_hash (hostname + os pid + start_time); os_pid is not unique"
        ),
        "parent_child_documented": "parent_pid_hash, parent_os_pid, process_path",
        "lifecycle_documented": "process_started, process_term, process_stop_seconds",
        "network_association_documented": "process_net_conn keyed by pid_hash",
        "label_granularity": "sample (benign/malicious via AV consensus, ~80 engines)",
        "ground_truth_quality": (
            "Sample labels are AV consensus, not analyst event labels. "
            "They must not be copied onto every process event."
        ),
        "temporal_coverage_documented": (
            "Train 2017–2023; test includes 2024 malware (overview claim)"
        ),
        "official_split_documented": "40,000 train / 25,416 test (overview claim)",
        "os": "Windows (Wintap); not Linux procfs telemetry",
        "local_files_present": False,
        "suitability": {
            "RQ1_reconstruction": "promising if process tables are supplied; unverified locally",
            "RQ2_detection": "sample-level only unless extra labels appear",
            "RQ3_hybrid": "Phase 9 hybrid not comparable (Linux identity model)",
            "RQ4_explanations": "possible with source row ids",
            "RQ5_robustness": "possible on adapters; not a substitute for missing corpus",
            "RQ6_cannot_validate": (
                "Ed25519 enrollment, Linux boot_id/start_ticks, live agent identity, "
                "event-level malice"
            ),
        },
        "rank_reason": (
            "Preferred adapter target: documented stable pid_hash, parent links, "
            "lifecycle timestamps, and an official train/test split. Rank is not "
            "an evaluation result."
        ),
    },
    {
        "id": "winmet",
        "name": "WinMET Windows malware execution traces",
        "official_source": "https://zenodo.org/records/16414116",
        "paper": "https://doi.org/10.1016/j.dib.2025.112273",
        "provenance": "CAPE sandbox traces processed by MALVADA; ~31,844 JSON traces.",
        "license_or_terms": "Zenodo record; 7z password documented as infected. Review before use.",
        "formats_documented": "JSON traces in five 7z volumes",
        "download_size_verified": "~13 GB compressed (Zenodo documentation)",
        "unpacked_size_verified": "~750 GB uncompressed (Zenodo documentation)",
        "event_types_documented": ("API calls", "process trees", "files", "registry", "network"),
        "process_identity_documented": "in-trace process_id / parent_id; not a host-global GUID",
        "parent_child_documented": "behavior.processtree",
        "lifecycle_documented": (
            "sandbox execution window; termination not independently verified here"
        ),
        "network_association_documented": "trace-level network communications (documented)",
        "label_granularity": (
            "trace/sample malware-family labels (CAPE and AVClass); malware-only corpus"
        ),
        "ground_truth_quality": (
            "Family labels on sandbox traces. No benign class in the described corpus."
        ),
        "temporal_coverage_documented": "unverified locally",
        "official_split_documented": (
            "not documented as an official train/test partition in this audit"
        ),
        "os": "Windows sandbox, not continuous enterprise telemetry",
        "local_files_present": False,
        "suitability": {
            "RQ1_reconstruction": "process trees documented; files absent locally",
            "RQ2_detection": "family classification possible; binary malice lacks benign traces",
            "RQ3_hybrid": "Phase 9 hybrid not comparable",
            "RQ4_explanations": "possible if JSON is loaded",
            "RQ5_robustness": "sandbox artefacts differ from live endpoints",
            "RQ6_cannot_validate": "benign class, Linux identity, live enrollment",
        },
        "rank_reason": "Strong process-tree JSON, but malware-only and ~750 GiB unpacked.",
    },
    {
        "id": "optc",
        "name": "DARPA OpTC",
        "official_source": "https://fkie-cad.github.io/COMIDDS/content/datasets/optc/",
        "provenance": "DARPA Transparent Computing scale-out; Windows 10 eCar + Zeek.",
        "license_or_terms": "Unverified here; distribution via documented GDrive.",
        "formats_documented": "eCar JSON, Zeek/Bro logs",
        "download_size_verified": None,
        "unpacked_size_verified": "about 1 TB (COMIDDS documentation)",
        "event_types_documented": ("PROCESS/FILE/FLOW eCar actions", "Zeek network"),
        "process_identity_documented": "actorID/objectID UUIDs plus pid/ppid; pid is not unique",
        "parent_child_documented": "ppid present; UUID actorID is the stronger handle",
        "lifecycle_documented": "PROCESS START/TERMINATE actions in eCar (documented examples)",
        "network_association_documented": (
            "FLOW object with pid; joining quality unverified locally"
        ),
        "label_granularity": (
            "Folder-implied activity plus separate later labeling projects that do not fully agree"
        ),
        "ground_truth_quality": (
            "Known disagreement between host-labeling efforts; not inspected locally."
        ),
        "temporal_coverage_documented": "6 days, 2019",
        "official_split_documented": "benign then evaluation periods; not a sample-level ML split",
        "os": "Windows 10 enterprise testbed (500 hosts in the released data)",
        "local_files_present": False,
        "suitability": {
            "RQ1_reconstruction": "possible in principle; 1 TB and no local files",
            "RQ2_detection": "host/session labeling is contested",
            "RQ3_hybrid": "Phase 9 hybrid not comparable",
            "RQ4_explanations": "possible with eCar id fields",
            "RQ5_robustness": "enterprise volume; not runnable here",
            "RQ6_cannot_validate": (
                "Linux agent identity; agreed event-level labels without extra corpora"
            ),
        },
        "rank_reason": (
            "Closest to enterprise Windows telemetry, impractical without an operator copy."
        ),
    },
)

PRIMARY_ADAPTER = "dmbd"


def candidate_by_id(dataset_id: str) -> dict[str, object]:
    for item in CANDIDATES:
        if item["id"] == dataset_id:
            return item
    raise KeyError(dataset_id)


def suitability_matrix() -> list[dict[str, str]]:
    rows = []
    capabilities = (
        ("Process creation", "event_types_documented"),
        ("Process termination", "lifecycle_documented"),
        ("Parent-child tree", "parent_child_documented"),
        ("Stable process identity", "process_identity_documented"),
        ("PID reuse validation", "process_identity_documented"),
        ("Process-network association", "network_association_documented"),
        ("Event-level labels", "label_granularity"),
        ("Sample-level labels", "label_granularity"),
        ("Independent ground truth", "ground_truth_quality"),
        ("Enterprise endpoint realism", "os"),
    )
    for title, _key in capabilities:
        row = {"capability": title}
        for item in CANDIDATES:
            present = bool(item["local_files_present"])
            documented = str(item.get(_key, ""))
            if not present:
                cell = "documented-unverified" if documented else "unavailable"
            else:
                cell = "evaluate"
            if title == "Event-level labels":
                if item["id"] == "dmbd":
                    cell = "not a sample-level AV consensus; event labels unavailable"
                elif item["id"] == "winmet":
                    cell = "family labels are trace-level, not per API call"
                elif item["id"] == "optc":
                    cell = "contested / external labeling; files absent"
            if title == "Sample-level labels" and item["id"] == "dmbd":
                cell = "documented (benign/malicious); files absent"
            if title == "PID reuse validation":
                cell = (
                    "supported if pid_hash differs for reused os_pid; files absent"
                    if item["id"] == "dmbd"
                    else "unverified locally"
                )
            if title == "Enterprise endpoint realism":
                cell = str(item["os"]) + "; files absent"
            row[str(item["id"])] = cell
        rows.append(row)
    return rows

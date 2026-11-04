"""CIC-IDS2017 provenance. Verified facts vs unavailable information."""

OFFICIAL_SOURCE = "https://www.unb.ca/cic/datasets/ids-2017.html"
CITATION = (
    "Iman Sharafaldin, Arash Habibi Lashkari, and Ali A. Ghorbani, "
    '"Toward Generating a New Intrusion Detection Dataset and Intrusion '
    'Traffic Characterization", 4th International Conference on Information '
    "Systems Security and Privacy (ICISSP), Portugal, January 2018."
)
LICENSE_NOTES = (
    "Operators must review the Canadian Institute for Cybersecurity terms "
    "before download. This repository does not redistribute the corpus."
)
EXPECTED_CAPTURE_DAYS = (
    "Monday-WorkingHours (BENIGN)",
    "Tuesday-WorkingHours",
    "Wednesday-workingHours",
    "Thursday-WorkingHours-Morning-WebAttacks",
    "Thursday-WorkingHours-Afternoon-Infilteration",
    "Friday-WorkingHours-Morning",
    "Friday-WorkingHours-Afternoon-PortScan",
    "Friday-WorkingHours-Afternoon-DDos",
)
KNOWN_LIMITATIONS = (
    "Flow records are not Linux process telemetry.",
    "Public reports document label noise, duplicate flows, and extreme/Inf values.",
    "Timestamp and IP fields can leak capture-session structure.",
    "Class distribution is heavily imbalanced toward BENIGN.",
    "A single CSV sample is not the full week-long corpus.",
)
UNAVAILABLE_UNTIL_FILES_INSPECTED = (
    "file hashes",
    "exact row counts",
    "per-file class histograms",
    "timestamp coverage of the operator copy",
)

NUMERIC_CANDIDATES = (
    "Destination Port",
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Flow Bytes/s",
    "Flow Packets/s",
)

IDENTIFIER_OR_LEAK_FIELDS = (
    "Flow ID",
    "Source IP",
    "Destination IP",
    "Source Port",
    "Timestamp",
)

EXCLUSIONS = {
    "Flow ID": "Record identifier; can leak duplicates across splits.",
    "Source IP": "Capture-host artifact; not a portable flow statistic.",
    "Destination IP": "Capture-host artifact; not a portable flow statistic.",
    "Source Port": "Ephemeral client port; can group sessions unrealistically.",
    "Timestamp": "Used only for temporal splitting, never as a model feature.",
    "Label": "Target, not a predictor.",
}

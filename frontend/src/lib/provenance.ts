type DataSource = "demo" | "live" | "empty" | "unavailable";

export type ProvenanceFlag = {
  kind: "demo" | "laboratory" | "live" | "empty" | "unavailable" | "loading";
  label: string;
  note: string;
};

export function provenanceFlag(
  mode: "demo" | "live",
  source: DataSource,
  loading: boolean,
  datasetLabel: string | null,
): ProvenanceFlag {
  if (loading) {
    return { kind: "loading", label: "LOADING", note: "Snapshot request in progress." };
  }
  if (mode === "demo") {
    return {
      kind: "demo",
      label: "DEMO MODE",
      note: "Synthetic fixtures in the browser. Not enrolled endpoint telemetry.",
    };
  }
  if (source === "unavailable") {
    return {
      kind: "unavailable",
      label: "UNAVAILABLE",
      note: "Live request failed. Demo rows were not substituted.",
    };
  }
  if (source === "empty") {
    return {
      kind: "empty",
      label: "EMPTY",
      note: "Control plane answered; no targets or cases in this snapshot.",
    };
  }
  if (datasetLabel === "synthetic_lab") {
    return {
      kind: "laboratory",
      label: "LAB ENVELOPES",
      note: "Signed laboratory envelopes ingested through POST /telemetry/ingest. Not /proc samples.",
    };
  }
  return {
    kind: "live",
    label: "LIVE",
    note: "Rows from the FastAPI control plane for the locked target.",
  };
}

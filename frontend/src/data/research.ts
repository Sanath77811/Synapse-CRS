export type ResearchPhase = {
  id: string;
  title: string;
  engineering: "implemented" | "partial";
  scientific: "not_completed" | "synthetic_only";
  independent: boolean;
  summary: string;
  limitations: string[];
  command: string;
};

/** Source of truth: docs/research generated last-run files and methodology. */
export const RESEARCH_PHASES: ResearchPhase[] = [
  {
    id: "phase-10",
    title: "Phase 10 — synthetic reconstruction harness",
    engineering: "implemented",
    scientific: "synthetic_only",
    independent: false,
    summary:
      "Hybrid components compared on 12 constructed reconstructions. Hybrid tied simpler approaches. Isolation Forest missed unusual-volume on that corpus. Event-count prediction did not beat persistence.",
    limitations: [
      "Not CIC-IDS2017.",
      "Not enterprise detection rates.",
      "Counterfactual ablation is not causal inference.",
    ],
    command: "make research-eval",
  },
  {
    id: "phase-11",
    title: "Phase 11 — flow benchmark",
    engineering: "implemented",
    scientific: "not_completed",
    independent: false,
    summary:
      "Separate flow track with fail-closed runner. CIC-IDS2017 was not present. cicids2017_evaluated=false.",
    limitations: ["Phase 9 hybrid is not comparable on flow records."],
    command: "make research-eval-phase11",
  },
  {
    id: "phase-12",
    title: "Phase 12 — endpoint evidence adapter",
    engineering: "implemented",
    scientific: "not_completed",
    independent: false,
    summary:
      "endpoint-evidence-1.0.0 plus DMBD-oriented adapter. DMBD/WinMET/OpTC files absent. independent_endpoint_validation_completed=false.",
    limitations: [
      "Sample labels are not event-level truth.",
      "pid_hash is not Linux boot_id/start_ticks.",
    ],
    command: "make research-eval-phase12",
  },
  {
    id: "phase-13",
    title: "Phase 13 — independent evidence acquisition",
    engineering: "implemented",
    scientific: "not_completed",
    independent: false,
    summary:
      "Bounded acquisition and completeness-aware sample method. Official DMBD label JSON inspected (40,000 train / 24,747 test; overview claimed 25,416). Process trees were not downloaded. scientific_completion=false.",
    limitations: [
      "Label inspection is not tree reconstruction.",
      "trees_0.json ~969 MB was refused by the 8 MiB bound.",
    ],
    command: "make research-eval-phase13",
  },
];

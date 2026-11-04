import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest, listAll } from "../api/client";
import type {
  AgentView,
  AuditEventView,
  CaseView,
  ChainVerificationView,
  CorrelationLinkView,
  FindingView,
  HealthView,
  PlatformSnapshot,
  ReasoningAssessmentView,
  ReconstructionView,
  RiskSummaryView,
  TargetView,
} from "../api/types";
import { readMode, readToken, writeMode, writeToken, type SessionMode } from "../auth/session";
import { demoSnapshot } from "../data/demo";

type LoadState = "idle" | "loading" | "ready" | "error";

const empty: PlatformSnapshot = {
  targets: [],
  cases: [],
  agents: [],
  findings: [],
  links: [],
  risk: null,
  assessments: [],
  timeline: null,
  audit: [],
  chain: null,
};

export function usePlatform() {
  const [mode, setMode] = useState<SessionMode>(readMode);
  const [token, setToken] = useState<string | null>(readToken);
  const [health, setHealth] = useState<HealthView | null>(null);
  const [ready, setReady] = useState<HealthView | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);
  const [state, setState] = useState<LoadState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PlatformSnapshot>(empty);
  const [selectedTargetId, setSelectedTargetId] = useState<string | null>(null);

  const probe = useCallback(async (signal?: AbortSignal) => {
    try {
      const [h, r] = await Promise.all([
        apiRequest<HealthView>("/health", { signal }),
        apiRequest<HealthView>("/ready", { signal }).catch(() => null),
      ]);
      setHealth(h);
      setReady(r);
      setHealthError(null);
      return Boolean(h.status);
    } catch (err) {
      setHealth(null);
      setReady(null);
      setHealthError(err instanceof Error ? err.message : "API unreachable");
      return false;
    }
  }, []);

  const loadLive = useCallback(
    async (bearer: string, signal?: AbortSignal) => {
      setState("loading");
      setError(null);
      try {
        const [targets, cases, audit, chain] = await Promise.all([
          listAll<TargetView>("/api/v1/targets", bearer, signal),
          listAll<CaseView>("/api/v1/cases", bearer, signal),
          listAll<AuditEventView>("/api/v1/audit/events", bearer, signal),
          apiRequest<ChainVerificationView>("/api/v1/audit/verify", { token: bearer, signal }),
        ]);
        const targetId = selectedTargetId && targets.some((item) => item.id === selectedTargetId)
          ? selectedTargetId
          : (targets[0]?.id ?? null);
        let agents: AgentView[] = [];
        let findings: FindingView[] = [];
        let links: CorrelationLinkView[] = [];
        let risk: RiskSummaryView | null = null;
        let assessments: ReasoningAssessmentView[] = [];
        let timeline: ReconstructionView | null = null;
        if (targetId) {
          const packed = await Promise.all([
            listAll<AgentView>(`/api/v1/targets/${targetId}/agents`, bearer, signal),
            listAll<FindingView>(`/api/v1/targets/${targetId}/findings`, bearer, signal),
            listAll<CorrelationLinkView>(`/api/v1/targets/${targetId}/correlations`, bearer, signal),
            apiRequest<RiskSummaryView>(`/api/v1/targets/${targetId}/risk`, { token: bearer, signal }),
            listAll<ReasoningAssessmentView>(
              `/api/v1/targets/${targetId}/reasoning/assessments`,
              bearer,
              signal,
            ),
          ]);
          agents = packed[0];
          findings = packed[1];
          links = packed[2];
          risk = packed[3];
          assessments = packed[4];
          if (assessments[0]) {
            timeline = await apiRequest<ReconstructionView>(
              `/api/v1/reasoning/assessments/${assessments[0].id}/timeline`,
              { token: bearer, signal },
            );
          }
        }
        if (!selectedTargetId && targetId) {
          setSelectedTargetId(targetId);
        }
        setData({ targets, cases, agents, findings, links, risk, assessments, timeline, audit, chain });
        setState("ready");
      } catch (err) {
        setState("error");
        setError(err instanceof Error ? err.message : "Request failed");
        setData(empty);
      }
    },
    [selectedTargetId],
  );

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      await probe(controller.signal);
      if (mode === "demo") {
        setData(demoSnapshot());
        setSelectedTargetId(demoSnapshot().targets[0]?.id ?? null);
        setState("ready");
        return;
      }
      if (token) {
        await loadLive(token, controller.signal);
      } else {
        setData(empty);
        setState("ready");
      }
    })();
    return () => controller.abort();
  }, [loadLive, mode, probe, token]);

  const enterDemo = useCallback(() => {
    writeMode("demo");
    setMode("demo");
  }, []);

  const enterLive = useCallback((nextToken: string) => {
    writeToken(nextToken);
    writeMode("live");
    setToken(nextToken);
    setMode("live");
  }, []);

  const signOut = useCallback(() => {
    writeToken(null);
    writeMode("demo");
    setToken(null);
    setMode("demo");
  }, []);

  const selectedTarget = useMemo(
    () => data.targets.find((item) => item.id === selectedTargetId) ?? data.targets[0] ?? null,
    [data.targets, selectedTargetId],
  );

  return {
    mode,
    token,
    health,
    ready,
    healthError,
    state,
    error,
    data,
    selectedTarget,
    selectedTargetId: selectedTarget?.id ?? null,
    setSelectedTargetId,
    enterDemo,
    enterLive,
    signOut,
    refresh: () => {
      if (mode === "live" && token) {
        void loadLive(token);
      } else {
        setData(demoSnapshot());
      }
      void probe();
    },
  };
}

export type PlatformContextValue = ReturnType<typeof usePlatform>;

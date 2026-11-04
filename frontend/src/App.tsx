import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { PlatformProvider } from "./context/PlatformContext";
import { Shell } from "./layout/Shell";
import { CommandCentre } from "./pages/CommandCentre";
import { DefenceLab } from "./pages/DefenceLab";
import { EvidenceLab } from "./pages/EvidenceLab";
import { HypothesisArena } from "./pages/HypothesisArena";
import { InvestigationStudio } from "./pages/InvestigationStudio";
import { ReasoningEngine } from "./pages/ReasoningEngine";
import { ResearchObservatory } from "./pages/ResearchObservatory";
import { SignIn } from "./pages/SignIn";
import { SystemControl } from "./pages/SystemControl";
import { TelemetryOps } from "./pages/TelemetryOps";

const ThreatGraph = lazy(async () => {
  const module = await import("./pages/ThreatGraph");
  return { default: module.ThreatGraph };
});

export function App() {
  return (
    <BrowserRouter>
      <PlatformProvider>
        <Routes>
          <Route path="/session" element={<SignIn />} />
          <Route element={<Shell />}>
            <Route path="/" element={<CommandCentre />} />
            <Route path="/telemetry" element={<TelemetryOps />} />
            <Route path="/evidence" element={<EvidenceLab />} />
            <Route path="/investigations" element={<InvestigationStudio />} />
            <Route path="/investigations/:caseId" element={<InvestigationStudio />} />
            <Route
              path="/graph"
              element={
                <Suspense fallback={<p className="muted">Loading graph…</p>}>
                  <ThreatGraph />
                </Suspense>
              }
            />
            <Route path="/reasoning" element={<ReasoningEngine />} />
            <Route path="/hypotheses" element={<HypothesisArena />} />
            <Route path="/defence" element={<DefenceLab />} />
            <Route path="/research" element={<ResearchObservatory />} />
            <Route path="/control" element={<SystemControl />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PlatformProvider>
    </BrowserRouter>
  );
}

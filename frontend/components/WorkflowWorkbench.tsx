"use client";

import { useEffect, useMemo, useState } from "react";

import {
  approveWorkflow,
  executeWorkflow,
  getApprovals,
  getHormuzDecisionClock,
  getHormuzReplay,
  getNetworkSummary,
  getRefineries,
  proposeWorkflow,
  runMultiRefineryAllocation,
  type ApprovalRecord,
  type AgentTraceEntry,
  type CanonicalIntelligenceCase,
  type CrisisReplay,
  type DecisionClock,
  type MultiRefineryAllocationResult,
  type MultiRefineryDemandLine,
  type MultiRefineryRequest,
  type NetworkSummary,
  type Portfolio,
  type Refinery,
  type WorkflowAssumptions,
  type WorkflowExecution,
  type WorkflowProposal,
} from "../lib/api";
import CrisisReplaySurface from "./CrisisReplaySurface";
import DecisionClockSurface from "./DecisionClockSurface";
import DecisionSafetyGate from "./DecisionSafetyGate";
import MultiRefineryAllocationSurface from "./MultiRefineryAllocationSurface";

const DEMO_SIGNAL = "Shipping advisory: elevated military activity near the Strait of Hormuz may disrupt India-bound crude cargoes over the coming days.";

const JOURNEY_STAGES = [
  { id: "stage-1", number: "01", label: "Crisis evidence" },
  { id: "stage-2", number: "02", label: "Analyst review" },
  { id: "stage-3", number: "03", label: "National impact" },
  { id: "stage-4", number: "04", label: "Safety & options" },
  { id: "stage-5", number: "05", label: "Executive action" },
] as const;

function number(value: number): string {
  return new Intl.NumberFormat("en-IN").format(Math.round(value));
}

function compactCurrency(value: number): string {
  if (value <= 0) return "$0";
  return `$${new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(value)}`;
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function providerLabel(status: string | undefined): string {
  if (!status) return "Not called";
  if (status === "Cached demo result") return "Local deterministic fallback";
  return status === "Live API" ? "Gemini API" : status;
}

function normalizeAssumptions(assumptions: WorkflowAssumptions): WorkflowAssumptions {
  return {
    ...assumptions,
    spr_bridge_opt_in: assumptions.spr_bridge_opt_in ?? false,
    government_authorization_assumed_for_scenario: assumptions.government_authorization_assumed_for_scenario ?? false,
    spr_bridge_duration_days: assumptions.spr_bridge_duration_days ?? 7,
  };
}

function scrollToStage(stageId: string): void {
  window.requestAnimationFrame(() => document.getElementById(stageId)?.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function bridgeSummary(portfolio: Portfolio): { headline: string; detail: string } {
  const bridge = portfolio.spr_bridge;
  if (!bridge) return { headline: "Bridge not modelled", detail: "This API response did not include a strategic-reserve contingency." };
  if (bridge.status === "CONTINGENCY_ALLOCATED") {
    return {
      headline: `${number(bridge.bridge_volume_bpd)} bpd for ${bridge.bridge_duration_days} days`,
      detail: "Finite simulated contingency. Human and government authorization remain required.",
    };
  }
  return {
    headline: bridge.status === "NOT_NEEDED" ? "Bridge not needed" : "Bridge not requested",
    detail: bridge.status === "NOT_NEEDED" ? "Seeded external alternatives cover the confirmed demand." : "Requires explicit analyst opt-in and a scenario authorization assumption.",
  };
}

function buildNationalDemandLines(primaryRefinery: string, primaryVolume: number, availableRefineries: Refinery[]): MultiRefineryDemandLine[] | undefined {
  const primary = primaryRefinery.trim();
  const supportRefineries = availableRefineries
    .map((item) => item.name)
    .filter((name) => name.toLocaleLowerCase() !== primary.toLocaleLowerCase())
    .slice(0, 2);

  if (!primary || supportRefineries.length < 1) return undefined;

  return [
    { refinery: primary, required_volume_bpd: primaryVolume, source_status: "User-entered" },
    ...supportRefineries.map((refinery) => ({ refinery, required_volume_bpd: 10_000, source_status: "Simulated" as const })),
  ];
}

function optionalScopeUnsupported(cause: unknown): boolean {
  const message = cause instanceof Error ? cause.message.toLowerCase() : "";
  return message.includes("national_demand_lines") || message.includes("extra inputs") || message.includes("extra_forbidden");
}

function stageState(index: number, proposal: WorkflowProposal | null, execution: WorkflowExecution | null, approved: boolean): "current" | "complete" | "pending" {
  if (!proposal) return index === 0 ? "current" : "pending";
  if (!execution) return index < 1 ? "complete" : index === 1 ? "current" : "pending";
  if (execution.status === "BLOCKED") return index < 3 ? "complete" : index === 3 ? "current" : "pending";
  if (!approved) return index < 4 ? "complete" : index === 4 ? "current" : "pending";
  return "complete";
}

function EmptyStage({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="stage-placeholder"><strong>{title}</strong><p>{children}</p></div>;
}

export default function WorkflowWorkbench() {
  const [summary, setSummary] = useState<NetworkSummary | null>(null);
  const [refineries, setRefineries] = useState<Refinery[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [replay, setReplay] = useState<CrisisReplay | null>(null);
  const [decisionClock, setDecisionClock] = useState<DecisionClock | null>(null);
  const [multiRefineryResult, setMultiRefineryResult] = useState<MultiRefineryAllocationResult | null>(null);
  const [signalText, setSignalText] = useState(DEMO_SIGNAL);
  const [refinery, setRefinery] = useState("Jamnagar");
  const [requiredVolume, setRequiredVolume] = useState(210_000);
  const [analystName, setAnalystName] = useState("Demo Procurement Lead");
  const [proposal, setProposal] = useState<WorkflowProposal | null>(null);
  const [draftAssumptions, setDraftAssumptions] = useState<WorkflowAssumptions | null>(null);
  const [execution, setExecution] = useState<WorkflowExecution | null>(null);
  const [workflowApproval, setWorkflowApproval] = useState<ApprovalRecord | null>(null);
  const [approvalDecision, setApprovalDecision] = useState<"APPROVED" | "REJECTED" | "DEFERRED">("APPROVED");
  const [approvalJustification, setApprovalJustification] = useState("Approve for commercial validation only; no purchase order is authorised.");
  const [loading, setLoading] = useState(true);
  const [clockLoading, setClockLoading] = useState(false);
  const [multiRefineryLoading, setMultiRefineryLoading] = useState(false);
  const [working, setWorking] = useState<"signal" | "execute" | "approval" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastLocalResponseAt, setLastLocalResponseAt] = useState<Date | null>(null);

  async function loadWorkspace(): Promise<void> {
    setLoading(true);
    setError(null);
    try {
      const [network, loadedRefineries, loadedApprovals, loadedReplay] = await Promise.all([
        getNetworkSummary(),
        getRefineries(),
        getApprovals(),
        getHormuzReplay().catch(() => null),
      ]);
      setSummary(network);
      setRefineries(loadedRefineries);
      setApprovals(loadedApprovals);
      setReplay(loadedReplay);
      setLastLocalResponseAt(new Date());
    } catch {
      setError("Unable to reach the local PetraVigil API. Start the API on port 8000, then retry this workspace.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  const selectedPortfolio = useMemo(
    () => execution?.portfolios?.portfolios.find((portfolio) => portfolio.label === execution.transparency?.selected_portfolio),
    [execution],
  );
  const caseContext: CanonicalIntelligenceCase | null = execution?.case_context ?? proposal?.case_context ?? null;
  const nationalImpact = multiRefineryResult ?? execution?.national_impact ?? null;
  const nationalImpactOrigin = multiRefineryResult ? "sensitivity" : execution?.national_impact ? "canonical" : "sensitivity";
  const selectedRouteNames = useMemo(() => selectedPortfolio?.allocations.map((allocation) => allocation.route) ?? [], [selectedPortfolio]);
  const volumeIsValid = Number.isFinite(requiredVolume) && requiredVolume >= 50_000 && requiredVolume <= 500_000;
  const sprBridgeOptedIn = draftAssumptions?.spr_bridge_opt_in ?? false;
  const sprAssumptionsAreValid = !sprBridgeOptedIn || Boolean(draftAssumptions?.government_authorization_assumed_for_scenario);
  const trace: AgentTraceEntry[] = execution?.agent_trace ?? proposal?.agent_trace ?? [];
  const providerStatus = proposal?.processed_signal.gemini.provider_status;

  function resetDependentWork(): void {
    setProposal(null);
    setDraftAssumptions(null);
    setExecution(null);
    setWorkflowApproval(null);
    setDecisionClock(null);
    setError(null);
    setMultiRefineryResult(null);
  }

  function loadCanonicalCase(): void {
    setSignalText(DEMO_SIGNAL);
    resetDependentWork();
    scrollToStage("stage-2");
  }

  async function handleApprovalDelayChange(hours: number): Promise<void> {
    setClockLoading(true);
    try {
      const next = await getHormuzDecisionClock(hours);
      setDecisionClock(next);
      setLastLocalResponseAt(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to recalculate the local decision-clock sensitivity.");
    } finally {
      setClockLoading(false);
    }
  }

  async function loadDecisionClockForCase(): Promise<void> {
    if (decisionClock || caseContext?.decision_clock_context.status !== "LINKED") return;
    setClockLoading(true);
    setError(null);
    try {
      const next = await getHormuzDecisionClock();
      setDecisionClock(next);
      setLastLocalResponseAt(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to load the local decision-clock context.");
    } finally {
      setClockLoading(false);
    }
  }

  async function handleMultiRefineryAllocation(payload: MultiRefineryRequest): Promise<void> {
    setMultiRefineryLoading(true);
    setError(null);
    try {
      const next = await runMultiRefineryAllocation(payload);
      setMultiRefineryResult(next);
      setLastLocalResponseAt(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to allocate the shared refinery cargo lanes.");
    } finally {
      setMultiRefineryLoading(false);
    }
  }

  async function handlePropose(): Promise<void> {
    setWorking("signal");
    setError(null);
    try {
      const basePayload = { text: signalText, refinery, required_volume_bpd: requiredVolume };
      const nationalDemandLines = buildNationalDemandLines(refinery, requiredVolume, refineries);
      let next: WorkflowProposal;
      try {
        next = await proposeWorkflow(nationalDemandLines ? { ...basePayload, national_demand_lines: nationalDemandLines } : basePayload);
      } catch (cause) {
        if (!nationalDemandLines || !optionalScopeUnsupported(cause)) throw cause;
        next = await proposeWorkflow(basePayload);
      }
      setProposal(next);
      setDraftAssumptions(normalizeAssumptions(next.proposed_assumptions));
      setExecution(null);
      setWorkflowApproval(null);
      setDecisionClock(null);
      setLastLocalResponseAt(new Date());
      scrollToStage("stage-2");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to analyse this signal.");
    } finally {
      setWorking(null);
    }
  }

  function updateAssumption<K extends keyof WorkflowAssumptions>(key: K, value: WorkflowAssumptions[K]): void {
    setDraftAssumptions((current) => current ? { ...current, [key]: value } : current);
    setExecution(null);
    setWorkflowApproval(null);
    setMultiRefineryResult(null);
  }

  function updateSprBridgeOptIn(enabled: boolean): void {
    setDraftAssumptions((current) => current ? {
      ...current,
      spr_bridge_opt_in: enabled,
      government_authorization_assumed_for_scenario: enabled ? Boolean(current.government_authorization_assumed_for_scenario) : false,
    } : current);
    setExecution(null);
    setWorkflowApproval(null);
    setMultiRefineryResult(null);
  }

  async function handleExecute(): Promise<void> {
    if (!proposal || !draftAssumptions) return;
    setWorking("execute");
    setError(null);
    setWorkflowApproval(null);
    setMultiRefineryResult(null);
    try {
      const next = await executeWorkflow(proposal.workflow_id, { analyst_name: analystName, assumptions: normalizeAssumptions(draftAssumptions) });
      setExecution(next);
      setLastLocalResponseAt(new Date());
      scrollToStage(next.status === "BLOCKED" ? "stage-4" : "stage-3");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to run the confirmed decision workflow.");
    } finally {
      setWorking(null);
    }
  }

  async function handleApproval(): Promise<void> {
    if (!execution?.recommendation_id) return;
    setWorking("approval");
    setError(null);
    try {
      const approval = await approveWorkflow(execution.workflow_id, {
        decision: approvalDecision,
        decided_by: analystName,
        justification: approvalJustification,
      });
      setApprovals((current) => [approval, ...current.filter((item) => item.approval_id !== approval.approval_id)].slice(0, 6));
      setWorkflowApproval(approval);
      setLastLocalResponseAt(new Date());
      scrollToStage("stage-5");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to record the local decision.");
    } finally {
      setWorking(null);
    }
  }

  return (
    <main className="workspace">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">PV</span>
          <div>
            <p className="eyebrow">DECISION INTELLIGENCE</p>
            <h1>PetraVigil</h1>
            <p className="subtitle">Evidence-first energy supply resilience</p>
          </div>
        </div>
        <div className="topbar-status" aria-live="polite">
          <span className="status"><span aria-hidden="true" /> Local prototype</span>
          <small>{lastLocalResponseAt ? `Last local API response ${lastLocalResponseAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Connecting to local API"}</small>
        </div>
      </header>

      <section className="case-hero" aria-labelledby="workspace-title">
        <div>
          <p className="eyebrow">ANALYST-CONFIRMED DECISION JOURNEY</p>
          <h2 id="workspace-title">Turn uncertain disruption evidence into a reviewable choice.</h2>
          <p>PetraVigil keeps the evidence, assumptions, constraints, and human decision linked. Gemini interprets unstructured text only when configured; deterministic services calculate risk, scenarios, and feasible portfolios.</p>
        </div>
        <div className="hero-actions">
          <button type="button" className="secondary-button" onClick={loadCanonicalCase}>Start the canonical Hormuz case</button>
          <p className="local-data-note">Local prototype: user-entered signals, historical seeded network context, and simulated scenario outputs. No procurement action is executed.</p>
        </div>
      </section>

      <nav className="journey-nav" aria-label="Guided decision journey">
        {JOURNEY_STAGES.map((stage, index) => {
          const state = stageState(index, proposal, execution, Boolean(workflowApproval));
          return <button type="button" className={`journey-nav-step is-${state}`} onClick={() => scrollToStage(stage.id)} aria-current={state === "current" ? "step" : undefined} key={stage.id}><span>{stage.number}</span><strong>{stage.label}</strong></button>;
        })}
      </nav>

      {error && <section className="error-panel" role="alert"><p>{error}</p><button type="button" className="secondary-button" onClick={() => void loadWorkspace()}>Retry local connection</button></section>}
      {loading && <section className="loading-shell" aria-label="Loading local decision workspace"><div className="skeleton skeleton-title" /><div className="skeleton-grid"><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /></div></section>}

      <section id="stage-1" className="journey-stage" aria-labelledby="stage-1-title">
        <div className="stage-index">01</div>
        <div className="stage-content">
          <div className="stage-heading"><div><p className="eyebrow">UNDERSTAND THE CRISIS</p><h3 id="stage-1-title">Start with geography, evidence, and what is explicitly unknown.</h3><p>The replay is a source-labelled local scenario—not live vessel tracking, market data, or an operational routing instruction.</p></div><span className="status-chip">Evidence context</span></div>
          <div className="provenance-strip" aria-label="Current data provenance"><span>Signal <strong>User-entered</strong></span><span>Network <strong>{summary?.data_status ?? "Loading"}</strong></span><span>Replay <strong>Simulated / historical</strong></span><span>Execution <strong>Local only</strong></span></div>
          {caseContext && <article className="case-evidence-summary" aria-label="Case evidence ledger">
            <div className="case-evidence-heading">
              <div><p className="eyebrow">CASE {caseContext.case_id}</p><h4>Evidence is attached to this decision case.</h4></div>
              <span className="status-chip">{caseContext.evidence_validation.status.replaceAll("_", " ")}</span>
            </div>
            <p>{caseContext.evidence_validation.rationale}</p>
            <div className="case-evidence-metrics">
              <span><small>Independent sources</small><strong>{caseContext.evidence_validation.independently_verified_evidence_count}</strong></span>
              <span><small>Reviewable items</small><strong>{caseContext.evidence_validation.unverified_evidence_count}</strong></span>
              <span><small>Validation confidence</small><strong>{percent(caseContext.evidence_validation.validation_confidence)}</strong></span>
            </div>
            <div className="evidence-ledger">
              {caseContext.evidence_ledger.map((item) => <article key={item.evidence_id}>
                <div><strong>{item.label}</strong><span>{item.validation_status.replaceAll("_", " ")}</span></div>
                <p>{item.detail}</p>
                <small>{item.source_status} source status {item.requires_analyst_review ? "- analyst review required" : ""}</small>
              </article>)}
            </div>
            <div className="case-context-notes"><p><strong>Replay:</strong> {caseContext.replay_context.note}</p><p><strong>Clock:</strong> {caseContext.decision_clock_context.note}</p></div>
          </article>}
          {replay ? <CrisisReplaySurface replay={replay} selectedRoutes={selectedRouteNames} onUseReplay={(signal) => { setSignalText(signal); resetDependentWork(); scrollToStage("stage-2"); }} /> : <EmptyStage title="Replay context unavailable">The workflow can still accept a user-entered signal. The optional local replay endpoint is not responding.</EmptyStage>}
        </div>
      </section>

      <section id="stage-2" className="journey-stage" aria-labelledby="stage-2-title">
        <div className="stage-index">02</div>
        <div className="stage-content">
          <div className="stage-heading"><div><p className="eyebrow">ANALYST REVIEW AND SCENARIO</p><h3 id="stage-2-title">Create a case, inspect the extraction, then sign off on assumptions.</h3><p>The workflow stops before simulation. An analyst can edit every material scenario input before any optimization runs.</p></div><span className="status-chip">Human gate</span></div>

          <div className="intake-grid">
            <label className="input-group">Signal text<textarea value={signalText} onChange={(event) => { setSignalText(event.target.value); resetDependentWork(); }} aria-label="Signal text" /></label>
            <div className="intake-settings">
              <label className="input-group">Target refinery<select value={refinery} onChange={(event) => { setRefinery(event.target.value); resetDependentWork(); }}>{refineries.map((item) => <option value={item.name} key={item.name}>{item.name} · {item.operator}</option>)}</select></label>
              <label className="input-group">Required replacement volume (bpd)<input type="number" min="50000" max="500000" step="10000" value={requiredVolume} aria-invalid={!volumeIsValid} onChange={(event) => { setRequiredVolume(Number(event.target.value)); resetDependentWork(); }} />{!volumeIsValid && <small className="field-error">Enter 50,000–500,000 bpd.</small>}</label>
              <label className="input-group">Analyst name<input value={analystName} onChange={(event) => setAnalystName(event.target.value)} minLength={2} /></label>
              <button type="button" onClick={handlePropose} disabled={working !== null || signalText.trim().length < 20 || analystName.trim().length < 2 || !volumeIsValid}>{working === "signal" ? "Structuring the local case…" : "Analyse signal and propose assumptions"}</button>
            </div>
          </div>

          {proposal && draftAssumptions && <>
            <article className="case-summary-bar" aria-live="polite"><span>Case {proposal.workflow_id.slice(0, 12)}</span><strong>{proposal.processed_signal.gemini.proposal.event_type.replaceAll("_", " ")}</strong><span>{proposal.processed_signal.risk_scores[0] ? `${proposal.processed_signal.risk_scores[0].corridor_id} · ${percent(proposal.processed_signal.risk_scores[0].score)}` : "No linked corridor"}</span><span>{providerLabel(proposal.processed_signal.gemini.provider_status)}</span></article>
            <div className="review-grid">
              <article><p className="eyebrow">Structured proposal</p><h4>{proposal.processed_signal.gemini.proposal.summary}</h4><p className="muted">Severity {proposal.processed_signal.gemini.proposal.severity}/10 · extraction confidence {percent(proposal.processed_signal.gemini.proposal.confidence)}</p><p className="evidence-note">{proposal.processed_signal.gemini.proposal.evidence_note}</p></article>
              <article><p className="eyebrow">Entity and corridor checks</p>{proposal.processed_signal.entity_resolutions.map((item) => <p className="audit-row" key={`${item.entity_type}-${item.entity}`}><strong>{item.entity}</strong><span className={item.resolved ? "resolved" : "unresolved"}>{item.resolved ? `Matched: ${item.canonical_name}` : "Requires review"}</span></p>)}{proposal.processed_signal.risk_scores.map((risk) => <div className="risk-card" key={risk.corridor_id}><strong>{risk.corridor_id}</strong><span>{percent(risk.score)}</span><small>Geopolitical {percent(risk.components.geopolitical)} · chokepoint {percent(risk.components.chokepoint_concentration)} · maritime {percent(risk.components.maritime_anomaly)}</small></div>)}</article>
            </div>

            <fieldset className="assumption-form"><legend>Analyst confirmation gate</legend><p className="muted">These values are proposed from the extraction and seeded corridor score. They are editable assumptions—not live facts.</p>
              <div className="scenario-controls">
                <label>Closure severity <strong>{percent(draftAssumptions.closure_severity)}</strong><input type="range" min="0.2" max="1" step="0.05" value={draftAssumptions.closure_severity} aria-valuetext={`${percent(draftAssumptions.closure_severity)} closure severity`} onChange={(event) => updateAssumption("closure_severity", Number(event.target.value))} /></label>
                <label>Disruption duration <strong>{draftAssumptions.disruption_duration_days} days</strong><input type="range" min="5" max="90" step="1" value={draftAssumptions.disruption_duration_days} aria-valuetext={`${draftAssumptions.disruption_duration_days} disruption days`} onChange={(event) => updateAssumption("disruption_duration_days", Number(event.target.value))} /></label>
                <label>Alternative route capacity <strong>{percent(draftAssumptions.alternative_route_capacity_ratio)}</strong><input type="range" min="0.3" max="1" step="0.05" value={draftAssumptions.alternative_route_capacity_ratio} aria-valuetext={`${percent(draftAssumptions.alternative_route_capacity_ratio)} alternative route capacity`} onChange={(event) => updateAssumption("alternative_route_capacity_ratio", Number(event.target.value))} /></label>
              </div>
              <div className="reproducibility-controls">
                <label>Brent elasticity<input type="number" min="0.1" max="30" step="0.1" value={draftAssumptions.brent_elasticity_usd_per_mmbpd} onChange={(event) => updateAssumption("brent_elasticity_usd_per_mmbpd", Number(event.target.value))} /><small>USD per MMBPD</small></label>
                <label>Simulation runs<input type="number" min="100" max="5000" step="100" value={draftAssumptions.n_runs} onChange={(event) => updateAssumption("n_runs", Number(event.target.value))} /><small>Reproducible Monte Carlo sample</small></label>
                <label>Random seed<input type="number" min="0" step="1" value={draftAssumptions.random_seed} onChange={(event) => updateAssumption("random_seed", Number(event.target.value))} /><small>Retain to reproduce the result</small></label>
              </div>
              <fieldset className="spr-bridge-controls"><legend>Strategic reserve contingency</legend><p>Only model a finite bridge when an analyst records the scenario authorization assumption. This prototype does not verify inventory or authorize a drawdown.</p><label className="spr-check"><input type="checkbox" checked={sprBridgeOptedIn} onChange={(event) => updateSprBridgeOptIn(event.target.checked)} /><span>Consider a strategic reserve bridge if seeded external alternatives leave a residual gap.</span></label><label className="spr-check"><input type="checkbox" disabled={!sprBridgeOptedIn} checked={draftAssumptions.government_authorization_assumed_for_scenario ?? false} onChange={(event) => updateAssumption("government_authorization_assumed_for_scenario", event.target.checked)} /><span>I record a user-entered scenario assumption that government authorization would be sought. This is not authorization.</span></label><label className="spr-duration">Maximum bridge duration <strong>{draftAssumptions.spr_bridge_duration_days ?? 7} days</strong><input type="range" min="1" max="7" step="1" disabled={!sprBridgeOptedIn} value={draftAssumptions.spr_bridge_duration_days ?? 7} onChange={(event) => updateAssumption("spr_bridge_duration_days", Number(event.target.value))} /></label>{!sprAssumptionsAreValid && <small className="field-error">Record the authorization assumption or disable the contingency before running the model.</small>}</fieldset>
              <p className="reproducibility-note">All scenario inputs are persisted with the workflow. The random seed remains visible so results can be reproduced.</p><p className="assumption-rationale">{draftAssumptions.rationale}</p><ul className="unknowns-list">{draftAssumptions.unknowns.map((item) => <li key={item}>{item}</li>)}</ul><button type="button" onClick={handleExecute} disabled={working !== null || !sprAssumptionsAreValid}>{working === "execute" ? "Running the confirmed workflow…" : "Confirm assumptions and calculate impact"}</button>
            </fieldset>
          </>}

          <details className="context-disclosure"><summary>Inspect the case-linked decision-clock sensitivity</summary>{caseContext?.decision_clock_context.status === "LINKED" ? <>{decisionClock ? <DecisionClockSurface clock={decisionClock} loading={clockLoading} onApprovalDelayChange={handleApprovalDelayChange} /> : <div className="context-load"><p>{caseContext.decision_clock_context.note}</p><button type="button" className="secondary-button" disabled={clockLoading} onClick={() => void loadDecisionClockForCase()}>{clockLoading ? "Loading local timing context..." : "Load local timing context"}</button></div>}</> : <p>A decision-clock context will appear only when this API response links one to the created case.</p>}</details>
        </div>
      </section>

      <section id="stage-3" className="journey-stage" aria-labelledby="stage-3-title">
        <div className="stage-index">03</div>
        <div className="stage-content">
          <div className="stage-heading"><div><p className="eyebrow">NATIONAL IMPACT AND OPTIMIZATION</p><h3 id="stage-3-title">Quantify the disruption before choosing a procurement posture.</h3><p>Scenario output is reproducible and simulated. The shared-cargo drill keeps a physical route finite across refineries rather than multiplying it per site.</p></div><span className="status-chip">Constrained models</span></div>
          {execution?.simulation ? <>
            <div className="impact-metrics"><article><span>P50 supply impact</span><strong>{number(execution.simulation.supply_impact_bpd.p50)} bpd</strong><small>P10–P90: {number(execution.simulation.supply_impact_bpd.p10)}–{number(execution.simulation.supply_impact_bpd.p90)}</small></article><article><span>P50 Brent premium</span><strong>${execution.simulation.brent_premium_usd_per_bbl.p50}/bbl</strong><small>P10–P90: ${execution.simulation.brent_premium_usd_per_bbl.p10}–${execution.simulation.brent_premium_usd_per_bbl.p90}</small></article><article><span>Simulated avoided exposure</span><strong>{compactCurrency(execution.simulation.act_now_avoided_cost_usd)}</strong><small>{number(execution.assumptions.n_runs)} reproducible runs</small></article></div>
            {execution.portfolios ? <article className="optimizer-brief"><p className="eyebrow">Optimizer outcome</p><strong>{execution.portfolios.portfolios.length - 1} feasible contingency postures</strong><span>Comparison {execution.portfolios.comparison_id} uses refinery compatibility, seeded capacity, and route-risk constraints.</span>{selectedPortfolio && <small>Current selected posture: {selectedPortfolio.label.replaceAll("_", " ")}.</small>}</article> : <article className="optimizer-brief"><p className="eyebrow">Optimizer outcome</p><strong>Portfolio withheld</strong><span>The scenario impact can be reviewed, but the safety gate did not release procurement options from this workflow.</span></article>}
            {caseContext && <article className="national-scope-summary"><div><p className="eyebrow">Case-linked national scope</p><strong>{caseContext.national_capacity_request.demand_lines.length} refinery demand lines</strong><span>{caseContext.national_capacity_request.demand_lines.map((line) => `${line.refinery} ${number(line.required_volume_bpd)} bpd`).join(" / ")}</span></div><p>Supporting refinery demand is explicitly source-labelled inside this local scenario; it is not a live national order book.</p></article>}
            {nationalImpactOrigin === "canonical" ? <p className="national-impact-status">The shared-capacity allocation below was generated as part of this confirmed case. It is a national-impact constraint, not a separate preloaded demo.</p> : <p className="national-impact-status">This API version did not return a case-linked national allocation, or you are viewing a separate sensitivity. Any result below remains clearly separate from the confirmed workflow.</p>}
            <MultiRefineryAllocationSurface result={nationalImpact} resultOrigin={nationalImpactOrigin} loading={multiRefineryLoading} onRun={handleMultiRefineryAllocation} />
          </> : <EmptyStage title="Awaiting analyst-confirmed scenario">Confirm assumptions in Stage 2 to generate reproducible impact ranges and open the optional national shared-cargo drill.</EmptyStage>}
        </div>
      </section>

      <section id="stage-4" className="journey-stage" aria-labelledby="stage-4-title">
        <div className="stage-index">04</div>
        <div className="stage-content">
          <div className="stage-heading"><div><p className="eyebrow">SAFETY AND RECOMMENDATION OPTIONS</p><h3 id="stage-4-title">Refuse unsafe recommendations; compare feasible alternatives when evidence clears.</h3><p>The safety gate preserves blockers and next actions rather than inventing a portfolio when capacity or confidence is insufficient.</p></div><span className="status-chip">Decision-safe</span></div>
          {execution ? <>
            {execution.decision_safety_gate ? <DecisionSafetyGate gate={execution.decision_safety_gate} /> : <article className="safety-fallback"><strong>{execution.status === "BLOCKED" ? "No recommendation was produced" : "Safety response unavailable from this local API version"}</strong><p>{execution.blocking_reason ?? "Review the workflow evidence, assumptions, and procurement constraints before making a human decision."}</p></article>}
            {execution.status === "COMPLETED" && execution.portfolios && execution.transparency && <>
              <div className="portfolio-grid" aria-label="Procurement portfolio comparison">{execution.portfolios.portfolios.map((portfolio) => {
                const bridge = bridgeSummary(portfolio);
                return <article className={`portfolio-card ${portfolio.label === execution.transparency?.selected_portfolio ? "is-selected" : ""}`} key={portfolio.portfolio_id}><p className="eyebrow">{portfolio.label.replaceAll("_", " ")}</p><strong>{portfolio.total_volume_bpd ? `${number(portfolio.total_volume_bpd)} bpd` : "No intervention"}</strong><span>{portfolio.total_volume_bpd ? `${compactCurrency(portfolio.total_daily_cost_usd)}/day` : "Remaining on exposed route"}</span><dl><div><dt>Route risk</dt><dd>{percent(portfolio.weighted_route_risk)}</dd></div><div><dt>Exposure avoided</dt><dd>{compactCurrency(portfolio.expected_avoided_exposure_usd)}</dd></div></dl><p>{portfolio.rationale}</p><div className="spr-summary"><span>Strategic reserve</span><strong>{bridge.headline}</strong><small>{bridge.detail}</small></div><details><summary>Inspect allocations ({portfolio.allocations.length})</summary>{portfolio.allocations.length ? <ul>{portfolio.allocations.map((item) => <li key={`${item.crude_grade}-${item.route}`}>{item.crude_grade}: {number(item.volume_bpd)} bpd via {item.route}</li>)}</ul> : <p>No proactive allocation.</p>}</details></article>;
              })}</div>
              {selectedPortfolio && <article className="recommendation-detail"><div><p className="eyebrow">Selected recommendation · {execution.recommendation_id}</p><h4>{execution.transparency.why_this_won}</h4></div><div className="recommendation-scoreline"><span><small>Decision confidence</small><strong>{percent(execution.transparency.confidence)}</strong></span>{execution.transparency.requires_human_approval && <span className="human-gate">Human approval required</span>}</div><div className="transparency-grid"><div><strong>Evidence</strong><ul>{execution.transparency.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Assumptions</strong><ul>{execution.transparency.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Risk factors</strong><ul>{execution.transparency.risk_factors.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Rejected alternatives</strong><ul>{execution.transparency.rejected_alternatives.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Open unknowns</strong><ul>{execution.transparency.unknowns.map((item) => <li key={item}>{item}</li>)}</ul></div></div></article>}
            </>}
          </> : <EmptyStage title="Awaiting safety evaluation">Run the analyst-confirmed scenario to see either a structured no-recommendation state or constrained procurement alternatives.</EmptyStage>}
        </div>
      </section>

      <section id="stage-5" className="journey-stage" aria-labelledby="stage-5-title">
        <div className="stage-index">05</div>
        <div className="stage-content">
          <div className="stage-heading"><div><p className="eyebrow">EXECUTIVE BRIEF AND ACTION SUMMARY</p><h3 id="stage-5-title">End with a concise explanation and a human-owned decision record.</h3><p>The brief explains a constrained output. It does not create facts, contact suppliers, or execute an external action.</p></div><span className="status-chip">Human-owned action</span></div>
          {execution?.status === "COMPLETED" && execution.transparency ? <>
            {execution.executive_brief && <article className="executive-brief"><div className="brief-heading"><div><p className="eyebrow">Executive explanation</p><h4>{providerLabel(execution.executive_brief.provider_status)}</h4></div><span className="status-chip">Constrained narrative</span></div>{execution.executive_brief.provider_status === "Cached demo result" && <p className="fallback-notice">Gemini is not configured, so this explanation uses deterministic local wording and does not create new facts.</p>}<p className="brief-copy">{execution.executive_brief.explanation}</p><ul>{execution.executive_brief.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul><p className="next-question">Next decision question: {execution.executive_brief.next_question}</p></article>}
            <article className="action-summary"><div><p className="eyebrow">Decision-ready summary</p><strong>{selectedPortfolio?.label.replaceAll("_", " ") ?? "Recommendation pending"}</strong><span>{execution.recommendation_id} · local decision support only</span></div><div><span>Analyst</span><strong>{execution.analyst_name}</strong></div><div><span>Approval requirement</span><strong>Human review</strong></div>{selectedPortfolio?.spr_bridge?.status === "CONTINGENCY_ALLOCATED" && <div><span>SPR contingency</span><strong>{number(selectedPortfolio.spr_bridge.bridge_volume_bpd)} bpd / {selectedPortfolio.spr_bridge.bridge_duration_days} days</strong></div>}</article>
            <article className="approval-panel"><div className="approval-heading"><div><p className="eyebrow">Local human decision</p><h4>Record the outcome against this exact workflow recommendation.</h4></div><span className="status-chip">No external execution</span></div><p>This record creates no purchase order, supplier contact, reserve drawdown, or external workflow.</p>{workflowApproval ? <div className="approval-receipt" role="status"><p className="eyebrow">Decision recorded locally</p><strong>{workflowApproval.decision} · {workflowApproval.recommendation_id}</strong><span>Recorded by {workflowApproval.decided_by} at {new Date(workflowApproval.decided_at).toLocaleString()}</span><p>{workflowApproval.justification}</p></div> : <div className="approval-controls"><label className="input-group">Decision<select value={approvalDecision} onChange={(event) => setApprovalDecision(event.target.value as "APPROVED" | "REJECTED" | "DEFERRED")}><option value="APPROVED">Approve for validation</option><option value="DEFERRED">Defer pending evidence</option><option value="REJECTED">Reject recommendation</option></select></label><label className="input-group">Decision justification<textarea value={approvalJustification} onChange={(event) => setApprovalJustification(event.target.value)} /></label><button type="button" onClick={handleApproval} disabled={working !== null || approvalJustification.trim().length < 10}>{working === "approval" ? "Recording local decision…" : "Record human decision"}</button></div>}</article>
          </> : <EmptyStage title="Awaiting an executable scenario result">An executive explanation and decision record become available only after the safety gate clears a constrained recommendation.</EmptyStage>}
        </div>
      </section>

      <details className="audit-disclosure"><summary>Open the auditable stage trace and local decision history</summary><div className="audit-disclosure-body"><div><p className="eyebrow">Agent trace</p>{trace.length ? <div className="agent-trace">{trace.map((item, index) => <article className={`trace-step is-${item.status.toLowerCase()}`} key={`${item.stage}-${index}`}><span aria-hidden="true">{index + 1}</span><div><div className="trace-heading"><strong>{item.stage}</strong><span>{item.status === "COMPLETED" ? "Complete" : "Review required"}</span></div><p>{item.summary}</p><small>{item.rationale}</small>{item.unknowns.length > 0 && <small className="trace-unknown">Open items: {item.unknowns.slice(0, 2).join(" · ")}{item.unknowns.length > 2 ? ` +${item.unknowns.length - 2} more` : ""}</small>}</div></article>)}</div> : <p className="muted">Analyse a source-labelled signal to begin the persisted audit trail.</p>}</div><div><p className="eyebrow">Local context</p><p className="muted">{summary ? `${summary.countries} countries · ${summary.crude_grades} grades · ${summary.refineries} refineries · ${summary.routes} seeded routes` : "Loading seeded network coverage"}</p><p className="muted">Historical seed data is prototype context, not live supplier availability.</p><p className="eyebrow">Recent local decisions</p>{approvals.length ? approvals.slice(0, 3).map((item) => <p className="history-row" key={item.approval_id}><span>{item.decision}</span><strong>{item.recommendation_id}</strong><small>{new Date(item.decided_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></p>) : <p className="muted">No local decision records yet.</p>}</div></div></details>
    </main>
  );
}

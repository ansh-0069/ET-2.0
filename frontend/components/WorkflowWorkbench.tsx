"use client";

import { useEffect, useMemo, useState } from "react";

import {
  approveWorkflow,
  executeWorkflow,
  getApprovals,
  getNetworkSummary,
  getRefineries,
  proposeWorkflow,
  type ApprovalRecord,
  type AgentTraceEntry,
  type NetworkSummary,
  type Refinery,
  type WorkflowAssumptions,
  type WorkflowExecution,
  type WorkflowProposal,
} from "../lib/api";

const DEMO_SIGNAL = "Shipping advisory: elevated military activity near the Strait of Hormuz may disrupt India-bound crude cargoes over the coming days.";
const WORKFLOW_STAGES = ["Signal", "Intelligence", "Risk", "Economic", "Procurement", "Decision"] as const;

function number(value: number): string {
  return new Intl.NumberFormat("en-IN").format(Math.round(value));
}

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function providerLabel(status: string | undefined): string {
  if (!status) return "Not called";
  if (status === "Cached demo result") return "Local deterministic fallback";
  return status === "Live API" ? "Gemini live API" : status;
}

function stageTrace(trace: AgentTraceEntry[], stage: string): AgentTraceEntry | undefined {
  return trace.find((entry) => entry.stage === stage);
}

export default function WorkflowWorkbench() {
  const [summary, setSummary] = useState<NetworkSummary | null>(null);
  const [refineries, setRefineries] = useState<Refinery[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
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
  const [working, setWorking] = useState<"signal" | "execute" | "approval" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSuccessfulRequestAt, setLastSuccessfulRequestAt] = useState<Date | null>(null);

  useEffect(() => {
    async function loadWorkspace(): Promise<void> {
      try {
        const [network, loadedRefineries, loadedApprovals] = await Promise.all([getNetworkSummary(), getRefineries(), getApprovals()]);
        setSummary(network);
        setRefineries(loadedRefineries);
        setApprovals(loadedApprovals);
        setLastSuccessfulRequestAt(new Date());
      } catch {
        setError("Unable to reach the PetraVigil API. Start the local API on port 8000 and retry.");
      } finally {
        setLoading(false);
      }
    }
    void loadWorkspace();
  }, []);

  const trace = execution?.agent_trace ?? proposal?.agent_trace ?? [];
  const providerStatus = proposal?.processed_signal.gemini.provider_status;
  const volumeIsValid = Number.isFinite(requiredVolume) && requiredVolume >= 50_000 && requiredVolume <= 500_000;
  const selectedPortfolio = useMemo(
    () => execution?.portfolios?.portfolios.find((portfolio) => portfolio.label === execution.transparency?.selected_portfolio),
    [execution],
  );

  function resetDependentWork(): void {
    setProposal(null);
    setDraftAssumptions(null);
    setExecution(null);
    setWorkflowApproval(null);
    setError(null);
  }

  async function handlePropose(): Promise<void> {
    setWorking("signal");
    setError(null);
    try {
      const next = await proposeWorkflow({ text: signalText, refinery, required_volume_bpd: requiredVolume });
      setProposal(next);
      setDraftAssumptions(next.proposed_assumptions);
      setExecution(null);
      setWorkflowApproval(null);
      setLastSuccessfulRequestAt(new Date());
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
  }

  async function handleExecute(): Promise<void> {
    if (!proposal || !draftAssumptions) return;
    setWorking("execute");
    setError(null);
    setWorkflowApproval(null);
    try {
      const next = await executeWorkflow(proposal.workflow_id, { analyst_name: analystName, assumptions: draftAssumptions });
      setExecution(next);
      setLastSuccessfulRequestAt(new Date());
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
      setLastSuccessfulRequestAt(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to record the local decision.");
    } finally {
      setWorking(null);
    }
  }

  function workflowStepState(index: number): "idle" | "active" | "complete" | "blocked" {
    if (execution?.status === "BLOCKED" && index >= 4) return index === 4 ? "blocked" : "idle";
    if (workflowApproval && execution?.status === "COMPLETED") return "complete";
    if (execution?.status === "COMPLETED") return index < 5 ? "complete" : "active";
    if (proposal) return index < 3 ? "complete" : index === 3 ? "active" : "idle";
    return index === 0 ? "active" : "idle";
  }

  return (
    <main className="workspace">
      <div className="ambient-grid" aria-hidden="true" />
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">PV</span>
          <div><p className="eyebrow">DECISION INTELLIGENCE</p><h1>PetraVigil</h1><p className="subtitle">Evidence-first energy supply resilience</p></div>
        </div>
        <div className="topbar-status"><span className="status"><span /> Local decision workspace</span><small>{lastSuccessfulRequestAt ? `Workspace synced ${lastSuccessfulRequestAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Connecting"}</small></div>
      </header>

      <section className="hero case-hero">
        <div><p className="eyebrow">ANALYST-CONFIRMED WORKFLOW</p><h2>Turn one signal into a reviewable procurement decision.</h2><p>Each stage consumes the persisted output of the last. Gemini is used only when configured; the offline fallback is explicitly deterministic. Risk, scenarios, and portfolios remain deterministic services.</p></div>
        <div className="hero-actions"><button className="secondary-button" onClick={() => { setSignalText(DEMO_SIGNAL); resetDependentWork(); }}>Load Hormuz example</button><p className="local-data-note">Prototype data: user-entered signal, historical seeded network, simulated scenario results.</p></div>
      </section>

      <section className="data-status-bar" aria-live="polite">
        <span className="provenance-chip">Signal: User-entered</span>
        <span className="provenance-chip">Network: {summary?.data_status ?? "Loading"}</span>
        <span className="provenance-chip">Narrative: {providerLabel(providerStatus)}</span>
        <span className="provenance-chip">Execution: local only</span>
      </section>

      <ol className="workflow-rail" aria-label="Decision workflow progress">
        {WORKFLOW_STAGES.map((label, index) => <li className={`workflow-step is-${workflowStepState(index)}`} aria-current={workflowStepState(index) === "active" ? "step" : undefined} key={label}><span>{index + 1}</span><strong>{label}</strong></li>)}
      </ol>

      {error && <p className="error">{error}</p>}
      {loading && <section className="loading-shell" aria-label="Loading decision workspace"><div className="skeleton skeleton-title" /><div className="skeleton-grid"><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /></div></section>}

      <section className="stage-card signal-intake-card" data-stage="signal">
        <div className="section-heading"><div><p className="label">01 · SIGNAL INTAKE</p><h3>Start a case with a source-labelled signal</h3><p>User-entered text is retained as unverified evidence. It cannot claim to be a live feed.</p></div><span className="badge">Analyst input</span></div>
        <div className="intake-grid"><label>Signal text<textarea value={signalText} onChange={(event) => { setSignalText(event.target.value); resetDependentWork(); }} aria-label="Signal text" /></label><div className="intake-settings"><label>Target refinery<select value={refinery} onChange={(event) => { setRefinery(event.target.value); resetDependentWork(); }}>{refineries.map((item) => <option value={item.name} key={item.name}>{item.name} · {item.operator}</option>)}</select></label><label>Required replacement volume (bpd)<input type="number" min="50000" max="500000" step="10000" value={requiredVolume} aria-invalid={!volumeIsValid} onChange={(event) => { setRequiredVolume(Number(event.target.value)); resetDependentWork(); }} />{!volumeIsValid && <small className="field-error">Enter 50,000–500,000 bpd.</small>}</label><label>Analyst name<input value={analystName} onChange={(event) => setAnalystName(event.target.value)} minLength={2} /></label><button onClick={handlePropose} disabled={working !== null || signalText.trim().length < 20 || analystName.trim().length < 2 || !volumeIsValid}>{working === "signal" ? "Extracting and scoring..." : "Analyse signal and propose assumptions"}</button></div></div>
      </section>

      {proposal && draftAssumptions && <>
        <section className="case-summary-bar" aria-live="polite"><span>Case {proposal.workflow_id.slice(0, 12)}</span><strong>{proposal.processed_signal.gemini.proposal.event_type.replaceAll("_", " ")}</strong><span>{proposal.processed_signal.risk_scores[0] ? `${proposal.processed_signal.risk_scores[0].corridor_id} · ${percent(proposal.processed_signal.risk_scores[0].score)}` : "No linked corridor"}</span><span>{providerLabel(proposal.processed_signal.gemini.provider_status)}</span></section>

        <section className="stage-card" data-stage="review">
          <div className="section-heading"><div><p className="label">02–03 · INTELLIGENCE AND RISK REVIEW</p><h3>Confirm what the system knows—and what it does not</h3></div><span className={`badge ${proposal.processed_signal.review_required ? "risk-badge medium" : "risk-badge high"}`}>{proposal.processed_signal.review_required ? "Review required" : "Resolved"}</span></div>
          <div className="review-grid"><article><p className="label">Structured proposal</p><h4>{proposal.processed_signal.gemini.proposal.summary}</h4><p className="muted">Severity {proposal.processed_signal.gemini.proposal.severity}/10 · extraction confidence {percent(proposal.processed_signal.gemini.proposal.confidence)}</p><p className="evidence-note">{proposal.processed_signal.gemini.proposal.evidence_note}</p></article><article><p className="label">Entity and corridor checks</p>{proposal.processed_signal.entity_resolutions.map((item) => <p className="audit-row" key={`${item.entity_type}-${item.entity}`}><strong>{item.entity}</strong><span className={item.resolved ? "resolved" : "unresolved"}>{item.resolved ? `Matched: ${item.canonical_name}` : "Requires review"}</span></p>)}{proposal.processed_signal.risk_scores.map((risk) => <div className="risk-card" key={risk.corridor_id}><strong>{risk.corridor_id}</strong><span>{percent(risk.score)}</span><small>Geo {percent(risk.components.geopolitical)} · chokepoint {percent(risk.components.chokepoint_concentration)} · maritime {percent(risk.components.maritime_anomaly)}</small></div>)}</article></div>
          <fieldset className="assumption-form"><legend>Analyst confirmation gate</legend><p className="muted">These values were proposed from the extracted severity, confidence, and corridor score. Edit them before running the scenario.</p><div className="scenario-controls"><label>Closure severity <strong>{percent(draftAssumptions.closure_severity)}</strong><input type="range" min="0.2" max="1" step="0.05" value={draftAssumptions.closure_severity} aria-valuetext={`${percent(draftAssumptions.closure_severity)} closure severity`} onChange={(event) => updateAssumption("closure_severity", Number(event.target.value))} /></label><label>Disruption duration <strong>{draftAssumptions.disruption_duration_days} days</strong><input type="range" min="5" max="90" step="1" value={draftAssumptions.disruption_duration_days} aria-valuetext={`${draftAssumptions.disruption_duration_days} disruption days`} onChange={(event) => updateAssumption("disruption_duration_days", Number(event.target.value))} /></label><label>Alternative route capacity <strong>{percent(draftAssumptions.alternative_route_capacity_ratio)}</strong><input type="range" min="0.3" max="1" step="0.05" value={draftAssumptions.alternative_route_capacity_ratio} aria-valuetext={`${percent(draftAssumptions.alternative_route_capacity_ratio)} alternative route capacity`} onChange={(event) => updateAssumption("alternative_route_capacity_ratio", Number(event.target.value))} /></label></div><div className="reproducibility-controls"><label>Brent elasticity <input type="number" min="0.1" max="30" step="0.1" value={draftAssumptions.brent_elasticity_usd_per_mmbpd} onChange={(event) => updateAssumption("brent_elasticity_usd_per_mmbpd", Number(event.target.value))} /><small>USD per MMBPD</small></label><label>Simulation runs <input type="number" min="100" max="5000" step="100" value={draftAssumptions.n_runs} onChange={(event) => updateAssumption("n_runs", Number(event.target.value))} /><small>Higher count improves stability</small></label><label>Random seed <input type="number" min="0" step="1" value={draftAssumptions.random_seed} onChange={(event) => updateAssumption("random_seed", Number(event.target.value))} /><small>Retain to reproduce this result</small></label></div><p className="reproducibility-note">All six inputs are included in the signed-off scenario request. The seed is visible so the simulation can be reproduced.</p><p className="assumption-rationale">{draftAssumptions.rationale}</p><ul className="unknowns-list">{draftAssumptions.unknowns.map((item) => <li key={item}>{item}</li>)}</ul><button className="accent-button" onClick={handleExecute} disabled={working !== null}>{working === "execute" ? "Running the confirmed workflow..." : "Confirm assumptions and run workflow"}</button></fieldset>
        </section>
      </>}

      {execution?.status === "BLOCKED" && <section className="stage-card stage-gate"><p className="label">WORKFLOW BLOCKED</p><h3>No feasible procurement portfolio was fabricated.</h3><p>{execution.blocking_reason}</p><p className="muted">Adjust the analyst-confirmed volume or capacity assumptions and run a new case.</p></section>}

      {execution?.status === "COMPLETED" && execution.simulation && execution.portfolios && execution.transparency && <>
        <section className="stage-card" data-stage="economic"><div className="section-heading"><div><p className="label">04 · ECONOMIC AGENT</p><h3>Scenario results use the assumptions you confirmed</h3></div><span className="badge">{execution.simulation.data_status}</span></div><div className="metrics"><article className="metric"><span className="metric-label">P50 supply impact</span><strong>{number(execution.simulation.supply_impact_bpd.p50)} bpd</strong><small>P10–P90: {number(execution.simulation.supply_impact_bpd.p10)}–{number(execution.simulation.supply_impact_bpd.p90)}</small></article><article className="metric"><span className="metric-label">P50 Brent premium</span><strong>${execution.simulation.brent_premium_usd_per_bbl.p50}/bbl</strong><small>P10–P90: ${execution.simulation.brent_premium_usd_per_bbl.p10}–${execution.simulation.brent_premium_usd_per_bbl.p90}</small></article><article className="metric"><span className="metric-label">Avoided exposure estimate</span><strong>${number(execution.simulation.act_now_avoided_cost_usd / 1_000_000)}M</strong><small>{execution.assumptions.n_runs.toLocaleString()} reproducible runs</small></article></div></section>

        <section className="stage-card" data-stage="procurement"><div className="section-heading"><div><p className="label">05 · PROCUREMENT AGENT</p><h3>Compare allocations before calling anything “best”</h3></div><span className="badge">OR-Tools constrained optimizer</span></div><div className="portfolio-grid">{execution.portfolios.portfolios.map((portfolio) => <article className={`portfolio-card ${portfolio.label === execution.transparency?.selected_portfolio ? "is-selected" : ""}`} key={portfolio.portfolio_id}><p className="label">{portfolio.label.replaceAll("_", " ")}</p><strong>{portfolio.total_volume_bpd ? `${number(portfolio.total_volume_bpd)} bpd` : "Exposed"}</strong><span>{portfolio.total_volume_bpd ? `$${number(portfolio.total_daily_cost_usd / 1_000_000)}M/day` : "No proactive cost"}</span><span>Route risk {percent(portfolio.weighted_route_risk)}</span><p>{portfolio.rationale}</p>{portfolio.allocations.map((item) => <small key={`${item.crude_grade}-${item.route}`}>{item.crude_grade}: {number(item.volume_bpd)} bpd via {item.route}</small>)}</article>)}</div>{selectedPortfolio && <article className="recommendation-detail"><p className="label">Selected recommendation · {execution.recommendation_id}</p><h4>{execution.transparency.why_this_won}</h4><div className="recommendation-scoreline"><span><small>Decision confidence</small><strong>{percent(execution.transparency.confidence)}</strong></span>{execution.transparency.requires_human_approval && <span className="human-gate">Human approval required</span>}</div><div className="transparency-grid"><div><strong>Evidence</strong><ul>{execution.transparency.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Confirmed assumptions</strong><ul>{execution.transparency.assumptions.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Risk factors</strong><ul>{execution.transparency.risk_factors.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Rejected alternatives</strong><ul>{execution.transparency.rejected_alternatives.map((item) => <li key={item}>{item}</li>)}</ul></div><div><strong>Unknowns</strong><ul>{execution.transparency.unknowns.map((item) => <li key={item}>{item}</li>)}</ul></div></div></article>}</section>

        {execution.executive_brief && <section className="stage-card" data-stage="executive"><div className="section-heading"><div><p className="label">06 · EXECUTIVE AGENT</p><h3>Explain the selected constrained portfolio</h3></div><span className="badge">{providerLabel(execution.executive_brief.provider_status)}</span></div>{execution.executive_brief.provider_status === "Cached demo result" && <p className="fallback-notice">Gemini is not configured, so this explanation uses deterministic local wording and does not create new facts.</p>}<div className="ai-result"><p>{execution.executive_brief.explanation}</p><ul>{execution.executive_brief.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul><p className="next-question">Next: {execution.executive_brief.next_question}</p></div></section>}

        <section className="stage-card approval-panel" data-stage="approval"><div className="section-heading"><div><p className="label">HUMAN DECISION</p><h3>Record an approval against this workflow recommendation</h3></div><span className="badge">Local only · no external execution</span></div><p className="muted">This record applies to {execution.recommendation_id}. It creates no purchase order, supplier contact, or external workflow.</p>{workflowApproval ? <div className="approval-receipt" role="status"><p className="label">Decision recorded locally</p><strong>{workflowApproval.decision} · {workflowApproval.recommendation_id}</strong><span>Recorded by {workflowApproval.decided_by} at {new Date(workflowApproval.decided_at).toLocaleString()}</span><p>{workflowApproval.justification}</p></div> : <div className="approval-controls"><label>Decision<select value={approvalDecision} onChange={(event) => setApprovalDecision(event.target.value as "APPROVED" | "REJECTED" | "DEFERRED")}><option value="APPROVED">Approve for validation</option><option value="DEFERRED">Defer pending evidence</option><option value="REJECTED">Reject recommendation</option></select></label><label>Decision justification<textarea value={approvalJustification} onChange={(event) => setApprovalJustification(event.target.value)} /></label><button className="accent-button" onClick={handleApproval} disabled={working !== null || approvalJustification.trim().length < 10}>{working === "approval" ? "Recording decision..." : "Record human decision"}</button></div>}</section>
      </>}

      <section className="stage-card agent-log" aria-live="polite"><div className="section-heading"><div><p className="label">AUDITABLE AGENT TRACE</p><h3>What each real stage consumed and produced</h3></div><span className="badge">No hidden autonomous execution</span></div>{trace.length ? <div className="agent-trace">{trace.map((item, index) => <article className={`trace-step ${item.status === "COMPLETED" ? "is-complete" : "is-review"}`} key={`${item.stage}-${index}`}><span aria-hidden="true">{index + 1}</span><div className="trace-body"><div className="trace-heading"><strong>{item.stage}</strong><div className="trace-meta"><span className={`trace-status ${item.status === "COMPLETED" ? "is-complete" : "is-review"}`}>{item.status === "COMPLETED" ? "Complete" : "Review required"}</span><small>{percent(item.confidence)} confidence</small></div></div><p>{item.summary}</p><small className="trace-rationale">{item.rationale}</small>{item.unknowns.length > 0 && <small className="trace-unknown">Open items: {item.unknowns.slice(0, 2).join(" · ")}{item.unknowns.length > 2 ? ` +${item.unknowns.length - 2} more` : ""}</small>}</div></article>)}</div> : <p className="empty-stage">Analyse a source-labelled signal to begin the audit trail.</p>}</section>

      <details className="activity-drawer"><summary>Prototype data coverage and local decision history</summary><div className="activity-grid"><div><p className="label">Seeded network</p><p>{summary ? `${summary.countries} countries · ${summary.crude_grades} grades · ${summary.refineries} refineries · ${summary.routes} routes` : "Loading network coverage"}</p><p className="muted">Historical seed data supports the prototype. It is not presented as live supplier availability.</p></div><div><p className="label">Recent local decisions</p>{approvals.length ? approvals.slice(0, 3).map((item) => <p className="history-row" key={item.approval_id}><span className={`approval-status ${item.decision.toLowerCase()}`}>{item.decision}</span><strong>{item.recommendation_id}</strong><span>{new Date(item.decided_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></p>) : <p className="muted">No local decision records yet.</p>}</div></div></details>
    </main>
  );
}

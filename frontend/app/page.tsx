"use client";

import { useEffect, useMemo, useState } from "react";

import {
  explainRecommendation,
  createApproval,
  briefPortfolio,
  extractSignal,
  getAlternatives,
  getApprovals,
  getLatestScenarioRun,
  getNetworkSummary,
  getRefineries,
  getScenarioRun,
  getSignalHistory,
  processSignal,
  generatePortfolios,
  runSimulation,
  runCanonicalScenario,
  type Alternative,
  type ApprovalRecord,
  type ExplanationResult,
  type NetworkSummary,
  type ProcessedSignal,
  type PortfolioComparison,
  type Refinery,
  type ScenarioRun,
  type Simulation,
  type SignalResult,
} from "../lib/api";

const RUN_STORAGE_KEY = "petravigil.phase1.active-run";
const DEMO_SIGNAL = "Shipping advisory: elevated military activity near the Strait of Hormuz may disrupt India-bound crude cargoes over the coming days.";
const LIVE_SIGNALS = [
  "AIS watch: Hormuz traffic density is being re-evaluated",
  "Gemini is ready to translate analyst inputs into an executive brief",
  "Route feasibility remains grounded in the seeded supply network",
  "Decision workspace is monitoring the Persian Gulf to West India corridor",
];
const REPLAY_STEPS = [
  { agent: "SIGINT", label: "Extracting the disruption signal", detail: "Gemini structures the operational alert" },
  { agent: "GEOINT", label: "Resolving corridor and chokepoint", detail: "Entity resolution and DPS are recalculated" },
  { agent: "ECON", label: "Stress-testing import exposure", detail: "Monte Carlo estimates supply and Brent impact" },
  { agent: "PROCURE", label: "Solving resilient procurement portfolios", detail: "OR-Tools compares cost, resilience, and inaction" },
  { agent: "HUMAN", label: "Preparing decision brief and approval", detail: "Gemini explains deterministic outputs for review" },
];

function number(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

export default function Home() {
  const [run, setRun] = useState<ScenarioRun | null>(null);
  const [summary, setSummary] = useState<NetworkSummary | null>(null);
  const [refineries, setRefineries] = useState<Refinery[]>([]);
  const [selectedRefinery, setSelectedRefinery] = useState("Jamnagar");
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [signalText, setSignalText] = useState(DEMO_SIGNAL);
  const [signalResult, setSignalResult] = useState<SignalResult | null>(null);
  const [processedSignal, setProcessedSignal] = useState<ProcessedSignal | null>(null);
  const [signalHistory, setSignalHistory] = useState<ProcessedSignal[]>([]);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [closureSeverity, setClosureSeverity] = useState(0.6);
  const [durationDays, setDurationDays] = useState(21);
  const [routeCapacity, setRouteCapacity] = useState(0.72);
  const [portfolioComparison, setPortfolioComparison] = useState<PortfolioComparison | null>(null);
  const [portfolioBrief, setPortfolioBrief] = useState<ExplanationResult | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResult | null>(null);
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([]);
  const [approvalDecision, setApprovalDecision] = useState<"APPROVED" | "REJECTED" | "DEFERRED">("APPROVED");
  const [approvalJustification, setApprovalJustification] = useState("Approve for commercial validation; no purchase order will be created by PetraVigil.");
  const [submittingApproval, setSubmittingApproval] = useState(false);
  const [replayRunning, setReplayRunning] = useState(false);
  const [replayStep, setReplayStep] = useState(-1);
  const [replaySeconds, setReplaySeconds] = useState(0);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [processingSignal, setProcessingSignal] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [generatingPortfolios, setGeneratingPortfolios] = useState(false);
  const [briefingPortfolio, setBriefingPortfolio] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveSignalIndex, setLiveSignalIndex] = useState(0);
  const [lastSync, setLastSync] = useState<Date | null>(null);

  useEffect(() => {
    async function loadWorkspace() {
      try {
        const storedRunId = window.localStorage.getItem(RUN_STORAGE_KEY);
        const [loadedSummary, loadedRefineries, loadedRun, loadedSignals, loadedApprovals] = await Promise.all([
          getNetworkSummary(),
          getRefineries(),
          storedRunId ? getScenarioRun(storedRunId) : getLatestScenarioRun(),
          getSignalHistory(),
          getApprovals(),
        ]);
        setSummary(loadedSummary);
        setRefineries(loadedRefineries);
        setRun(loadedRun);
        setSignalHistory(loadedSignals);
        setApprovals(loadedApprovals);
        window.localStorage.setItem(RUN_STORAGE_KEY, loadedRun.run_id);
        setLastSync(new Date());
      } catch {
        try {
          const [loadedSummary, loadedRefineries] = await Promise.all([getNetworkSummary(), getRefineries()]);
          setSummary(loadedSummary);
          setRefineries(loadedRefineries);
        } catch {
          setError("Unable to reach the PetraVigil API.");
        }
      } finally {
        setLoading(false);
      }
    }
    void loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedRefinery) return;
    void getAlternatives(selectedRefinery).then(setAlternatives).catch(() => setAlternatives([]));
  }, [selectedRefinery]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setLiveSignalIndex((current) => (current + 1) % LIVE_SIGNALS.length);
      setLastSync(new Date());
    }, 4200);
    return () => window.clearInterval(interval);
  }, []);

  async function handleRun(): Promise<void> {
    setRunning(true);
    setError(null);
    try {
      const created = await runCanonicalScenario();
      setRun(created);
      window.localStorage.setItem(RUN_STORAGE_KEY, created.run_id);
      setLastSync(new Date());
      void explainRecommendation().then(setExplanation).catch(() => undefined);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to run the scenario.");
    } finally {
      setRunning(false);
    }
  }

  async function handleAnalyze(): Promise<void> {
    setAnalyzing(true);
    try {
      setSignalResult(await extractSignal(signalText));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to analyse the signal.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleProcessSignal(): Promise<void> {
    setProcessingSignal(true);
    setError(null);
    try {
      const processed = await processSignal(signalText);
      setProcessedSignal(processed);
      setSignalResult(processed.gemini);
      setSignalHistory((current) => [processed, ...current.filter((item) => item.signal_id !== processed.signal_id)].slice(0, 6));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to validate and score the signal.");
    } finally {
      setProcessingSignal(false);
    }
  }

  async function handleExplain(): Promise<void> {
    setExplaining(true);
    try {
      setExplanation(await explainRecommendation());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to generate an explanation.");
    } finally {
      setExplaining(false);
    }
  }

  async function handleSimulate(): Promise<void> {
    setSimulating(true);
    setError(null);
    try {
      setSimulation(await runSimulation({ closure_severity: closureSeverity, disruption_duration_days: durationDays, alternative_route_capacity_ratio: routeCapacity, n_runs: 1000, random_seed: 20260720 }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to run the simulation.");
    } finally {
      setSimulating(false);
    }
  }

  async function handleGeneratePortfolios(): Promise<void> {
    setGeneratingPortfolios(true);
    setError(null);
    try {
      setPortfolioComparison(await generatePortfolios(routeCapacity));
      setPortfolioBrief(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to generate portfolios.");
    } finally {
      setGeneratingPortfolios(false);
    }
  }

  async function handlePortfolioBrief(label: "DO_NOTHING" | "LOWEST_COST" | "BALANCED" | "MAX_RESILIENCE"): Promise<void> {
    setBriefingPortfolio(label);
    try {
      setPortfolioBrief(await briefPortfolio(label));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to prepare the portfolio briefing.");
    } finally {
      setBriefingPortfolio(null);
    }
  }

  async function handleApproval(): Promise<void> {
    setSubmittingApproval(true);
    setError(null);
    try {
      const approval = await createApproval({ decision: approvalDecision, decided_by: "Demo Procurement Lead", justification: approvalJustification });
      setApprovals((current) => [approval, ...current].slice(0, 6));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to record the approval.");
    } finally {
      setSubmittingApproval(false);
    }
  }

  async function handleCrisisReplay(): Promise<void> {
    setReplayRunning(true);
    setReplayStep(0);
    setReplaySeconds(0);
    setError(null);
    const startedAt = Date.now();
    const timer = window.setInterval(() => setReplaySeconds((Date.now() - startedAt) / 1000), 100);
    const pause = () => new Promise<void>((resolve) => window.setTimeout(resolve, 520));
    try {
      const processed = await processSignal(DEMO_SIGNAL);
      setProcessedSignal(processed);
      setSignalResult(processed.gemini);
      setSignalHistory((current) => [processed, ...current.filter((item) => item.signal_id !== processed.signal_id)].slice(0, 6));
      setReplayStep(1);
      await pause();
      const simulated = await runSimulation({ closure_severity: closureSeverity, disruption_duration_days: durationDays, alternative_route_capacity_ratio: routeCapacity, n_runs: 1000, random_seed: 20260720 });
      setSimulation(simulated);
      setReplayStep(2);
      await pause();
      const portfolios = await generatePortfolios(routeCapacity);
      setPortfolioComparison(portfolios);
      setReplayStep(3);
      await pause();
      setExplanation(await explainRecommendation());
      setReplayStep(4);
      setLastSync(new Date());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to complete the crisis replay.");
    } finally {
      window.clearInterval(timer);
      setReplaySeconds((Date.now() - startedAt) / 1000);
      setReplayRunning(false);
    }
  }

  const scenario = run?.scenario;
  const recommendation = scenario?.recommendations[0];
  const liveSignal = useMemo(() => LIVE_SIGNALS[liveSignalIndex], [liveSignalIndex]);

  return (
    <main className="workspace">
      <div className="ambient-grid" aria-hidden="true" />
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">PV</span>
          <div>
            <p className="eyebrow">DECISION INTELLIGENCE</p>
            <h1>PetraVigil</h1>
            <p className="subtitle">Evidence-first energy supply resilience</p>
          </div>
        </div>
        <div className="topbar-status"><span className="status"><span /> Live decision workspace</span><small>{lastSync ? `Synced ${lastSync.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Connecting"}</small></div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">CANONICAL SHOWCASE FLOW</p>
          <h2>Detect, test, and explain a resilient procurement route.</h2>
          <p>Seeded network data powers feasibility. Gemini enriches unstructured inputs without becoming a source of truth.</p>
        </div>
        <div className="hero-actions"><button onClick={handleRun} disabled={running}>{running ? "Running scenario..." : "Run Hormuz scenario"}</button><div className="radar" aria-label="Live monitoring radar"><span /><i /><b /></div></div>
      </section>

      <section className="live-ticker" aria-live="polite"><span className="ticker-dot" /><span className="label">LIVE INTELLIGENCE</span><strong key={liveSignal}>{liveSignal}</strong><span className="ticker-tail">streaming</span></section>

      <section className="crisis-replay panel" aria-live="polite">
        <div className="section-heading"><div><p className="label">JUDGE MODE · CRISIS REPLAY</p><h3>From raw signal to decision-ready in one visible flow</h3></div><div className="replay-timer"><strong>{replaySeconds.toFixed(1)}s</strong><span>{replayRunning ? "signal to decision" : "ready to replay"}</span></div></div>
        <p className="muted">Runs the real local Gemini extraction/fallback, deterministic DPS, Monte Carlo engine, OR-Tools portfolios, and executive brief. No procurement action is executed.</p>
        <button className="secondary-button accent-button replay-button" onClick={handleCrisisReplay} disabled={replayRunning}>{replayRunning ? "Running live replay..." : "Start 30-second crisis replay"}</button>
        <div className="agent-trace">{REPLAY_STEPS.map((step, index) => <div className={`trace-step ${index < replayStep ? "complete" : index === replayStep ? "active" : ""}`} key={step.agent}><span>{index < replayStep ? "✓" : index + 1}</span><div><strong>{step.agent}</strong><p>{step.label}</p><small>{step.detail}</small></div></div>)}</div>
      </section>

      {error && <p className="error">{error}. Start the API on port 8000 and try again.</p>}
      {loading && <section className="loading-shell" aria-label="Loading decision workspace"><div className="skeleton skeleton-title" /><div className="skeleton-grid"><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /><div className="skeleton skeleton-card" /></div></section>}

      {summary && <section className="network-strip" aria-label="Seeded network coverage">
        <span><strong>{summary.countries}</strong> supply countries</span><span><strong>{summary.crude_grades}</strong> crude grades</span><span><strong>{summary.refineries}</strong> refineries</span><span><strong>{summary.routes}</strong> routes</span><span className="badge">{summary.data_status}</span>
      </section>}

      {scenario && recommendation && (
        <section className="results" aria-live="polite">
          <div className="run-meta"><span className="badge">{scenario.status}</span><span>{scenario.scenario_name}</span><span>Run {run?.run_id.slice(0, 12)}</span></div>
          <div className="grid">
            <article className="panel signal-panel"><p className="label">Signal</p><h3>Hormuz escalation</h3><p>{scenario.risk_event.summary}</p><div className="metrics"><span>Severity <strong>{scenario.risk_event.severity}/10</strong></span><span>Confidence <strong>{Math.round(scenario.risk_event.confidence * 100)}%</strong></span></div></article>
            <article className="panel"><p className="label">Corridor disruption probability</p><h3>{scenario.risk_score.corridor_id}</h3><p className="score">{Math.round(scenario.risk_score.score * 100)}<small>/100</small></p><p className="muted">Traceable to the simulated evidence chain.</p></article>
            <article className="panel"><p className="label">P50 import-cost exposure</p><p className="score">${number(scenario.expected_outcomes.additional_import_cost_p50_usd_per_day / 1_000_000)}M</p><p className="muted">per day · supply impact {number(scenario.expected_outcomes.supply_impact_p50_bpd)} bpd</p></article>
          </div>
          <article className="action-card"><div><p className="label">Recommended action · Rank 1</p><h3>Increase {recommendation.crude_grade} from {recommendation.supplier_country}</h3><p>{number(recommendation.volume_bpd)} bpd to {recommendation.refinery} via {recommendation.route}.</p></div><div className="action-stats"><span>Route risk <strong>{Math.round(recommendation.route_risk_score * 100)}/100</strong></span><span className="badge">Feasibility checks passed</span></div></article>
        </section>
      )}

      <section className="scenario-lab panel">
        <div className="section-heading"><div><p className="label">SCENARIO LAB · REAL MONTE CARLO</p><h3>Stress-test the Hormuz disruption before taking action</h3></div><span className="badge">1,000 reproducible runs</span></div>
        <div className="scenario-controls"><label>Closure severity <strong>{Math.round(closureSeverity * 100)}%</strong><input aria-label="Closure severity" type="range" min="0.2" max="1" step="0.05" value={closureSeverity} onChange={(event) => setClosureSeverity(Number(event.target.value))} /></label><label>Disruption duration <strong>{durationDays} days</strong><input aria-label="Disruption duration" type="range" min="5" max="60" step="1" value={durationDays} onChange={(event) => setDurationDays(Number(event.target.value))} /></label><label>Alternative-route capacity <strong>{Math.round(routeCapacity * 100)}%</strong><input aria-label="Alternative route capacity" type="range" min="0.3" max="1" step="0.05" value={routeCapacity} onChange={(event) => setRouteCapacity(Number(event.target.value))} /></label><button className="secondary-button accent-button" onClick={handleSimulate} disabled={simulating}>{simulating ? "Running 1,000 simulations..." : "Run Scenario Lab"}</button></div>
        {simulation && <div className="simulation-output"><div className="grid"><article className="metric-box"><p className="label">P50 supply impact</p><strong>{number(simulation.supply_impact_bpd.p50)} bpd</strong><span>P10–P90: {number(simulation.supply_impact_bpd.p10)}–{number(simulation.supply_impact_bpd.p90)}</span></article><article className="metric-box"><p className="label">P50 Brent premium</p><strong>${simulation.brent_premium_usd_per_bbl.p50}/bbl</strong><span>P10–P90: ${simulation.brent_premium_usd_per_bbl.p10}–${simulation.brent_premium_usd_per_bbl.p90}</span></article><article className="metric-box"><p className="label">Act-now value</p><strong>${number(simulation.act_now_avoided_cost_usd / 1_000_000)}M</strong><span>Estimated avoided exposure window</span></article></div><div className="fan-chart"><p className="label">BRENT PREMIUM UNCERTAINTY BAND</p><div className="fan-bars">{simulation.series.filter((_, index) => index % Math.ceil(simulation.series.length / 12) === 0).map((point) => <div className="fan-column" key={point.day}><div className="fan-range" style={{ height: `${Math.min(100, point.brent_premium.p90 * 5)}%`, bottom: `${Math.min(80, point.brent_premium.p10 * 5)}%` }} /><span>{point.day}</span></div>)}</div><p className="muted">Band shows P10–P90 projected Brent premium by day. Inputs and random seed are stored with the result.</p></div></div>}
      </section>

      <section className="portfolio-studio panel">
        <div className="section-heading"><div><p className="label">ADAPTIVE PROCUREMENT ORCHESTRATOR</p><h3>Compare cost, resilience, and doing nothing</h3></div><span className="badge">OR-Tools constrained optimiser</span></div>
        <p className="muted">Every allocation respects the seeded refinery-compatible grades and alternative-route capacity. It remains a local decision recommendation—never a purchase order.</p>
        <button className="secondary-button accent-button" onClick={handleGeneratePortfolios} disabled={generatingPortfolios}>{generatingPortfolios ? "Solving portfolio constraints..." : "Generate four portfolios"}</button>
        {portfolioComparison && <div className="portfolio-grid">{portfolioComparison.portfolios.map((portfolio) => <article className={`portfolio-card ${portfolio.label.toLowerCase()}`} key={portfolio.portfolio_id}><p className="label">{portfolio.label.replaceAll("_", " ")}</p><strong>{portfolio.total_volume_bpd ? `${number(portfolio.total_volume_bpd)} bpd` : "Exposed"}</strong><span>{portfolio.total_volume_bpd ? `$${number(portfolio.total_daily_cost_usd / 1_000_000)}M/day` : "No proactive cost"}</span><span>Route risk {Math.round(portfolio.weighted_route_risk * 100)}/100</span><p>{portfolio.rationale}</p>{portfolio.allocations.map((allocation) => <small key={`${allocation.crude_grade}-${allocation.route}`}>{allocation.crude_grade}: {number(allocation.volume_bpd)} bpd</small>)}<button className="brief-button" onClick={() => handlePortfolioBrief(portfolio.label)} disabled={briefingPortfolio === portfolio.label}>{briefingPortfolio === portfolio.label ? "Briefing..." : "Ask Gemini to brief"}</button></article>)}</div>}
        {portfolioBrief && <div className="ai-result"><div className="result-meta"><span className="badge">{portfolioBrief.provider_status}</span><span>{portfolioBrief.model}</span></div><p>{portfolioBrief.explanation}</p><p className="next-question">Next: {portfolioBrief.next_question}</p></div>}
      </section>

      <section className="intelligence-grid">
        <article className="panel intelligence-panel">
          <div className="section-heading"><div><p className="label">GEMINI SIGNAL MESH</p><h3>Turn a messy alert into a structured proposal</h3></div><span className="badge">Gemini + fallback</span></div>
          <textarea value={signalText} onChange={(event) => setSignalText(event.target.value)} aria-label="Signal input" />
          <div className="button-row"><button className="secondary-button" onClick={handleAnalyze} disabled={analyzing || signalText.trim().length < 20}>{analyzing ? "Extracting..." : "Preview with Gemini"}</button><button className="secondary-button accent-button" onClick={handleProcessSignal} disabled={processingSignal || signalText.trim().length < 20}>{processingSignal ? "Validating and scoring..." : "Validate + score signal"}</button></div>
          {signalResult && <div className="ai-result"><div className="result-meta"><span className="badge">{signalResult.provider_status}</span><span>{signalResult.model}</span></div><p><strong>{signalResult.proposal.event_type}</strong> · severity {signalResult.proposal.severity}/10 · confidence {Math.round(signalResult.proposal.confidence * 100)}%</p><p>{signalResult.proposal.summary}</p><p className="muted">{signalResult.proposal.evidence_note}</p><p className="disclaimer">{signalResult.disclaimer}</p></div>}
        </article>

        <article className="panel intelligence-panel">
          <div className="section-heading"><div><p className="label">REFINERY / ROUTE EXPLORER</p><h3>Find compatible routes that avoid Hormuz</h3></div><span className="badge">Historical seed</span></div>
          <label className="select-label">Refinery<select value={selectedRefinery} onChange={(event) => setSelectedRefinery(event.target.value)}>{refineries.map((refinery) => <option key={refinery.name} value={refinery.name}>{refinery.name} · {refinery.operator}</option>)}</select></label>
          <div className="alternatives">{alternatives.map((option) => <div className="alternative" key={option.option_id}><div><strong>{option.crude_grade}</strong><span>{option.supplier_country} · {option.route}</span></div><div><strong>{option.transit_days} days</strong><span>risk {Math.round(option.route_risk_score * 100)}/100</span></div><p>{option.compatibility_note}</p></div>)}</div>
        </article>
      </section>

      <section className="signal-audit panel" aria-live="polite">
        <div className="section-heading"><div><p className="label">SIGNAL MESH AUDIT TRAIL</p><h3>From unverified text to transparent corridor risk</h3></div>{processedSignal && <span className="badge">{processedSignal.review_required ? "Analyst review required" : "Resolved"}</span>}</div>
        {processedSignal ? <div className="audit-grid"><div><p className="label">1 · ENTITY RESOLUTION</p>{processedSignal.entity_resolutions.map((resolution) => <p className="audit-row" key={`${resolution.entity_type}-${resolution.entity}`}><strong>{resolution.entity}</strong><span className={resolution.resolved ? "resolved" : "unresolved"}>{resolution.resolved ? `Matched: ${resolution.canonical_name}` : "Unresolved"}</span></p>)}</div><div><p className="label">2 · DISRUPTION PROBABILITY SCORE</p>{processedSignal.risk_scores.map((risk) => <div className="risk-card" key={risk.corridor_id}><strong>{risk.corridor_id}</strong><span>{Math.round(risk.score * 100)}/100</span><small>Geo {Math.round(risk.components.geopolitical * 100)} · Chokepoint {Math.round(risk.components.chokepoint_concentration * 100)} · Maritime {Math.round(risk.components.maritime_anomaly * 100)}</small></div>)}</div></div> : <p className="muted">Validate a signal to persist its source text, Gemini proposal, entity matches, review state, and deterministic DPS components.</p>}
        {signalHistory.length > 0 && <div className="history"><p className="label">RECENT SIGNALS</p>{signalHistory.slice(0, 3).map((signal) => <div key={signal.signal_id} className="history-row"><span className="badge">{signal.source_status}</span><strong>{signal.gemini.proposal.event_type}</strong><span>{signal.risk_scores[0] ? `${signal.risk_scores[0].corridor_id}: ${Math.round(signal.risk_scores[0].score * 100)}/100` : "No corridor score"}</span></div>)}</div>}
      </section>

      {recommendation && <section className="explanation-panel panel">
        <div><p className="label">GEMINI DECISION BRIEF</p><h3>Explain the recommendation in executive language</h3><p className="muted">The model may explain deterministic outputs, but it does not calculate prices, capacity, sanctions, or procurement decisions.</p></div>
        <button className="secondary-button" onClick={handleExplain} disabled={explaining}>{explaining ? "Preparing brief..." : "Explain this action"}</button>
        {explanation && <div className="ai-result"><div className="result-meta"><span className="badge">{explanation.provider_status}</span><span>{explanation.model}</span></div><p>{explanation.explanation}</p><ul>{explanation.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul><p className="next-question">Next: {explanation.next_question}</p></div>}
      </section>}

      {recommendation && <section className="approval-panel panel" aria-live="polite">
        <div className="section-heading"><div><p className="label">HUMAN-IN-THE-LOOP APPROVAL</p><h3>Log a decision, not a purchase order</h3></div><span className="badge">Local only</span></div>
        <p className="muted">This creates an append-only audit record for {recommendation.recommendation_id}. PetraVigil cannot contact suppliers or execute procurement.</p>
        <div className="approval-controls"><label>Decision<select aria-label="Approval decision" value={approvalDecision} onChange={(event) => setApprovalDecision(event.target.value as "APPROVED" | "REJECTED" | "DEFERRED")}><option value="APPROVED">Approve for validation</option><option value="DEFERRED">Defer pending evidence</option><option value="REJECTED">Reject recommendation</option></select></label><label>Human justification<textarea aria-label="Approval justification" value={approvalJustification} onChange={(event) => setApprovalJustification(event.target.value)} /></label><button className="secondary-button accent-button" onClick={handleApproval} disabled={submittingApproval || approvalJustification.trim().length < 10}>{submittingApproval ? "Recording decision..." : "Record human decision"}</button></div>
        {approvals.length > 0 && <div className="approval-history"><p className="label">RECENT DECISIONS</p>{approvals.slice(0, 3).map((approval) => <div className="history-row" key={approval.approval_id}><span className={`approval-status ${approval.decision.toLowerCase()}`}>{approval.decision}</span><strong>{approval.decided_by}</strong><span>{new Date(approval.decided_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div>)}</div>}
      </section>}
    </main>
  );
}

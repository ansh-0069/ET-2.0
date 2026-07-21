export type ScenarioRun = {
  run_id: string;
  status: "COMPLETED";
  created_at: string;
  scenario: {
    scenario_name: string;
    status: string;
    risk_event: { summary: string; severity: number; confidence: number };
    risk_score: { corridor_id: string; score: number };
    expected_outcomes: Record<string, number>;
    recommendations: Array<{
      recommendation_id: string;
      supplier_country: string | null;
      crude_grade: string | null;
      refinery: string | null;
      volume_bpd: number;
      route: string | null;
      route_risk_score: number;
      rationale: string;
    }>;
  };
};

export type NetworkSummary = { countries: number; crude_grades: number; refineries: number; routes: number; chokepoints: number; data_status: string };
export type Refinery = { name: string; operator: string; capacity_mmtpa: number; complexity_index: number; compatible_grades: string[] };
export type Alternative = { option_id: string; supplier_country: string; crude_grade: string; refinery: string; route: string; avoids_chokepoint: string; transit_days: number; route_risk_score: number; available_volume_bpd: number; compatibility_note: string; data_status: string };
export type SignalResult = { provider_status: string; model: string; proposal: { energy_relevant: boolean; event_type: string; severity: number; confidence: number; affected_countries: string[]; affected_chokepoints: string[]; time_horizon: string; summary: string; evidence_note: string }; disclaimer: string };
export type ExplanationResult = { provider_status: string; model: string; explanation: string; risks: string[]; next_question: string };
export type ProcessedSignal = { signal_id: string; created_at: string; source_status: string; raw_text: string; gemini: SignalResult; entity_resolutions: Array<{ entity: string; entity_type: string; resolved: boolean; canonical_name: string | null; note: string }>; risk_scores: Array<{ corridor_id: string; score: number; components: Record<string, number> }>; review_required: boolean };
export type Simulation = { simulation_id: string; data_status: string; assumptions: { closure_severity: number; disruption_duration_days: number; brent_elasticity_usd_per_mmbpd: number; alternative_route_capacity_ratio: number; n_runs: number; random_seed: number }; supply_impact_bpd: { p10: number; p50: number; p90: number }; brent_premium_usd_per_bbl: { p10: number; p50: number; p90: number }; additional_cost_usd_per_day: { p10: number; p50: number; p90: number }; spr_bridge_days: { p10: number; p50: number; p90: number }; act_now_avoided_cost_usd: number; series: Array<{ day: number; brent_premium: { p10: number; p50: number; p90: number } }> };
export type SprBridgeAllocation = { status: "NOT_REQUESTED" | "NOT_NEEDED" | "CONTINGENCY_ALLOCATED"; data_status: "Simulated"; capacity_source_status: "Simulated"; authorization_source_status: "User-entered"; seeded_capacity_bpd: number; seeded_max_bridge_days: number; bridge_volume_bpd: number; bridge_duration_days: number; bridge_volume_bbl: number; analyst_opt_in: boolean; government_authorization_assumed_for_scenario: boolean; requires_human_approval: true; requires_government_authorization: true; activation_conditions: string[]; limitations: string[] };
export type Portfolio = { portfolio_id: string; label: "DO_NOTHING" | "LOWEST_COST" | "BALANCED" | "MAX_RESILIENCE"; total_volume_bpd: number; total_daily_cost_usd: number; weighted_route_risk: number; expected_avoided_exposure_usd: number; allocations: Array<{ supplier_country: string; crude_grade: string; route: string; volume_bpd: number; cost_usd_per_bbl: number; route_risk_score: number }>; spr_bridge: SprBridgeAllocation; rationale: string };
export type PortfolioComparison = { comparison_id: string; request: { refinery: string; required_volume_bpd: number; alternative_route_capacity_ratio: number }; portfolios: Portfolio[] };
export type ApprovalRecord = { approval_id: string; recommendation_id: string; decision: "DRAFT" | "APPROVED" | "REJECTED" | "DEFERRED"; decided_by: string; decided_at: string; justification: string; execution_external: false };
export type AgentTraceEntry = { stage: "SIGNAL" | "INTELLIGENCE" | "RISK" | "ECONOMIC" | "PROCUREMENT" | "EXECUTIVE"; status: "COMPLETED" | "REQUIRES_REVIEW"; confidence: number; summary: string; rationale: string; unknowns: string[] };
export type WorkflowAssumptions = { closure_severity: number; disruption_duration_days: number; brent_elasticity_usd_per_mmbpd: number; alternative_route_capacity_ratio: number; n_runs: number; random_seed: number; confidence: number; rationale: string; unknowns: string[]; spr_bridge_opt_in: boolean; government_authorization_assumed_for_scenario: boolean; spr_bridge_duration_days: number };
export type RecommendationTransparency = { selected_portfolio: "LOWEST_COST" | "BALANCED" | "MAX_RESILIENCE"; confidence: number; evidence: string[]; assumptions: string[]; risk_factors: string[]; rejected_alternatives: string[]; unknowns: string[]; why_this_won: string; requires_human_approval: true };
export type WorkflowProposal = { workflow_id: string; status: "AWAITING_ANALYST_CONFIRMATION"; created_at: string; refinery: string; required_volume_bpd: number; processed_signal: ProcessedSignal; proposed_assumptions: WorkflowAssumptions; agent_trace: AgentTraceEntry[] };
export type DecisionSafetyGateSource = { label: string; kind: "EVIDENCE" | "CONSTRAINT" | "ASSUMPTION"; source_status: string; detail: string };
export type DecisionSafetyGateCheck = { check_id: "EXTRACTION_CONFIDENCE" | "CORRIDOR_RESOLUTION" | "SOURCE_PROVENANCE" | "SUPPLY_FEASIBILITY"; state: "PASS" | "WARNING" | "BLOCKER"; summary: string; sources: DecisionSafetyGateSource[]; next_actions: string[] };
export type DecisionSafetyGate = { status: "CLEARED" | "BLOCKED"; decision: "RECOMMENDATION_READY" | "NO_RECOMMENDATION_YET"; summary: string; checks: DecisionSafetyGateCheck[]; blockers: string[]; warnings: string[]; next_actions: string[] };
export type WorkflowExecution = { workflow_id: string; status: "COMPLETED" | "BLOCKED"; completed_at: string; analyst_name: string; processed_signal: ProcessedSignal; assumptions: WorkflowAssumptions; recommendation_id: string | null; simulation: Simulation | null; portfolios: PortfolioComparison | null; executive_brief: ExplanationResult | null; transparency: RecommendationTransparency | null; blocking_reason: string | null; decision_safety_gate?: DecisionSafetyGate | null; agent_trace: AgentTraceEntry[] };
export type ReplaySourceStatus = "Simulated" | "Historical" | "User-entered";
export type ReplayEvidenceEvent = { sequence: number; label: string; source_status: ReplaySourceStatus; reliability: number; summary: string; impact: string };
export type ReplayRoute = { route_id: string; name: string; coordinates: Array<[number, number]>; status: "EXPOSED" | "ALTERNATIVE"; source_status: ReplaySourceStatus; transit_days: number; available_volume_bpd: number; route_risk_score: number; note: string };
export type ReplayLocation = { location_id: string; name: string; kind: "CHOKEPOINT" | "ORIGIN" | "DESTINATION" | "WAYPOINT"; coordinates: [number, number]; source_status: ReplaySourceStatus };
export type CrisisReplay = { replay_id: string; title: string; disclaimer: string; chokepoint: string; replay_signal: string; evidence: ReplayEvidenceEvent[]; routes: ReplayRoute[]; locations: ReplayLocation[] };
export type DecisionClockSourceStatus = "Simulated" | "Seeded" | "User-entered";
export type DecisionClockMetric = { key: "base_decision_window_hours" | "stockout_threshold_hours" | "baseline_approval_delay_hours" | "laycan_cutoff_hours" | "protected_inventory_buffer_hours" | "usable_stock_cover_hours" | "decision_lead_time_hours" | "last_responsible_action_offset_hours" | "effective_approval_delay_hours"; label: string; value: number; unit: "hours"; source_status: DecisionClockSourceStatus; rationale: string };
export type DecisionClockStage = { sequence: number; offset_hours: number; label: string; source_status: DecisionClockSourceStatus; kind: "SIGNAL" | "ANALYST_REVIEW" | "LAST_RESPONSIBLE_ACTION" | "APPROVAL_COMPLETION" | "LAYCAN_CUTOFF" | "STOCKOUT_THRESHOLD"; action: string; detail: string };
export type DecisionClockAssumption = { assumption_id: string; label: string; value: string; source_status: DecisionClockSourceStatus; rationale: string };
export type DecisionClock = { clock_id: string; title: string; disclaimer: string; replay_id: string; base_decision_window_hours: number; stockout_threshold_hours: number; baseline_approval_delay_hours: number; laycan_cutoff_hours: number; protected_inventory_buffer_hours: number; usable_stock_cover_hours: number; decision_lead_time_hours: number; last_responsible_action_offset_hours: number; effective_approval_delay_hours: number; metrics: DecisionClockMetric[]; stages: DecisionClockStage[]; assumptions: DecisionClockAssumption[] };
export type MultiRefineryDemandLine = { refinery: string; required_volume_bpd: number };
export type MultiRefineryRequest = { scenario_label?: string; demand_lines: MultiRefineryDemandLine[]; alternative_route_capacity_ratio: number; disrupted_chokepoint: string; assumption_source_status?: "User-entered" };
export type MultiRefineryAllocation = { refinery: string; supplier_country: string; crude_grade: string; route: string; volume_bpd: number; cost_usd_per_bbl: number; route_risk_score: number; allocation_status: "Simulated"; route_capacity_source_status: "Historical" };
export type MultiRefineryResult = { refinery: string; requested_volume_bpd: number; allocated_volume_bpd: number; unserved_volume_bpd: number; fulfillment_status: string; demand_source_status: "User-entered"; compatible_route_count: number; allocations: MultiRefineryAllocation[]; note: string };
export type SharedRouteUtilization = { route: string; supplier_country: string; seed_capacity_bpd: number; alternative_route_capacity_ratio: number; effective_capacity_bpd: number; allocated_capacity_bpd: number; remaining_capacity_bpd: number; transit_days: number; route_risk_score: number; route_capacity_source_status: "Historical"; allocation_status: "Simulated" };
export type CargoContentionParticipant = { refinery: string; scenario_requested_volume_bpd: number; allocated_volume_bpd: number; demand_source_status: "User-entered" };
export type CargoContention = { route: string; competing_refineries: string[]; scenario_requested_capacity_bpd: number; effective_capacity_bpd: number; allocated_capacity_bpd: number; status: "CONTESTED" | "SHARED_WITH_HEADROOM"; participants: CargoContentionParticipant[]; route_capacity_source_status: "Historical"; allocation_status: "Simulated"; note: string };
export type MultiRefineryProvenance = { label: string; source_status: "User-entered" | "Historical" | "Simulated"; detail: string };
export type MultiRefineryAllocationResult = { allocation_id: string; created_at: string; status: "FEASIBLE" | "INFEASIBLE"; decision: "ALLOCATION_READY" | "NO_RECOMMENDATION_YET"; data_status: "Simulated"; network_source_status: "Historical"; demand_source_status: "User-entered"; live_data_connected: false; request: MultiRefineryRequest; refinery_results: MultiRefineryResult[]; shared_route_utilization: SharedRouteUtilization[]; cargo_contention: CargoContention[]; spr_bridge_status: "NOT_MODELED"; provenance: MultiRefineryProvenance[]; limitations: string[]; rationale: string; requires_human_approval: true; execution_external: false };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null) as { detail?: string | Array<{ msg?: string }> } | null;
    const detail = typeof payload?.detail === "string"
      ? payload.detail
      : Array.isArray(payload?.detail)
        ? payload.detail.map((item) => item.msg).filter(Boolean).join(" ")
        : null;
    throw new Error(detail || `API request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export const runCanonicalScenario = () => request<ScenarioRun>("/api/v1/scenario-runs/canonical", { method: "POST" });
export const getScenarioRun = (runId: string) => request<ScenarioRun>(`/api/v1/scenario-runs/${runId}`);
export const getLatestScenarioRun = () => request<ScenarioRun>("/api/v1/scenario-runs/latest");
export const getNetworkSummary = () => request<NetworkSummary>("/api/v1/network/summary");
export const getRefineries = () => request<Refinery[]>("/api/v1/network/refineries");
export const getAlternatives = (refinery: string) => request<Alternative[]>(`/api/v1/network/alternatives?refinery=${encodeURIComponent(refinery)}&disrupted_chokepoint=HORMUZ`);
export const extractSignal = (text: string) => request<SignalResult>("/api/v1/intelligence/extract", { method: "POST", body: JSON.stringify({ text }) });
export const explainRecommendation = () => request<ExplanationResult>("/api/v1/intelligence/explain", { method: "POST" });
export const processSignal = (text: string) => request<ProcessedSignal>("/api/v1/signals/process", { method: "POST", body: JSON.stringify({ text, source_status: "User-entered" }) });
export const getSignalHistory = () => request<ProcessedSignal[]>("/api/v1/signals?limit=6");
export const runSimulation = (assumptions: Partial<Simulation["assumptions"]>) => request<Simulation>("/api/v1/simulations", { method: "POST", body: JSON.stringify(assumptions) });
export const getLatestSimulation = () => request<Simulation>("/api/v1/simulations/latest");
export const generatePortfolios = (alternativeRouteCapacityRatio: number) => request<PortfolioComparison>("/api/v1/portfolios", { method: "POST", body: JSON.stringify({ refinery: "Jamnagar", required_volume_bpd: 210000, alternative_route_capacity_ratio: alternativeRouteCapacityRatio }) });
export const briefPortfolio = (label: Portfolio["label"]) => request<ExplanationResult>(`/api/v1/portfolios/${label}/brief`, { method: "POST" });
export const getApprovals = () => request<ApprovalRecord[]>("/api/v1/approvals?limit=6");
export const createApproval = (payload: Pick<ApprovalRecord, "decision" | "decided_by" | "justification">) => request<ApprovalRecord>("/api/v1/approvals/canonical", { method: "POST", body: JSON.stringify(payload) });
export const proposeWorkflow = (payload: { text: string; refinery: string; required_volume_bpd: number }) => request<WorkflowProposal>("/api/v1/workflows/propose", { method: "POST", body: JSON.stringify(payload) });
export const executeWorkflow = (workflowId: string, payload: { analyst_name: string; assumptions: WorkflowAssumptions }) => request<WorkflowExecution>(`/api/v1/workflows/${workflowId}/execute`, { method: "POST", body: JSON.stringify({ ...payload, analyst_confirmed: true }) });
export const approveWorkflow = (workflowId: string, payload: Pick<ApprovalRecord, "decision" | "decided_by" | "justification">) => request<ApprovalRecord>(`/api/v1/workflows/${workflowId}/approval`, { method: "POST", body: JSON.stringify(payload) });
export const getHormuzReplay = () => request<CrisisReplay>("/api/v1/replays/hormuz");
export const getHormuzDecisionClock = (approvalDelayHours?: number) => request<DecisionClock>(`/api/v1/decision-clock/hormuz${approvalDelayHours === undefined ? "" : `?approval_delay_hours=${approvalDelayHours}`}`);
export const runMultiRefineryAllocation = (payload: Partial<MultiRefineryRequest> = {}) => request<MultiRefineryAllocationResult>("/api/v1/portfolios/multi-refinery", { method: "POST", body: JSON.stringify(payload) });

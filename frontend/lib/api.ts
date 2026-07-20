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
export type Portfolio = { portfolio_id: string; label: "DO_NOTHING" | "LOWEST_COST" | "BALANCED" | "MAX_RESILIENCE"; total_volume_bpd: number; total_daily_cost_usd: number; weighted_route_risk: number; expected_avoided_exposure_usd: number; allocations: Array<{ supplier_country: string; crude_grade: string; route: string; volume_bpd: number; cost_usd_per_bbl: number; route_risk_score: number }>; rationale: string };
export type PortfolioComparison = { comparison_id: string; request: { refinery: string; required_volume_bpd: number; alternative_route_capacity_ratio: number }; portfolios: Portfolio[] };
export type ApprovalRecord = { approval_id: string; recommendation_id: string; decision: "DRAFT" | "APPROVED" | "REJECTED" | "DEFERRED"; decided_by: string; decided_at: string; justification: string; execution_external: false };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });

  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`);
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

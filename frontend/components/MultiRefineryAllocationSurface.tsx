"use client";

import { useEffect, useState } from "react";

import type { MultiRefineryAllocationResult, MultiRefineryDemandLine, MultiRefineryRequest } from "../lib/api";

const DEFAULT_DEMANDS: MultiRefineryDemandLine[] = [
  { refinery: "Jamnagar", required_volume_bpd: 120_000 },
  { refinery: "Paradip", required_volume_bpd: 50_000 },
  { refinery: "Kochi", required_volume_bpd: 80_000 },
];

function number(value: number): string {
  return new Intl.NumberFormat("en-IN").format(Math.round(value));
}

type MultiRefineryAllocationSurfaceProps = {
  result: MultiRefineryAllocationResult | null;
  resultOrigin?: "canonical" | "sensitivity";
  loading: boolean;
  onRun: (payload: MultiRefineryRequest) => void;
};

export default function MultiRefineryAllocationSurface({ result, resultOrigin = "sensitivity", loading, onRun }: MultiRefineryAllocationSurfaceProps) {
  const [demandLines, setDemandLines] = useState<MultiRefineryDemandLine[]>(DEFAULT_DEMANDS);
  const [capacityRatio, setCapacityRatio] = useState(0.72);

  useEffect(() => {
    if (result) {
      setDemandLines(result.request.demand_lines);
      setCapacityRatio(result.request.alternative_route_capacity_ratio);
    }
  }, [result]);

  function updateDemand(refinery: string, requiredVolume: number): void {
    setDemandLines((current) => current.map((line) => line.refinery === refinery ? { ...line, required_volume_bpd: requiredVolume } : line));
  }

  const totalDemand = demandLines.reduce((total, line) => total + (Number.isFinite(line.required_volume_bpd) ? line.required_volume_bpd : 0), 0);

  return (
    <section className="context-surface multi-refinery-surface" aria-labelledby="multi-refinery-title">
      <div className="section-heading"><div><p className="label">NATIONAL IMPACT · SHARED CARGO CONSTRAINT</p><h3 id="multi-refinery-title">Allocate finite alternatives across linked refineries</h3><p>Each route capacity is scaled once and shared across all compatible refineries. The output is a local, source-labelled allocation drill, not a market offer, tanker booking, or reserve activation.</p></div><span className="badge">No duplicate cargo capacity</span></div>

      {resultOrigin === "canonical" && result && <p className="canonical-allocation-note">This result was generated inside the confirmed workflow. Any rerun below is a separate sensitivity, not a replacement for the recorded case.</p>}

      <div className="multi-refinery-controls">
        <div className="multi-demand-grid">{demandLines.map((line) => <label key={line.refinery}>{line.refinery}<input type="number" min="0" max="500000" step="5000" value={line.required_volume_bpd} onChange={(event) => updateDemand(line.refinery, Number(event.target.value))} /><small>bpd demand</small></label>)}</div>
        <label className="multi-capacity-control">Shared alternative capacity <strong>{Math.round(capacityRatio * 100)}%</strong><input type="range" min="0.3" max="1" step="0.02" value={capacityRatio} onChange={(event) => setCapacityRatio(Number(event.target.value))} /><small>Applied once to each seeded physical route.</small></label>
        <div className="multi-action-row"><span>Total requested: <strong>{number(totalDemand)} bpd</strong></span><button type="button" className="secondary-button" disabled={loading || demandLines.some((line) => !Number.isFinite(line.required_volume_bpd) || line.required_volume_bpd < 0)} onClick={() => onRun({ demand_lines: demandLines, alternative_route_capacity_ratio: capacityRatio, disrupted_chokepoint: "HORMUZ" })}>{loading ? "Allocating shared cargo..." : resultOrigin === "canonical" ? "Run separate what-if" : "Run shared-cargo allocation"}</button></div>
      </div>

      {result && <>
        <div className={`multi-result-summary is-${result.status.toLowerCase()}`}><div><span>Network outcome</span><strong>{result.status === "FEASIBLE" ? "Feasible shared allocation" : "No feasible shared allocation"}</strong></div><div><span>SPR treatment</span><strong>{result.spr_bridge_status.replaceAll("_", " ")}</strong></div><div><span>Provenance</span><strong>{result.network_source_status} network · {result.data_status} allocation</strong></div></div>

        <div className="multi-refinery-results" aria-label="Refinery-level allocation results">{result.refinery_results.map((refinery) => <article key={refinery.refinery}><div><p className="label">{refinery.refinery}</p><strong>{number(refinery.allocated_volume_bpd)} / {number(refinery.requested_volume_bpd)} bpd</strong><span className={`fulfillment-status is-${refinery.fulfillment_status.toLowerCase()}`}>{refinery.fulfillment_status.replaceAll("_", " ")}</span></div><p>{refinery.unserved_volume_bpd ? `${number(refinery.unserved_volume_bpd)} bpd remains unserved under the shared route constraints.` : "All requested demand is covered within the seeded shared-route constraints."}</p>{refinery.allocations.map((allocation) => <small key={`${allocation.crude_grade}-${allocation.route}`}>{allocation.crude_grade} · {number(allocation.volume_bpd)} bpd via {allocation.route}</small>)}</article>)}</div>

        <div className="shared-route-ledger"><div className="ledger-heading"><div><p className="label">SHARED ROUTE UTILIZATION</p><p>Capacity is not multiplied per refinery.</p></div><span className="source-chip is-historical">Historical seeded network</span></div>{result.shared_route_utilization.map((route) => { const utilization = route.effective_capacity_bpd ? Math.min(100, (route.allocated_capacity_bpd / route.effective_capacity_bpd) * 100) : 0; return <article key={route.route}><div><strong>{route.route}</strong><span>{number(route.allocated_capacity_bpd)} / {number(route.effective_capacity_bpd)} bpd allocated</span></div><div className="route-utilization" aria-label={`${route.route}: ${Math.round(utilization)} percent of seeded capacity allocated`}><i style={{ width: `${utilization}%` }} /></div><small>{number(route.remaining_capacity_bpd)} bpd remaining · {route.route_capacity_source_status}</small></article>; })}</div>

        <div className="cargo-contention-list"><div className="ledger-heading"><div><p className="label">CARGO CONTENTION</p><p>Shared lanes with more than one compatible refinery.</p></div></div>{result.cargo_contention.map((contention) => <article className={`is-${contention.status.toLowerCase()}`} key={contention.route}><strong>{contention.route}</strong><span>{contention.competing_refineries.join(" · ")}</span><p>Scenario demand {number(contention.scenario_requested_capacity_bpd)} bpd against {number(contention.effective_capacity_bpd)} bpd effective capacity; {number(contention.allocated_capacity_bpd)} bpd was allocated.</p><small>{contention.status.replaceAll("_", " ")} · participants: {contention.participants.map((participant) => `${participant.refinery} ${number(participant.allocated_volume_bpd)} bpd`).join(", ")}</small></article>)}</div>

        <ul className="multi-limitations">{result.limitations.map((limitation) => <li key={limitation}>{limitation}</li>)}</ul>
      </>}
    </section>
  );
}

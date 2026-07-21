"use client";

import type { DecisionClock, DecisionClockStage } from "../lib/api";

function sourceClass(value: string): string {
  return value.toLowerCase().replaceAll(" ", "-");
}

function stage(clock: DecisionClock, kind: DecisionClockStage["kind"]): DecisionClockStage | undefined {
  return clock.stages.find((item) => item.kind === kind);
}

type DecisionClockSurfaceProps = {
  clock: DecisionClock;
  loading: boolean;
  onApprovalDelayChange: (hours: number) => void;
};

export default function DecisionClockSurface({ clock, loading, onApprovalDelayChange }: DecisionClockSurfaceProps) {
  const lastAction = stage(clock, "LAST_RESPONSIBLE_ACTION");
  const laycanCutoff = stage(clock, "LAYCAN_CUTOFF");
  const stockout = stage(clock, "STOCKOUT_THRESHOLD");
  const timelineSpan = Math.max(clock.stockout_threshold_hours, clock.laycan_cutoff_hours, 1);
  const lastActionPosition = Math.min(100, (clock.last_responsible_action_offset_hours / timelineSpan) * 100);
  const laycanPosition = Math.min(100, (clock.laycan_cutoff_hours / timelineSpan) * 100);

  return (
    <section className="context-surface decision-clock" aria-labelledby="decision-clock-title">
      <div className="section-heading decision-clock-heading">
        <div>
          <p className="label">DECISION CLOCK · LEAD-TIME REPLAY</p>
          <h3 id="decision-clock-title">{clock.title}</h3>
          <p>{clock.disclaimer}</p>
        </div>
        <span className="badge">Replay T+0 · no live deadline</span>
      </div>

      <div className="decision-clock-summary" aria-label="Decision deadline summary">
        <article><span>Last responsible action</span><strong>T+{clock.decision_lead_time_hours}h</strong><small>{lastAction?.action}</small></article>
        <article><span>Laycan cutoff</span><strong>T+{clock.laycan_cutoff_hours}h</strong><small>{laycanCutoff?.detail}</small></article>
        <article><span>Scenario buffer breach</span><strong>T+{clock.stockout_threshold_hours}h</strong><small>{stockout?.detail}</small></article>
      </div>

      <div className="clock-control-row">
        <label>
          Assumed approval delay
          <select value={clock.effective_approval_delay_hours} onChange={(event) => onApprovalDelayChange(Number(event.target.value))} disabled={loading} aria-describedby="clock-delay-note">
            {[0, 12, 24, 36, 48, 72].map((hours) => <option key={hours} value={hours}>{hours} hours</option>)}
          </select>
        </label>
        <p id="clock-delay-note">Changes only the source-labelled local timing sensitivity. It does not create or submit a procurement action.</p>
      </div>

      <div className="clock-band-wrap" role="img" aria-label={`Decision clock from replay signal at T plus zero to seeded stockout threshold at T plus ${clock.stockout_threshold_hours} hours`}>
        <div className="clock-axis"><span>T+0</span><span>T+{Math.round(timelineSpan / 2)}h</span><span>T+{timelineSpan}h</span></div>
        <div className="clock-band">
          <div className="clock-window is-decision" style={{ width: `${lastActionPosition}%` }}><span>Decision window</span></div>
          <div className="clock-window is-buffer" style={{ left: `${lastActionPosition}%`, width: `${Math.max(0, laycanPosition - lastActionPosition)}%` }}><span>Approval / laycan buffer</span></div>
          <div className="clock-marker is-last-action" style={{ left: `${lastActionPosition}%` }}><i /><strong>T+{clock.last_responsible_action_offset_hours}h</strong><small>Last responsible action</small></div>
          <div className="clock-marker is-laycan" style={{ left: `${laycanPosition}%` }}><i /><strong>T+{clock.laycan_cutoff_hours}h</strong><small>Laycan cutoff</small></div>
          <div className="clock-marker is-stockout"><i /><strong>T+{clock.stockout_threshold_hours}h</strong><small>Scenario buffer breach</small></div>
        </div>
      </div>

      <ol className="clock-stage-list" aria-label="Decision clock milestones">
        {clock.stages.map((item) => <li className={item.kind === "LAST_RESPONSIBLE_ACTION" ? "is-key" : ""} key={item.kind}><span>T+{item.offset_hours}h</span><div><strong>{item.label}</strong><p>{item.action}</p><small>{item.detail}</small></div><span className={`source-chip is-${sourceClass(item.source_status)}`}>{item.source_status}</span></li>)}
      </ol>

      <details className="clock-assumptions"><summary>Timing assumption ledger ({clock.assumptions.length})</summary><div>{clock.assumptions.map((item) => <article key={item.assumption_id}><div><strong>{item.label}</strong><span>{item.value}</span></div><small>{item.rationale}</small><span className={`source-chip is-${sourceClass(item.source_status)}`}>{item.source_status}</span></article>)}</div></details>
    </section>
  );
}

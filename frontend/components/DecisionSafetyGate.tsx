import type { DecisionSafetyGate as DecisionSafetyGateModel } from "../lib/api";

function sourceClass(value: string): string {
  return value.toLowerCase().replaceAll(" ", "-");
}

type DecisionSafetyGateProps = {
  gate: DecisionSafetyGateModel;
};

export default function DecisionSafetyGate({ gate }: DecisionSafetyGateProps) {
  const blocked = gate.status === "BLOCKED";

  return (
    <section className={`stage-card decision-safety-gate ${blocked ? "is-blocked" : "is-cleared"}`} aria-labelledby="decision-safety-gate-title">
      <div className="section-heading"><div><p className="label">DECISION SAFETY GATE</p><h3 id="decision-safety-gate-title">{blocked ? "No recommendation yet" : "Recommendation cleared for human review"}</h3><p>{gate.summary}</p></div><span className={`badge ${blocked ? "safety-badge-blocked" : "safety-badge-cleared"}`}>{gate.decision.replaceAll("_", " ")}</span></div>
      <div className="safety-check-list">
        {gate.checks.map((check) => <article className={`safety-check is-${check.state.toLowerCase()}`} key={check.check_id}><div className="safety-check-heading"><span>{check.state}</span><strong>{check.check_id.replaceAll("_", " ")}</strong></div><p>{check.summary}</p><div className="safety-sources">{check.sources.map((source, index) => <span key={`${source.label}-${index}`}><b>{source.kind}</b>{source.label}<i className={`source-chip is-${sourceClass(source.source_status)}`}>{source.source_status}</i><small>{source.detail}</small></span>)}</div>{check.next_actions.length > 0 && <ul>{check.next_actions.map((action) => <li key={action}>{action}</li>)}</ul>}</article>)}
      </div>
      {gate.next_actions.length > 0 && <div className="safety-next-actions"><strong>What to do next</strong><ol>{gate.next_actions.map((action) => <li key={action}>{action}</li>)}</ol></div>}
    </section>
  );
}

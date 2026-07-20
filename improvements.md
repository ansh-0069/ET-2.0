The strongest upgrade for both plans is an **evidence-to-action chain**: source → extracted event → DPS inputs → scenario assumptions → optimizer constraints → recommendation. It directly answers the judge criteria on accuracy, fidelity, geospatial evidence, and executability.

## Add to the enterprise solution

1. **National Supply Resilience Index**
   - A single executive score combining supply continuity, import-cost exposure, refinery utilisation, SPR readiness, and supplier concentration.
   - Makes PetraVigil a national decision platform, not only a monitoring tool.

2. **“Pre-crisis portfolio” recommendations**
   - Go beyond rerouting after an incident: recommend term-contract diversification, optional tanker capacity, alternative-grade pre-qualification, and minimum inventory by refinery.
   - This supports your “warm playbooks” differentiator with a real preventive strategy.

3. **Model governance and historical backtesting**
   - Add a model-validation layer that replays Abqaiq, Ever Given, and Red Sea events, showing prediction/calibration error.
   - Include model cards, confidence intervals, data freshness, and a “what assumptions drove this result?” view.

4. **Refinery yield and blending logic**
   - Extend crude compatibility from API gravity/sulfur matching to yield impact: diesel, petrol, LPG, fuel-oil output, blending limits, and refinery turnaround status.
   - This is a major realism upgrade over generic supply-chain tools.

5. **Commercial feasibility engine**
   - Add contract terms, supplier allocation, tanker availability, port draft/storage limits, insurance, sanctions exposure, and lead time as explicit constraints.
   - A recommendation should be labelled “technically feasible,” “commercially feasible,” and “legally cleared.”

6. **Human approval and execution workflow**
   - Define approval roles: analyst → refinery procurement head → PSU/MoPNG authority.
   - Include escalation SLAs, immutable decision logs, justification capture, and post-action outcome tracking.

7. **Recommendation confidence and fallback**
   - Each action card should show confidence, source freshness, unresolved assumptions, and Plan B/Plan C if a supplier or corridor becomes unavailable.
   - This makes the platform decision-safe, not overconfident.

8. **Strategic Petroleum Reserve optimiser**
   - Model SPR decisions as a portfolio: which reserve to release from, volume, duration, replenishment timing, and the cost of using SPR now versus preserving it for a worse scenario.

9. **Counterfactual impact measurement**
   - Show: “If we act today, expected avoided cost is ₹X; if we wait 72 hours, it falls to ₹Y.”
   - This gives decision-makers a clear action window and creates a powerful business-impact story.

10. **War-game / tabletop mode**
   - Add a secure simulation workspace for compound crises—Hormuz + Red Sea + sanctions, for example—with roles for procurement, government, shipping, and refinery teams.
   - It is highly compelling for government and enterprise buyers.

## Add to the MVP build plan

1. **Crisis Replay as the hero experience**
   - Begin with a stable baseline, inject one credible disruption signal, and visibly reach a recommendation in under 30 seconds.
   - Keep this flow flawless and rehearsed; it matters more than having five equally deep screens.

2. **Evidence panel on every action card**
   - Show the exact news/AIS/price signals, source reliability, timestamp, affected route, and extracted facts.
   - Let a judge click “Why this recommendation?” and see the causal chain.

3. **Assumption sandbox**
   - Add 3–4 sliders: closure severity, duration, Brent elasticity, route capacity, and risk appetite.
   - Re-run the scenario and recommendation live. This directly proves that your assumptions are explicit and testable.

4. **“Do nothing” versus three action portfolios**
   - Compare:
     - Do nothing
     - Lowest-cost action
     - Balanced recommendation
     - Maximum-resilience action
   - Display cost, supply protected, lead time, risk, and SPR usage. This is more persuasive than a single “best” answer.

5. **Feasibility proof and rejected alternatives**
   - For the chosen WTI/Guyana recommendation, show grade match, available volume, route risk, tanker/port constraint, and sanctions status.
   - Add “Why not Basrah Medium?” with a concise rejection reason. Judges will remember this.

6. **Historical validation card**
   - For one past event, display predicted versus actual transit delay or Brent premium, with an honest error range.
   - It makes your simulation feel like a calibrated model rather than an attractive random-number generator.

7. **Visible multi-agent trace**
   - Use a compact agent timeline: SIGINT detects → GEOINT confirms vessel anomaly → ECON estimates cost → ROUTE finds options → PROCURE solves allocation.
   - This proves the multi-agent system is substantive, not just architecture-diagram decoration.

8. **Decision timer**
   - Put a visible “Signal-to-decision: 18 sec” timer in the replay.
   - It maps perfectly to the challenge’s requirement for end-to-end response speed.

9. **Clearly label simulated versus live data**
   - Use a data-status badge: `Live`, `Historical`, or `Simulated`.
   - This earns trust. Never let seeded AIS, prices, or scenario numbers appear accidentally live.

10. **Use the 3D knowledge graph as a supporting proof, not the main demo**
   - It is visually impressive, but it can consume build time and can be hard to read.
   - Prioritise the crisis replay, scenario comparison, and action cards; keep the graph as a quick “why oil is not fungible” moment.

## Credibility fixes to make before presenting

- Use one consistent response-time baseline; the plans currently mention 5–14 days, 47 days, and 30 minutes in different places.
- Make all savings and market-impact figures traceable to a source or label them as scenario assumptions.
- Present 2025/2026 geopolitical events carefully as historical or simulated scenarios, with source/date labels.
- State clearly that PetraVigil is a decision-support system with human approval—not an autonomous crude-purchasing bot.

If time is tight, build only these five additions: crisis replay, evidence chain, assumption sandbox, action-portfolio comparison, and feasibility/rejection reasoning. Those will produce the biggest judging impact.
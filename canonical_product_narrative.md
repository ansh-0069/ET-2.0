# PetraVigil Canonical Product Narrative

## The one-sentence product

PetraVigil is an evidence-labelled, analyst-confirmed contingency-decision prototype for India's crude-supply resilience: it turns a user-entered disruption signal into a reproducible constrained recommendation, or explicitly returns `NO_RECOMMENDATION_YET` when the evidence or capacity cannot support a safe decision.

## What the working prototype does

```text
User-entered signal
  -> Gemini structured proposal or labelled deterministic fallback
  -> seeded entity matching and deterministic risk score
  -> analyst-confirmed assumptions
  -> reproducible NumPy simulation
  -> seeded OR-Tools portfolio optimisation
  -> labelled explanation
  -> local human decision record
```

The first endpoint stops at a proposal so that an analyst can inspect and edit assumptions. The workflow runs only after confirmation. A decision is attached to the exact recommendation it reviews.

## What makes the prototype distinctive

| Product safeguard | Demonstrable value |
|---|---|
| Source labels and unresolved items | Separates user-entered, historical/seeded, and simulated information so a polished screen is not mistaken for verified live evidence. |
| Analyst confirmation | Prevents an LLM extraction or a fixed score from silently becoming an operational assumption. |
| Reproducible scenario seed and visible assumptions | Lets a reviewer rerun the same scenario and challenge its inputs. |
| `NO_RECOMMENDATION_YET` gate | Refuses a plausible-looking but unsafe procurement recommendation when confidence, provenance, or feasible capacity is inadequate. |
| Finite SPR contingency | Limits the prototype bridge to a seeded maximum and requires recorded opt-in and authorization assumptions; it never triggers a drawdown. |
| Shared multi-refinery capacity drill | Treats a physical route as one shared capacity pool, so several refineries cannot each claim the same cargo capacity. |
| Local approval record | Captures an analyst decision without pretending to place an order or integrate a procurement system. |

## Evidence status ledger

| Capability | Current status | Do not claim |
|---|---|---|
| Signal intake | Implemented; always stored as `User-entered` | Continuous live monitoring or verified external news ingestion |
| Gemini | Optional structured extraction and explanation, with labelled local fallback | Gemini as factual source, price feed, legal checker, or autonomous decision maker |
| Risk and simulation | Deterministic seeded score plus reproducible simulated scenario | Calibrated live disruption probability or market forecast |
| Optimisation | OR-Tools against bundled compatibility and route-capacity constraints | Live supplier availability, tanker booking, or executable procurement |
| Map and Decision Clock | Local, source-labelled replay | AIS tracking, vessel telemetry, or operational deadline |
| Storage and approval | Local SQLite record | Enterprise audit, RBAC, ERP integration, or external action |
| Architecture ideas | Enterprise roadmap | Active Neo4j, RAG, Redis, Kafka, LangGraph, live feeds, or multi-agent orchestration |

## Five-minute judge story: one Hormuz case

**0:00-0:30 - Set the honest frame.** India needs a way to move from an uncertain disruption signal to a reviewable contingency decision. State the boundary: this is an offline, evidence-labelled decision prototype, not a live surveillance or execution platform.

**0:30-1:00 - Rehearse the event.** Open the source-labelled Hormuz replay and Decision Clock. Show how an analyst can examine a local scenario and test an approval-delay assumption before a decision becomes urgent.

**1:00-1:45 - Convert text into a proposal, not a fact.** Load the Hormuz case. Show the raw user-entered text, Gemini or the labelled fallback extraction, entity matches, unknowns, and confidence. The analyst can correct the assumptions before any simulation runs.

**1:45-2:40 - Run a reproducible constrained scenario.** Confirm the closure and alternative-capacity assumptions. Show the scenario result, seed, and portfolio comparison. Explain that the simulation is simulated and the network constraints are seeded.

**2:40-3:35 - Prove the system knows when to stop.** Use a shortfall case to surface `NO_RECOMMENDATION_YET`. Show the blocker and next action rather than a fabricated answer. This is the core trust demonstration.

**3:35-4:25 - Prove physical constraints.** Switch to the feasible case and show a selected portfolio, then use the multi-refinery allocation drill to show shared route capacity. If the SPR contingency is shown, state that it is finite, single-refinery, opt-in, and only a decision-support assumption.

**4:25-5:00 - Finish with accountability.** Record an Approve, Defer, or Reject decision. Close with: "The next production step is verified data adapters, calibration, and governed enterprise integration. Today, PetraVigil proves the safe decision workflow first."

## Statements that are safe in the demo

- "The raw signal is source-labelled and analyst reviewed."
- "Gemini proposes structure; deterministic services apply the constraints."
- "This simulation is reproducible from visible, analyst-confirmed assumptions."
- "The safety gate can refuse a recommendation."
- "This local allocation drill prevents shared capacity from being double-counted."
- "No procurement action is executed."
- "The last verified local backend run passed 37 tests."

## Statements to avoid until integrated and validated

- "We continuously monitor live AIS, news, prices, sanctions, ports, suppliers, or tankers."
- "The risk score is a calibrated probability or market forecast."
- "The system found a live vessel deviation or current supplier availability."
- "We save a measured amount of money, respond in a specified number of minutes, or improve a national outcome by a specified percentage."
- "We have active multi-agent orchestration, RAG, Neo4j, Redis, Kafka, or ERP execution."

## Production path, not a current claim

The enterprise design should add licensed and validated data adapters, provenance verification, calibration against historical outcomes, globally finite reserve/contract constraints, identity and approval controls, and controlled ERP integration. Each should be separately tested before any operational use.

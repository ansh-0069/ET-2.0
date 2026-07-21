# PETRAVIGIL - Enterprise Energy Supply Resilience Target Architecture
## Roadmap Only - Not the Current Prototype Runtime

---

## 1. Executive Summary and Status Boundary

This document describes a **proposed enterprise / government-grade target architecture**, not a statement of the active repository runtime or a claim about production performance, data access, customer deployment, response time, or ROI.

The working prototype is an evidence-labelled, analyst-confirmed local decision workflow: a user-entered signal is turned into a proposed structure (with optional Gemini extraction or a labelled fallback), reviewed by an analyst, processed through seeded deterministic risk/constraint services and a reproducible simulation, then recorded as a local human decision. It can return `NO_RECOMMENDATION_YET` rather than fabricate a recommendation. It does **not** continuously monitor feeds, track live vessels, use a deployed knowledge graph/RAG/multi-agent system, integrate with procurement systems, or execute an external action.

The production vision is to build a governed decision layer for India's crude-supply resilience that can ingest licensed, verified geopolitical and logistics data; model uncertainty; and present analyst-approved contingency options. Every production capability in this document needs separately validated data provenance, calibration, security, operational controls, and customer approval.

> **Target thesis**: Rather than claiming to predict the future, a production system should make disruption assumptions, constraints, evidence, uncertainty, and human accountability explicit enough to rehearse defensible decisions.

---

## 2. Target Problem Decomposition

The challenge breaks down into **five interconnected sub-problems**:

| # | Sub-Problem | Current State | Target State |
|---|---|---|---|
| 1 | **Signal Detection** | Manual monitoring of news, sanctions lists, AIS feeds | Continuous, multi-source ingestion with LLM-extracted structured risk events |
| 2 | **Disruption Modeling** | Static scenario planning (if any) | Probabilistic scenario trees with Monte Carlo simulation over supply corridors |
| 3 | **Supply Chain Graph** | Tribal knowledge, spreadsheets | Live Knowledge Graph encoding supplier → route → chokepoint → port → refinery → crude grade relationships |
| 4 | **Procurement Optimization** | Phone calls, broker relationships, days of deliberation | Automated alternative route/supplier scoring with cost, risk, and refinery-compatibility constraints |
| 5 | **Coordination & Execution** | Email chains, ministerial meetings | Orchestrated recommendation workflows with approval gates and audit trails |

---

## 3. Target System Architecture (Future State)

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PETRAVIGIL PLATFORM                          │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐    │
│  │  SIGNAL MESH │   │ SCENARIO     │   │ PROCUREMENT          │    │
│  │  (Ingestion  │──▶│ ENGINE       │──▶│ ORCHESTRATOR         │    │
│  │   & NLP)     │   │ (Simulation) │   │ (Optimization)       │    │
│  └──────┬───────┘   └──────┬───────┘   └──────────┬───────────┘    │
│         │                  │                       │                │
│         ▼                  ▼                       ▼                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              ENERGY KNOWLEDGE GRAPH (Neo4j + Vector Store)  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│         │                  │                       │                │
│         ▼                  ▼                       ▼                │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │         COMMAND CENTER UI (Geospatial + Dashboards)         │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Proposed Multi-Agent Architecture (Future State)

The production target could use a **multi-agent system** in which specialized services collaborate through a governed graph and event bus. No such active orchestration is part of the current prototype:

```
┌──────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR (Supervisor)                │
│                                                                  │
│  Manages agent lifecycle, conflict resolution, and escalation    │
│  Routes tasks based on signal type and urgency tier              │
└──────────┬──────────┬──────────┬──────────┬──────────┬───────────┘
           │          │          │          │          │
    ┌──────▼──┐ ┌─────▼────┐ ┌──▼─────┐ ┌─▼──────┐ ┌▼─────────┐
    │ SIGINT  │ │ GEOINT   │ │ ECON   │ │ ROUTE  │ │ PROCURE  │
    │ Agent   │ │ Agent    │ │ Agent  │ │ Agent  │ │ Agent    │
    │         │ │          │ │        │ │        │ │          │
    │ News,   │ │ AIS      │ │ Spot   │ │ Route  │ │ Generate │
    │ Policy, │ │ Vessel   │ │ Price, │ │ Risk,  │ │ Procure- │
    │ Sanction│ │ Tracking │ │ Demand │ │ Alt    │ │ ment     │
    │ Signals │ │ Port     │ │ Supply │ │ Paths  │ │ Recommen-│
    │         │ │ Status   │ │ Model  │ │        │ │ dations  │
    └─────────┘ └──────────┘ └────────┘ └────────┘ └──────────┘
```

**Agent Descriptions:**

| Agent | Role | Input Sources | Output |
|---|---|---|---|
| **SIGINT Agent** | Monitors and extracts structured geopolitical risk events from unstructured sources | News APIs (GDELT, Event Registry), sanctions registries (OFAC, EU), policy documents, social signals | Structured risk events with entity extraction, severity score, affected corridors |
| **GEOINT Agent** | Tracks vessel movements, port congestion, chokepoint traffic patterns | AIS data feeds (MarineTraffic/VesselFinder API), satellite imagery APIs, port authority feeds | Vessel position updates, congestion indices, anomaly detection (dark shipping, route deviations) |
| **ECON Agent** | Models commodity price movements, demand-supply balances, and economic impact | Platts/Argus price feeds, ICE/NYMEX futures, IEA/OPEC reports, Indian refinery throughput data | Price forecasts, demand-supply gap analysis, import bill impact estimates |
| **ROUTE Agent** | Evaluates and scores alternative procurement corridors under disruption scenarios | Knowledge Graph (routes, distances, transit times), GEOINT outputs, historical transit data | Ranked alternative routes with transit time, cost delta, risk score, capacity constraints |
| **PROCURE Agent** | Synthesizes all agent outputs into executable procurement recommendations | All other agents' outputs, refinery configuration data, contract terms, SPR levels | Procurement action cards: supplier, grade, volume, route, estimated cost, risk-adjusted ROAS |

### 3.3 Data Architecture

#### 3.3.1 Data Sources (Production-Grade)

| Category | Source | Update Frequency | Data Type |
|---|---|---|---|
| **Geopolitical Signals** | GDELT Project (Global Database of Events) | 15-minute | Structured event records |
| | Event Registry API | Real-time | News articles with NLP enrichment |
| | OFAC SDN List (US Treasury) | Daily | Sanctions entities & vessels |
| | EU Sanctions Map | Daily | Sanctioned entities |
| | UN Comtrade | Monthly | Trade flow statistics |
| **Maritime Intelligence** | AIS via MarineTraffic/Spire Maritime | Real-time | Vessel positions, type, draft, destination |
| | Lloyd's List Intelligence | Daily | Port calls, vessel fixtures |
| | Suez/Hormuz transit logs | Daily | Chokepoint throughput |
| **Commodity Markets** | ICE Brent Futures (via exchange API) | Tick-level | Price, volume, open interest |
| | Platts/Argus (via S&P Global) | Daily | Physical crude assessments by grade |
| | PPAC India petroleum statistics | Monthly | Indian import volumes, source countries |
| **Infrastructure** | Indian refinery configurations (PPAC) | Static + updates | Refinery capacity, crude diet, complexity |
| | Global port databases | Weekly | Port capacity, draft limits, infrastructure |
| | Pipeline & terminal maps | Static | Geographic infrastructure topology |

#### 3.3.2 Knowledge Graph Schema

```
┌─────────┐     EXPORTS      ┌──────────┐    SHIPS_VIA     ┌───────────┐
│ COUNTRY │────────────────▶│  CRUDE   │───────────────▶│  ROUTE    │
│         │                  │  GRADE   │                │ (corridor)│
└─────────┘                  └──────────┘                └───────────┘
     │                            │                          │
     │ HAS_RISK_EVENT             │ COMPATIBLE_WITH          │ PASSES_THROUGH
     ▼                            ▼                          ▼
┌─────────┐                ┌──────────┐               ┌───────────┐
│  RISK   │                │ REFINERY │               │ CHOKEPOINT│
│  EVENT  │                │          │               │           │
└─────────┘                └──────────┘               └───────────┘
     │                          │                          │
     │ AFFECTS                  │ OPERATED_BY              │ HAS_CONGESTION
     ▼                          ▼                          ▼
┌─────────┐                ┌──────────┐               ┌───────────┐
│CORRIDOR │                │ COMPANY  │               │  PORT     │
│         │                │ (IOC/    │               │           │
└─────────┘                │  BPCL/..)│               └───────────┘
                           └──────────┘
```

**Key Relationships in Neo4j:**

```cypher
// Example: Find all crude grades that flow through Strait of Hormuz
// and are compatible with Jamnagar refinery
MATCH (g:CrudeGrade)-[:SHIPS_VIA]->(r:Route)-[:PASSES_THROUGH]->(c:Chokepoint {name: 'Strait of Hormuz'})
MATCH (g)-[:COMPATIBLE_WITH]->(ref:Refinery {name: 'Jamnagar'})
RETURN g.name, g.api_gravity, g.sulfur_content, r.name, r.avg_transit_days

// Example: When Hormuz is disrupted, find alternative grades + routes
MATCH (g:CrudeGrade)-[:COMPATIBLE_WITH]->(ref:Refinery {name: 'Jamnagar'})
MATCH (g)-[:SHIPS_VIA]->(r:Route)
WHERE NOT (r)-[:PASSES_THROUGH]->(:Chokepoint {name: 'Strait of Hormuz'})
RETURN g.name, r.name, r.avg_transit_days, r.cost_per_barrel_premium
ORDER BY r.cost_per_barrel_premium ASC
```

**Node Properties:**

| Node | Key Properties |
|---|---|
| `Country` | name, region, OPEC_member, sanctioned, production_bpd, export_capacity_bpd |
| `CrudeGrade` | name, API_gravity, sulfur_pct, TAN, pour_point, origin_country, benchmark_differential |
| `Route` | name, distance_nm, avg_transit_days, cost_per_barrel, insurance_premium, piracy_risk |
| `Chokepoint` | name, lat, lon, daily_throughput_mbpd, alternative_route, width_nm |
| `Refinery` | name, location, capacity_bpd, complexity_index, crude_diet (list of compatible grades) |
| `Port` | name, country, max_draft_m, storage_capacity_mb, congestion_index |
| `RiskEvent` | type, severity (1-10), source, timestamp, affected_entities, confidence_score |
| `Vessel` | IMO, name, type (VLCC/Suezmax/Aframax), DWT, flag_state, current_position |

### 3.4 Core Processing Pipelines

#### Pipeline 1: Signal Ingestion & Risk Scoring

```
Raw Sources ──▶ Source Adapters ──▶ LLM Extraction ──▶ Entity Resolution ──▶ Risk Scoring ──▶ Knowledge Graph
                                         │
                                         ▼
                                   Structured Event:
                                   {
                                     type: "SANCTIONS_ESCALATION",
                                     entities: ["Iran", "crude_oil"],
                                     corridors_affected: ["Persian Gulf → Jamnagar"],
                                     severity: 8.2,
                                     confidence: 0.87,
                                     source_evidence: [...],
                                     timestamp: "2026-07-19T14:30:00Z"
                                   }
```

**LLM Signal Extraction Prompt Strategy:**

The SIGINT Agent uses a structured extraction prompt with few-shot examples specific to energy geopolitics. Key extraction targets:
- **Event Type**: Taxonomy of ~40 event types (sanctions, military action, port closure, pipeline attack, diplomatic shift, OPEC decision, etc.)
- **Affected Entities**: Countries, companies, crude grades, infrastructure
- **Severity Assessment**: 1-10 scale calibrated against historical disruptions
- **Temporal Indicators**: Immediate, short-term (days), medium-term (weeks), structural (months+)
- **Confidence Score**: Based on source reliability, corroboration count, information freshness

**Risk Scoring Model:**

Each corridor gets a composite **Disruption Probability Score (DPS)** updated continuously:

```
DPS(corridor, t) = w1 × GeopoliticalRisk(t) 
                 + w2 × MaritimeThreatLevel(t) 
                 + w3 × SanctionsExposure(t) 
                 + w4 × HistoricalDisruptionFreq 
                 + w5 × ChokePointConcentration
                 + w6 × InsuranceMarketSignal(t)
```

Where weights are calibrated against historical disruption events (2019 Abqaiq attack, 2021 Suez blockage, 2023 Houthi escalation, 2025 Iran standoff).

#### Pipeline 2: Scenario Simulation Engine

The heart of PetraVigil — a **Monte Carlo simulation engine** that pre-computes disruption scenarios:

**Scenario Tree Structure:**

```
                              ┌─── Sub-scenario: Hormuz fully blocked (5%)
              ┌── Scenario A: │
              │   Iran-US     ├─── Sub-scenario: Partial blockade (15%)
              │   Escalation  │
              │   (DPS: 0.72) └─── Sub-scenario: Insurance spike only (80%)
              │
Root State ───┼── Scenario B: ┌─── Sub-scenario: 2+ month closure (10%)
(Current)     │   Red Sea     ├─── Sub-scenario: Periodic attacks (40%)
              │   Disruption  └─── Sub-scenario: Naval escort normalizes (50%)
              │   (DPS: 0.65)
              │
              └── Scenario C: ┌─── Sub-scenario: Full embargo (3%)
                  Russia       ├─── Sub-scenario: Price cap tightening (30%)
                  Sanctions    └─── Sub-scenario: Status quo (67%)
                  Shift
                  (DPS: 0.41)
```

**For each leaf scenario, the engine computes:**

1. **Supply Impact**: Which corridors are affected, volume reduction (bpd), duration estimate
2. **Price Impact**: Brent premium estimation using historical elasticity models
3. **Procurement Alternatives**: Ranked list of alternative supplier-grade-route combinations
4. **Cost Impact**: Total additional import bill for India (₹ crores / $M)
5. **SPR Drawdown Rate**: Days of strategic reserve consumption at projected import levels
6. **Refinery Impact**: Which refineries face feedstock shortages, capacity utilization drop

**Simulation Parameters:**
- **10,000 Monte Carlo runs** per scenario tree
- **Disruption duration**: Sampled from historical distributions (log-normal)
- **Price elasticity**: Calibrated against 2019-2025 disruption events
- **Transit time uncertainty**: Based on AIS-derived historical variance per route
- **Demand inelasticity**: India's short-term demand elasticity ≈ -0.05 (highly inelastic)

#### Pipeline 3: Adaptive Procurement Orchestrator

Given a triggered scenario, the Procurement Orchestrator solves a **constrained optimization problem**:

**Objective Function:**
```
Minimize: TotalCost = Σ (volume_i × (spot_price_i + freight_i + insurance_i + risk_premium_i))

Subject to:
  1. Σ volume_i ≥ MinDemand (refinery minimum throughput)
  2. grade_i ∈ CompatibleGrades(refinery_j) ∀ (i,j) assignments
  3. volume_i ≤ AvailableCapacity(supplier_i, route_i)
  4. DPS(route_i) ≤ MaxAcceptableRisk
  5. Σ SPR_drawdown ≤ MaxSPRUtilization (e.g., 50% of reserves)
  6. transit_time_i ≤ MaxLeadTime (based on refinery inventory days)
  7. Diversification: No single corridor > 40% of total volume
```

**Output: Procurement Action Cards**

```json
{
  "action_id": "PA-2026-0719-001",
  "trigger_scenario": "Hormuz partial blockade",
  "urgency": "HIGH",
  "confidence": 0.82,
  "recommendations": [
    {
      "rank": 1,
      "action": "INCREASE_VOLUME",
      "supplier_country": "United States",
      "crude_grade": "WTI Midland",
      "volume_bpd": 150000,
      "route": "Houston → COGH → Jamnagar",
      "transit_days": 42,
      "cost_premium": "+$3.20/bbl vs current",
      "refinery_compatibility": ["Jamnagar (RIL)", "Kochi (BPCL)"],
      "rationale": "US Gulf Coast has excess export capacity. WTI Midland API/sulfur profile matches Jamnagar complex refinery diet."
    },
    {
      "rank": 2,
      "action": "REDIRECT_EXISTING",
      "supplier_country": "Guyana",
      "crude_grade": "Liza Light",
      "volume_bpd": 80000,
      "route": "Georgetown → COGH → Paradip",
      "transit_days": 38,
      "cost_premium": "+$1.80/bbl vs current",
      "refinery_compatibility": ["Paradip (IOC)"],
      "rationale": "Guyana production ramping. No chokepoint exposure. Light sweet crude suitable for Paradip."
    },
    {
      "rank": 3,
      "action": "ACTIVATE_SPR",
      "volume_bpd": 200000,
      "duration_days": 15,
      "spr_utilization": "32%",
      "rationale": "Bridge supply gap while term contract redirections take effect."
    }
  ],
  "total_additional_cost_estimate": {
    "daily": "$48.2M",
    "monthly": "$1.45B",
    "as_pct_gdp": "0.05%"
  },
  "evidence_chain": [
    {"source": "Reuters", "headline": "...", "timestamp": "..."},
    {"source": "AIS Data", "observation": "12 VLCCs diverted from Hormuz in last 6 hours"},
    {"source": "ICE Brent", "observation": "Brent up $4.20 in session, backwardation steepening"}
  ]
}
```

---

## 4. Target Technology Stack

### 4.1 Core Infrastructure

| Layer | Technology | Rationale |
|---|---|---|
| **Orchestration** | Kubernetes (EKS/GKE) + Argo Workflows | Scalable agent orchestration, DAG-based pipeline management |
| **Event Streaming** | Apache Kafka | Real-time event bus between agents, guaranteed delivery |
| **Knowledge Graph** | Neo4j Enterprise | Native graph DB for complex relationship traversal |
| **Vector Store** | Weaviate / Pinecone | RAG over geopolitical intelligence documents |
| **Time-Series DB** | TimescaleDB | AIS positions, commodity prices, risk scores over time |
| **Object Storage** | S3 / GCS | Raw data lake for historical analysis |
| **Compute** | GPU instances (A100) for LLM inference | Low-latency signal extraction |

### 4.2 AI/ML Stack

| Component | Technology | Purpose |
|---|---|---|
| **LLM (Signal Extraction)** | Gemini 2.5 Pro / GPT-4o / Claude | Structured event extraction from news/policy docs |
| **LLM (RAG)** | Gemini 2.5 Flash + Vector DB | Question answering over intelligence corpus |
| **Agent Framework** | LangGraph / CrewAI | Multi-agent orchestration with tool use |
| **Embedding Model** | text-embedding-3-large | Document & event embedding for similarity/RAG |
| **Anomaly Detection** | Isolation Forest + LSTM | AIS anomaly detection (dark shipping, route deviations) |
| **Simulation** | Custom Python (NumPy/SciPy) + Ray | Distributed Monte Carlo simulation |
| **Optimization** | Google OR-Tools / PuLP | Procurement optimization (LP/MIP solver) |
| **Geospatial** | GeoPandas + H3 (Uber's hexagonal grid) | Spatial indexing of vessel positions, route geometry |

### 4.3 Frontend

| Component | Technology | Purpose |
|---|---|---|
| **Web App** | Next.js 15 (React 19) | Server-side rendering, API routes |
| **Mapping** | Deck.gl + Mapbox GL JS | High-performance WebGL geospatial visualization |
| **Charts** | D3.js + Observable Plot | Custom data visualizations |
| **Real-time** | WebSocket (Socket.io) | Live updates for vessel tracking, alert streaming |
| **Graph Viz** | vis-network / force-graph | Knowledge graph exploration |

---

## 5. Target Differentiators and Validation Hypotheses

The comparisons and differentiators below are product-positioning hypotheses, not an audited competitive study or a claim that the current prototype already delivers these capabilities. Validate them with domain users, licensed data providers, and representative historical cases.

### 5.1 Positioning Hypothesis vs. Traditional SCRM Tools

| Dimension | Traditional Tools | Proposed PetraVigil Target |
|---|---|---|
| Signal source | Varies by product and deployment | Intended: governed ingestion of verified news, AIS, sanctions, and market data where licensed. |
| Update frequency | Varies by data provider and operating model | Target freshness must be defined and tested per source, not presumed. |
| Scenario modeling | Varies by product and deployment | Intended: probabilistic scenarios with uncertainty bounds and explicit assumptions. |
| Domain specificity | Varies | Intended: crude-grade, refinery-compatibility, route, and policy constraints. |
| Recommendation type | Varies | Intended: analyst-approved decision cards with alternatives, blockers, and evidence; not autonomous execution. |
| Geospatial intelligence | Varies | Intended: source-labelled maritime context only after licensed feeds and validation. |

### 5.2 Candidate Technical Differentiators to Validate

1. **Corridor-level disruption score**: A proposed composite score for geopolitical, maritime, economic, and insurance signals. It must be calibrated against historical outcomes and shown with uncertainty before it can be described as a probability.

2. **Rehearsed scenario playbooks**: A production system could maintain governed, versioned playbooks for priority disruptions. Each needs ownership, review cadence, and evidence of calibration; this is not an active current runtime feature.

3. **Refinery-grade compatibility constraints**: The prototype already uses seeded compatibility and route capacity constraints. A production model would require refinery-validated crude-diet data, commercial constraints, and change controls.

4. **Evidence-chain transparency**: The prototype source-labels user-entered, seeded/historical, and simulated information. Production evidence chains would need immutable source identifiers, freshness, licences, verification status, and audit retention.

5. **SPR policy modelling**: The prototype permits a finite, opt-in, single-refinery contingency assumption. A production model must represent a globally finite reserve and authority-specific policy approvals before any operational recommendation.

---

## 6. Target Scalability Architecture

### 6.1 Horizontal Scaling

```
                    Load Balancer
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
      ┌──────────┐ ┌──────────┐ ┌──────────┐
      │ API Pod  │ │ API Pod  │ │ API Pod  │   ← Stateless, auto-scaled
      │ (Next.js)│ │ (Next.js)│ │ (Next.js)│
      └──────────┘ └──────────┘ └──────────┘
            │            │            │
            ▼            ▼            ▼
      ┌─────────────────────────────────────┐
      │        Redis Cluster (Cache)         │   ← Session, rate limiting
      └─────────────────────────────────────┘
            │
      ┌─────┴──────────────────────────┐
      ▼                                ▼
┌──────────────┐              ┌──────────────────┐
│ Kafka Cluster│              │ Agent Workers     │
│ (3+ brokers) │──────────▶│ (K8s Jobs, auto-  │
│              │              │  scaled by queue  │
└──────────────┘              │  depth)           │
                              └──────────────────┘
```

### 6.2 Proposed Deployment Models

Potential deployment models to validate with customers:
- **Sovereign Deployment**: On-premises for government (MoPNG, PPAC)
- **Private Cloud**: For PSU refiners (IOC, BPCL, HPCL)
- **SaaS Multi-Tenant**: For trading houses, insurance companies, shipping firms

### 6.3 Target Performance Criteria (Not Yet Validated)

| Metric | Target |
|---|---|
| Signal ingestion to risk score | < 30 seconds |
| News event to structured extraction | < 10 seconds |
| Scenario simulation (10K runs) | < 2 minutes |
| Procurement recommendation generation | < 5 minutes |
| End-to-end signal-to-recommendation | < 30 minutes |
| AIS position update processing | < 5 seconds |
| Dashboard refresh (WebSocket push) | < 1 second |
| Concurrent users | 500+ |

---

## 7. Target Security & Compliance Controls

| Aspect | Implementation |
|---|---|
| Data classification | Tiered: PUBLIC, CONFIDENTIAL, SECRET (for government deployment) |
| Authentication | SAML 2.0 / OAuth 2.0 + MFA |
| Authorization | RBAC with row-level security on procurement recommendations |
| Encryption | TLS 1.3 in transit, AES-256 at rest |
| Audit logging | Immutable audit trail for all recommendation actions |
| Data residency | India-hosted for government deployment (AWS Mumbai / Azure Central India) |
| AI governance | Model cards for all ML components, explainability reports for procurement recommendations |

---

## 8. Business Model and Value Validation

### 8.1 Value Hypotheses (Not Quantified Claims)

The repository contains no validated customer baseline, live market integration, deployment, or cost-outcome study. Do not claim a response-time improvement, national import-bill saving, price saving, SPR efficiency, or productivity percentage. The correct enterprise validation plan is:

| Value hypothesis | Evidence required before making a quantified claim |
|---|---|
| Analysts can make a more traceable contingency decision | Time-stamped baseline and controlled pilot measurements across comparable cases. |
| Constraints can reduce impossible procurement options | Refinery, route, contract, and supplier validation against real historical decisions. |
| Earlier visibility can reduce commercial exposure | Licensed price/quote data, a defined counterfactual, and independent financial review. |
| SPR assumptions can improve policy rehearsal | Authorized policy scenarios, a globally finite reserve model, and government sign-off. |
| Evidence labelling can reduce review risk | User research, audit feedback, and documented incident/review outcomes. |

### 8.2 Target Users

| User Tier | Organization | Use Case |
|---|---|---|
| **Strategic** | MoPNG, PPAC, PMO | National energy security monitoring, policy simulation |
| **Operational** | IOC, BPCL, HPCL, MRPL, RIL, Nayara | Crude procurement optimization, refinery feedstock planning |
| **Market** | Commodity traders, shipping companies | Route risk assessment, freight rate forecasting |
| **Insurance** | P&I clubs, war risk insurers | Maritime risk underwriting, premium calculation |
| **Intelligence** | Think tanks, defence establishments | Geopolitical energy dependency analysis |

---

## 9. Target Deployment Roadmap

### Phase 1: Foundation (Months 1-3)
- Knowledge Graph construction (India crude import network)
- Signal ingestion pipeline (GDELT, news APIs)
- Basic LLM extraction for geopolitical events
- Corridor-level DPS scoring
- Core geospatial visualization

### Phase 2: Intelligence (Months 4-6)
- Multi-agent system deployment
- AIS integration for vessel tracking
- Monte Carlo scenario simulation engine
- RAG over historical disruption intelligence
- Procurement optimization (v1)

### Phase 3: Operationalization (Months 7-9)
- Real-time alerting and notification workflows
- Procurement action card generation
- Integration with refinery ERP systems
- SPR drawdown modeling
- Government deployment (PPAC pilot)

### Phase 4: Scale & Refine (Months 10-12)
- Multi-country expansion (Japan, South Korea, EU)
- Insurance market integration
- Predictive model refinement with feedback loops
- Mobile command center app
- War-gaming / tabletop exercise mode

---

## 10. Market Positioning Hypotheses (Validate Before Sales)

| Competitor | Known category strength | Proposed PetraVigil wedge to validate |
|---|---|---|
| **Kpler** | Commodity data and vessel-tracking category | Use trusted data-provider inputs as part of a governed India-specific decision workflow; validate integration and overlap. |
| **Vortexa** | Cargo-tracking category | Validate whether a constrained contingency-decision layer adds value beyond tracking. |
| **Palantir Foundry** | General-purpose data and operational analytics category | Validate domain-data, governance, and implementation advantages rather than asserting differentiation. |
| **Everstream Analytics** | Supply-chain risk-monitoring category | Validate whether crude-grade and shared-capacity constraints address a distinct buyer workflow. |
| **PPAC and public data sources** | Government reference-data category | Treat them as possible inputs/stakeholders, not as a system to replace. |

**Positioning hypothesis:** PetraVigil's possible wedge is an India-specific, governed decision and constraint layer that consumes trusted data-provider and enterprise inputs. Whether this is differentiated, defensible, and worth paying for must be validated through customer discovery and competitive diligence.

---

## 11. Target Risk Mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucination in risk scoring | Ensemble extraction (multiple models), confidence thresholds, human-in-the-loop for scores > 7 |
| AIS data gaps (dark shipping) | Anomaly detection on AIS dropout patterns, satellite imagery fallback |
| Model calibration drift | Continuous backtesting against historical disruptions, quarterly recalibration |
| Data source unavailability | Multi-source redundancy for every signal category, graceful degradation |
| Government adoption resistance | Tabletop exercise mode for low-risk familiarization, parallel-run with existing processes |

---

*Target direction: make disruption planning more explicit, evidence-aware, and accountable before any production automation is considered.*

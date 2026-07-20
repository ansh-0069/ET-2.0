# PETRAVIGIL — AI-Driven Energy Supply Chain Resilience Platform
## Full-Scale Enterprise / Government-Grade Solution Architecture

---

## 1. Executive Summary

**PetraVigil** (Latin: *petra* = rock/petroleum, *vigil* = watchman) is a sovereign energy intelligence platform that continuously monitors geopolitical risk signals, models disruption scenarios with probabilistic simulation, and generates executable procurement re-routing recommendations — compressing the signal-to-action cycle from **weeks to under 30 minutes**.

Built for India's Ministry of Petroleum & Natural Gas (MoPNG), the Petroleum Planning & Analysis Cell (PPAC), and public-sector refiners like IndianOil/BPCL/HPCL, PetraVigil transforms India's reactive crude oil procurement posture into an anticipatory, resilience-first strategy.

> **Core Thesis**: The platform doesn't predict the future — it exhaustively pre-computes futures, scores them by probability, and keeps procurement playbooks warm for each one. When a disruption signal fires, the response is retrieval, not invention.

---

## 2. Problem Decomposition

The challenge breaks down into **five interconnected sub-problems**:

| # | Sub-Problem | Current State | Target State |
|---|---|---|---|
| 1 | **Signal Detection** | Manual monitoring of news, sanctions lists, AIS feeds | Continuous, multi-source ingestion with LLM-extracted structured risk events |
| 2 | **Disruption Modeling** | Static scenario planning (if any) | Probabilistic scenario trees with Monte Carlo simulation over supply corridors |
| 3 | **Supply Chain Graph** | Tribal knowledge, spreadsheets | Live Knowledge Graph encoding supplier → route → chokepoint → port → refinery → crude grade relationships |
| 4 | **Procurement Optimization** | Phone calls, broker relationships, days of deliberation | Automated alternative route/supplier scoring with cost, risk, and refinery-compatibility constraints |
| 5 | **Coordination & Execution** | Email chains, ministerial meetings | Orchestrated recommendation workflows with approval gates and audit trails |

---

## 3. System Architecture

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

### 3.2 Multi-Agent Architecture (Agentic AI Core)

PetraVigil uses a **multi-agent system** where specialized agents collaborate through a shared knowledge graph and event bus:

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

## 4. Technology Stack

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

## 5. Key Differentiators (Why This Wins)

### 5.1 vs. Traditional SCRM Tools (SAP IBP, Kinaxis, o9 Solutions)

| Dimension | Traditional Tools | PetraVigil |
|---|---|---|
| Signal source | Manual input, structured data only | Multi-modal: news NLP, AIS, sanctions, prices |
| Update frequency | Weekly/monthly planning cycles | Continuous (sub-minute for critical signals) |
| Scenario modeling | Deterministic what-if | Probabilistic Monte Carlo with confidence intervals |
| Domain specificity | Generic supply chain | Purpose-built for crude oil import corridors |
| Recommendation type | "Consider alternatives" | Executable action cards with specific grades, routes, costs |
| Geospatial intelligence | None | Live vessel tracking, chokepoint monitoring |

### 5.2 Novel Technical Contributions

1. **Corridor-Level Disruption Probability Score (DPS)**: A composite, continuously-updated risk metric that fuses geopolitical, maritime, economic, and insurance signals into a single actionable score per supply corridor. No existing product offers this at corridor granularity with real-time updates.

2. **Pre-Computed Scenario Playbooks**: Instead of generating recommendations after a crisis hits, PetraVigil maintains a library of "warm" playbooks for the top-N most probable disruption scenarios, updated daily. When a scenario triggers, the response is retrieval + minor adjustment, not computation from scratch.

3. **Refinery-Grade Compatibility Constraints**: Most supply chain tools treat "oil" as fungible. PetraVigil encodes the technical reality that a complex refinery like Jamnagar can process heavy sour crude that a simple refinery like Bina cannot. Recommendations respect refinery crude diet constraints.

4. **Evidence Chain Transparency**: Every recommendation comes with a full evidence chain linking back to the specific signals, AIS observations, and price movements that triggered it. This is critical for government procurement where audit trails are mandatory.

5. **SPR Integration**: Strategic Petroleum Reserve drawdown is modeled as a decision variable in the optimization, not an afterthought. The system knows India's SPR levels and can recommend optimal drawdown strategies as bridge supplies.

---

## 6. Scalability Architecture

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

### 6.2 Multi-Tenancy

The platform supports multiple deployment models:
- **Sovereign Deployment**: On-premises for government (MoPNG, PPAC)
- **Private Cloud**: For PSU refiners (IOC, BPCL, HPCL)
- **SaaS Multi-Tenant**: For trading houses, insurance companies, shipping firms

### 6.3 Performance Targets

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

## 7. Security & Compliance

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

## 8. Business Model & Impact Quantification

### 8.1 Value Proposition (Quantified)

Based on the McKinsey finding that economies with integrated response intelligence stabilize **47 days faster**:

| Metric | Without PetraVigil | With PetraVigil | Impact |
|---|---|---|---|
| Disruption response time | 5-14 days | < 1 day | 85% reduction |
| Spot market premium exposure | Full Brent spike (avg +$8/bbl in 2025) | Partially hedged via early action (+$3/bbl) | ~$5/bbl savings |
| SPR utilization efficiency | Reactive drawdown, often late | Optimized drawdown timing | 30% less SPR consumption |
| Annual import bill savings (moderate disruption year) | Baseline | -$2.5B to -$4B annually | Significant fiscal impact |
| Procurement team productivity | 80% time on data gathering | 80% time on decision-making | Role transformation |

### 8.2 Target Users

| User Tier | Organization | Use Case |
|---|---|---|
| **Strategic** | MoPNG, PPAC, PMO | National energy security monitoring, policy simulation |
| **Operational** | IOC, BPCL, HPCL, MRPL, RIL, Nayara | Crude procurement optimization, refinery feedstock planning |
| **Market** | Commodity traders, shipping companies | Route risk assessment, freight rate forecasting |
| **Insurance** | P&I clubs, war risk insurers | Maritime risk underwriting, premium calculation |
| **Intelligence** | Think tanks, defence establishments | Geopolitical energy dependency analysis |

---

## 9. Deployment Roadmap

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

## 10. Competitive Landscape

| Competitor | Strength | PetraVigil Advantage |
|---|---|---|
| **Kpler** | Commodity data, vessel tracking | We add AI-driven recommendations + scenario simulation |
| **Vortexa** | Real-time cargo tracking | We add geopolitical risk fusion + procurement optimization |
| **Palantir Foundry** | General-purpose analytics | We are domain-specific with energy supply chain ontology |
| **Everstream Analytics** | Supply chain risk monitoring | We go beyond risk scoring to executable procurement actions |
| **Preset Analytics (PPAC)** | Government data repository | We add real-time intelligence + AI-driven decision support |

**PetraVigil's moat**: No existing tool combines geopolitical NLP + AIS intelligence + energy-specific knowledge graph + Monte Carlo simulation + constrained procurement optimization in a single, real-time platform. Each competitor covers 1-2 of these; PetraVigil integrates all five.

---

## 11. Risk Mitigation (For the Platform Itself)

| Risk | Mitigation |
|---|---|
| LLM hallucination in risk scoring | Ensemble extraction (multiple models), confidence thresholds, human-in-the-loop for scores > 7 |
| AIS data gaps (dark shipping) | Anomaly detection on AIS dropout patterns, satellite imagery fallback |
| Model calibration drift | Continuous backtesting against historical disruptions, quarterly recalibration |
| Data source unavailability | Multi-source redundancy for every signal category, graceful degradation |
| Government adoption resistance | Tabletop exercise mode for low-risk familiarization, parallel-run with existing processes |

---

*PetraVigil: From reactive crisis management to anticipatory resilience — because the next disruption won't wait for a committee meeting.*

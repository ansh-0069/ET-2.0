from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "phase": "8",
        "workflow": "analyst-confirmed",
        "runtime": "local-prototype",
    }


def test_canonical_scenario_endpoint_returns_contract() -> None:
    response = client.get("/api/v1/scenarios/canonical")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario_id"] == "SC-HORMUZ-PARTIAL-BLOCKADE"
    assert payload["status"] == "Simulated"
    assert payload["recommendations"][0]["recommendation_id"] == "PA-HORMUZ-001"


def test_canonical_run_is_persisted_and_retrievable() -> None:
    created = client.post("/api/v1/scenario-runs/canonical")

    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "COMPLETED"
    assert payload["scenario"]["scenario_id"] == "SC-HORMUZ-PARTIAL-BLOCKADE"

    retrieved = client.get(f"/api/v1/scenario-runs/{payload['run_id']}")
    latest = client.get("/api/v1/scenario-runs/latest")

    assert retrieved.status_code == 200
    assert retrieved.json()["run_id"] == payload["run_id"]
    assert latest.status_code == 200


def test_seeded_network_returns_safe_alternatives() -> None:
    summary = client.get("/api/v1/network/summary")
    alternatives = client.get("/api/v1/network/alternatives", params={"refinery": "Jamnagar", "disrupted_chokepoint": "HORMUZ"})

    assert summary.status_code == 200
    assert summary.json()["refineries"] == 3
    assert alternatives.status_code == 200
    assert alternatives.json()[0]["crude_grade"] == "WTI Midland"
    assert all(option["avoids_chokepoint"] == "HORMUZ" for option in alternatives.json())


def test_gemini_endpoint_has_labelled_offline_fallback(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    response = client.post(
        "/api/v1/intelligence/extract",
        json={"text": "A shipping advisory reports possible disruption near Hormuz, affecting India-bound crude cargoes."},
    )

    assert response.status_code == 200
    assert response.json()["provider_status"] == "Cached demo result"


def test_signal_mesh_persists_resolutions_and_dps(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    created = client.post(
        "/api/v1/signals/process",
        json={"text": "A shipping advisory reports tanker deviation and a rising insurance premium near Hormuz affecting India-bound crude cargoes."},
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["source_status"] == "User-entered"
    assert payload["review_required"] is True
    assert all(item["resolved"] for item in payload["entity_resolutions"])
    assert payload["risk_scores"][0]["corridor_id"] == "Persian Gulf -> West India"
    assert payload["risk_scores"][0]["score"] > 0.6

    history = client.get("/api/v1/signals")
    assert history.status_code == 200
    assert any(item["signal_id"] == payload["signal_id"] for item in history.json())


def test_monte_carlo_simulation_is_reproducible_and_persisted() -> None:
    payload = {"closure_severity": 0.6, "disruption_duration_days": 21, "brent_elasticity_usd_per_mmbpd": 5.4, "alternative_route_capacity_ratio": 0.72, "n_runs": 1000, "random_seed": 42}
    first = client.post("/api/v1/simulations", json=payload)
    second = client.post("/api/v1/simulations", json=payload)

    assert first.status_code == 201
    assert first.json()["brent_premium_usd_per_bbl"] == second.json()["brent_premium_usd_per_bbl"]
    assert first.json()["additional_cost_usd_per_day"]["p90"] > first.json()["additional_cost_usd_per_day"]["p10"]
    assert len(first.json()["series"]) == 21
    assert client.get("/api/v1/simulations/latest").status_code == 200


def test_portfolio_optimizer_returns_four_executable_comparisons() -> None:
    response = client.post("/api/v1/portfolios", json={"refinery": "Jamnagar", "required_volume_bpd": 210000, "alternative_route_capacity_ratio": 0.72})

    assert response.status_code == 201
    portfolios = response.json()["portfolios"]
    assert [item["label"] for item in portfolios] == ["DO_NOTHING", "LOWEST_COST", "BALANCED", "MAX_RESILIENCE"]
    assert portfolios[0]["allocations"] == []
    assert all(item["total_volume_bpd"] == 210000 for item in portfolios[1:])
    assert client.get("/api/v1/portfolios/latest").status_code == 200


def test_human_approval_is_persisted_without_external_execution() -> None:
    created = client.post(
        "/api/v1/approvals/canonical",
        json={
            "decision": "APPROVED",
            "decided_by": "Demo Procurement Lead",
            "justification": "Approve the local recommendation for analyst-led commercial validation only.",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["recommendation_id"] == "PA-HORMUZ-001"
    assert payload["execution_external"] is False

    history = client.get("/api/v1/approvals")
    assert history.status_code == 200
    assert any(item["approval_id"] == payload["approval_id"] for item in history.json())


def test_judge_replay_flow_is_complete_and_safe(monkeypatch) -> None:
    """Protect the exact signal-to-decision journey used in the hackathon demo."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    signal = client.post(
        "/api/v1/signals/process",
        json={
            "text": "Shipping advisory: elevated military activity near the Strait of Hormuz may disrupt India-bound crude cargoes over the coming days.",
            "source_status": "User-entered",
        },
    )
    simulation = client.post(
        "/api/v1/simulations",
        json={
            "closure_severity": 0.6,
            "disruption_duration_days": 21,
            "alternative_route_capacity_ratio": 0.72,
            "n_runs": 1000,
            "random_seed": 20260720,
        },
    )
    portfolios = client.post(
        "/api/v1/portfolios",
        json={
            "refinery": "Jamnagar",
            "required_volume_bpd": 210000,
            "alternative_route_capacity_ratio": 0.72,
        },
    )
    brief = client.post("/api/v1/portfolios/BALANCED/brief")
    approval = client.post(
        "/api/v1/approvals/canonical",
        json={
            "decision": "APPROVED",
            "decided_by": "Demo Procurement Lead",
            "justification": "Approved for analyst-led commercial validation only; no purchase order is authorised.",
        },
    )

    assert signal.status_code == 201
    assert signal.json()["risk_scores"][0]["score"] >= 0.6
    assert simulation.status_code == 201
    assert simulation.json()["assumptions"]["n_runs"] == 1000
    assert portfolios.status_code == 201
    assert portfolios.json()["portfolios"][2]["label"] == "BALANCED"
    assert brief.status_code == 200
    assert brief.json()["provider_status"] == "Cached demo result"
    assert approval.status_code == 201
    assert approval.json()["execution_external"] is False

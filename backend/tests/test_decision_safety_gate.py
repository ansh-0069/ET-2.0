from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def _proposal(required_volume_bpd: int) -> dict:
    response = client.post(
        "/api/v1/workflows/propose",
        json={
            "text": "Shipping advisory reports tanker deviation and rising insurance premiums near Hormuz affecting India-bound crude cargoes.",
            "refinery": "Jamnagar",
            "required_volume_bpd": required_volume_bpd,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_standard_demo_clears_gate_with_visible_prototype_warnings(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposal = _proposal(210_000)

    response = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={
            "analyst_confirmed": True,
            "analyst_name": "Safety Gate Demo Analyst",
            "assumptions": proposal["proposed_assumptions"],
        },
    )

    assert response.status_code == 200
    workflow = response.json()
    gate = workflow["decision_safety_gate"]
    assert workflow["status"] == "COMPLETED"
    assert gate["status"] == "CLEARED"
    assert gate["decision"] == "RECOMMENDATION_READY"
    assert workflow["recommendation_id"] is not None
    assert workflow["portfolios"] is not None
    assert not gate["blockers"]
    checks = {check["check_id"]: check for check in gate["checks"]}
    assert checks["SOURCE_PROVENANCE"]["state"] == "WARNING"
    assert checks["SUPPLY_FEASIBILITY"]["state"] == "PASS"
    assert {source["source_status"] for source in checks["SOURCE_PROVENANCE"]["sources"]} >= {
        "User-entered",
        "Cached demo result",
        "Historical",
    }
    assert all(check["state"] != "BLOCKER" for check in gate["checks"])


def test_infeasible_demand_returns_no_recommendation_gate_even_with_finite_spr(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    proposal = _proposal(500_000)
    assumptions = proposal["proposed_assumptions"]
    assumptions.update(
        {
            "alternative_route_capacity_ratio": 0.72,
            "spr_bridge_opt_in": True,
            "government_authorization_assumed_for_scenario": True,
            "spr_bridge_duration_days": 7,
        }
    )

    response = client.post(
        f"/api/v1/workflows/{proposal['workflow_id']}/execute",
        json={
            "analyst_confirmed": True,
            "analyst_name": "Capacity Safety Reviewer",
            "assumptions": assumptions,
        },
    )

    assert response.status_code == 200
    workflow = response.json()
    gate = workflow["decision_safety_gate"]
    assert workflow["status"] == "BLOCKED"
    assert workflow["recommendation_id"] is None
    assert workflow["portfolios"] is None
    assert workflow["executive_brief"] is None
    assert workflow["transparency"] is None
    assert gate["status"] == "BLOCKED"
    assert gate["decision"] == "NO_RECOMMENDATION_YET"
    assert gate["blockers"]
    assert "No recommendation yet" in gate["summary"]
    supply_check = next(check for check in gate["checks"] if check["check_id"] == "SUPPLY_FEASIBILITY")
    assert supply_check["state"] == "BLOCKER"
    assert "shortfall" in supply_check["summary"]
    assert {source["source_status"] for source in supply_check["sources"]} >= {
        "User-entered",
        "Historical",
        "Simulated",
    }
    assert any("permitted finite scenario bridge" in action for action in supply_check["next_actions"])

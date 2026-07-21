from fastapi.testclient import TestClient

from petravigil.main import app


client = TestClient(app)


def test_default_multi_refinery_demo_enforces_one_global_capacity_ledger() -> None:
    """The showcase request is feasible but exposes US/Guyana route competition."""
    response = client.post("/api/v1/portfolios/multi-refinery")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "FEASIBLE"
    assert payload["decision"] == "ALLOCATION_READY"
    assert payload["data_status"] == "Simulated"
    assert payload["network_source_status"] == "Historical"
    assert payload["demand_source_status"] == "User-entered"
    assert payload["live_data_connected"] is False
    assert [item["refinery"] for item in payload["refinery_results"]] == ["Jamnagar", "Paradip", "Kochi"]
    assert all(item["unserved_volume_bpd"] == 0 for item in payload["refinery_results"])
    assert payload["spr_bridge_status"] == "NOT_MODELED"
    assert any("globally finite reserve" in item for item in payload["limitations"])

    route_ledger = {item["route"]: item for item in payload["shared_route_utilization"]}
    for route_name in ("US Gulf -> West India", "Guyana -> West India"):
        route = route_ledger[route_name]
        allocation_total = sum(
            allocation["volume_bpd"]
            for refinery in payload["refinery_results"]
            for allocation in refinery["allocations"]
            if allocation["route"] == route_name
        )
        assert allocation_total == route["allocated_capacity_bpd"]
        assert allocation_total <= route["effective_capacity_bpd"]
        assert route["route_capacity_source_status"] == "Historical"
        assert route["allocation_status"] == "Simulated"

    contention = {item["route"]: item for item in payload["cargo_contention"]}
    assert contention["US Gulf -> West India"]["status"] == "CONTESTED"
    assert set(contention["US Gulf -> West India"]["competing_refineries"]) == {"Jamnagar", "Kochi"}
    assert contention["US Gulf -> West India"]["scenario_requested_capacity_bpd"] > contention[
        "US Gulf -> West India"
    ]["effective_capacity_bpd"]
    assert contention["Guyana -> West India"]["status"] == "CONTESTED"
    assert set(contention["Guyana -> West India"]["competing_refineries"]) == {"Jamnagar", "Paradip"}


def test_infeasible_multi_refinery_request_returns_a_structured_shortfall() -> None:
    response = client.post(
        "/api/v1/portfolios/multi-refinery",
        json={
            "demand_lines": [
                {"refinery": "Jamnagar", "required_volume_bpd": 240_000},
                {"refinery": "Paradip", "required_volume_bpd": 90_000},
                {"refinery": "Kochi", "required_volume_bpd": 150_000},
            ],
            "alternative_route_capacity_ratio": 0.72,
            "disrupted_chokepoint": "HORMUZ",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "INFEASIBLE"
    assert payload["decision"] == "NO_RECOMMENDATION_YET"
    assert sum(item["unserved_volume_bpd"] for item in payload["refinery_results"]) > 0
    assert "not a procurement recommendation" in payload["rationale"]
    assert all(
        route["allocated_capacity_bpd"] <= route["effective_capacity_bpd"]
        for route in payload["shared_route_utilization"]
    )
    assert payload["execution_external"] is False


def test_multi_refinery_request_requires_at_least_two_distinct_demand_lines() -> None:
    response = client.post(
        "/api/v1/portfolios/multi-refinery",
        json={
            "demand_lines": [{"refinery": "Jamnagar", "required_volume_bpd": 120_000}],
            "alternative_route_capacity_ratio": 0.72,
        },
    )

    assert response.status_code == 422

"""Offline graph projection for the Phase 2 supply-network demo."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from petravigil.models import AlternativeRouteOption, DataStatus, NetworkSummary, RefineryProfile


NETWORK_PATH = Path(__file__).parents[1] / "data" / "supply_network.json"


class SupplyNetworkService:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.grades = {grade["name"]: grade for grade in payload["crude_grades"]}

    def summary(self) -> NetworkSummary:
        return NetworkSummary(
            countries=len(self.payload["countries"]),
            crude_grades=len(self.payload["crude_grades"]),
            refineries=len(self.payload["refineries"]),
            routes=len(self.payload["routes"]),
            chokepoints=len(self.payload["chokepoints"]),
            data_status=DataStatus(self.payload["data_status"]),
        )

    def refineries(self) -> list[RefineryProfile]:
        return [RefineryProfile.model_validate(item) for item in self.payload["refineries"]]

    def alternatives(self, refinery_name: str, disrupted_chokepoint: str) -> list[AlternativeRouteOption]:
        refinery = next((item for item in self.payload["refineries"] if item["name"] == refinery_name), None)
        if refinery is None:
            raise KeyError(refinery_name)

        options: list[AlternativeRouteOption] = []
        for grade_name in refinery["compatible_grades"]:
            grade = self.grades[grade_name]
            for route in self.payload["routes"]:
                if route["origin"] != grade["country"] or disrupted_chokepoint in route["chokepoints"]:
                    continue
                options.append(
                    AlternativeRouteOption(
                        option_id=f"ALT-{refinery_name[:3].upper()}-{grade_name[:3].upper()}-{len(options) + 1:02d}",
                        supplier_country=grade["country"],
                        crude_grade=grade_name,
                        refinery=refinery_name,
                        route=route["name"],
                        avoids_chokepoint=disrupted_chokepoint,
                        transit_days=route["transit_days"],
                        route_risk_score=route["risk_score"],
                        available_volume_bpd=route["available_volume_bpd"],
                        compatibility_note=(f"{grade_name} is in the seeded compatible crude diet for {refinery_name}."),
                        data_status=DataStatus(self.payload["data_status"]),
                    )
                )
        return sorted(options, key=lambda item: (item.route_risk_score, item.transit_days))


@lru_cache(maxsize=1)
def get_supply_network() -> SupplyNetworkService:
    with NETWORK_PATH.open(encoding="utf-8") as network_file:
        return SupplyNetworkService(json.load(network_file))

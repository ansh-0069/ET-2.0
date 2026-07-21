"""Global, source-labelled route allocator for a multi-refinery scenario.

The single-refinery portfolio API deliberately treats capacity as local to one
refinery. This service is separate because a physical cargo route is a shared
constraint: once its scaled seeded capacity is allocated to one refinery, that
same capacity is unavailable to every other refinery in the scenario.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from uuid import uuid4

from ortools.linear_solver import pywraplp

from petravigil.models import (
    AlternativeRouteOption,
    CargoContentionParticipant,
    CargoContentionRecord,
    DataStatus,
    MultiRefineryAllocation,
    MultiRefineryPortfolioRequest,
    MultiRefineryPortfolioResponse,
    MultiRefineryProvenance,
    MultiRefineryResultLine,
    SharedRouteUtilization,
)
from petravigil.services.supply_network import SupplyNetworkService


# Historical seed prices are used only to make equal-volume simulated
# allocations deterministic. They are not live market quotes or executable
# offers, and no commercial terms are inferred from them.
PRICE_BY_GRADE = {"WTI Midland": 83.2, "Liza Light": 81.8, "Bonny Light": 82.4}
_VOLUME_PRIORITY = 1_000_000


class MultiRefineryPortfolioAllocator:
    """Allocate seeded compatible supply without double-booking physical routes."""

    def __init__(self, network: SupplyNetworkService) -> None:
        self.network = network

    def generate(self, request: MultiRefineryPortfolioRequest) -> MultiRefineryPortfolioResponse:
        options_by_refinery: list[list[AlternativeRouteOption]] = []
        route_metadata: dict[str, AlternativeRouteOption] = {}

        for demand_line in request.demand_lines:
            try:
                options = self.network.alternatives(demand_line.refinery, request.disrupted_chokepoint)
            except KeyError:
                # An unknown refinery is deliberately represented in the
                # non-feasible result rather than becoming an opaque 500/404.
                options = []
            options_by_refinery.append(options)
            for option in options:
                existing = route_metadata.get(option.route)
                if existing is not None and (
                    existing.available_volume_bpd != option.available_volume_bpd
                    or existing.transit_days != option.transit_days
                    or existing.route_risk_score != option.route_risk_score
                ):
                    raise RuntimeError(f"inconsistent seeded metadata for shared route: {option.route}")
                route_metadata.setdefault(option.route, option)

        effective_capacity = {
            route: round(option.available_volume_bpd * request.alternative_route_capacity_ratio)
            for route, option in route_metadata.items()
        }
        allocations_by_slot = self._solve(request, options_by_refinery, effective_capacity)

        refinery_results = self._refinery_results(request, options_by_refinery, allocations_by_slot)
        shared_route_utilization = self._route_utilization(
            request,
            route_metadata,
            effective_capacity,
            options_by_refinery,
            allocations_by_slot,
        )
        cargo_contention = self._cargo_contention(
            request,
            effective_capacity,
            options_by_refinery,
            allocations_by_slot,
        )

        has_unserved_volume = any(line.unserved_volume_bpd > 0 for line in refinery_results)
        status = "INFEASIBLE" if has_unserved_volume else "FEASIBLE"
        decision = "NO_RECOMMENDATION_YET" if has_unserved_volume else "ALLOCATION_READY"
        served_volume = sum(line.allocated_volume_bpd for line in refinery_results)
        requested_volume = sum(line.requested_volume_bpd for line in refinery_results)
        contention_routes = ", ".join(record.route for record in cargo_contention) or "none"
        rationale = (
            f"The local solver allocated {served_volume:,} of {requested_volume:,} bpd while enforcing one "
            f"global scaled-capacity constraint per physical route. Shared-route contention is recorded for: "
            f"{contention_routes}."
        )
        if has_unserved_volume:
            rationale += " Unserved demand makes this a capacity shortfall, not a procurement recommendation."
        demand_source_status = (
            DataStatus.SIMULATED
            if any(line.source_status == DataStatus.SIMULATED for line in request.demand_lines)
            else DataStatus.USER_ENTERED
        )
        demand_detail = (
            "At least one refinery demand line is a local simulated scenario tranche; the remaining lines may be analyst-entered assumptions. "
            "None are purchase requests or verified operating data."
            if demand_source_status == DataStatus.SIMULATED
            else "Demand lines and alternative-route capacity ratio are analyst-entered scenario assumptions; they are not purchase requests or verified operating data."
        )

        return MultiRefineryPortfolioResponse(
            allocation_id=f"MR-PORT-{str(uuid4()).upper()}",
            created_at=datetime.now(timezone.utc),
            status=status,
            decision=decision,
            demand_source_status=demand_source_status,
            request=request,
            refinery_results=refinery_results,
            shared_route_utilization=shared_route_utilization,
            cargo_contention=cargo_contention,
            provenance=[
                MultiRefineryProvenance(
                    label="Scenario demand lines and capacity ratio",
                    source_status=demand_source_status,
                    detail=demand_detail,
                ),
                MultiRefineryProvenance(
                    label="Seeded compatibility and route capacity network",
                    source_status=DataStatus.HISTORICAL,
                    detail=(
                        "Refinery-grade compatibility, route risk, transit time, and capacity come from the local "
                        "historical seed network and have no live operational refresh."
                    ),
                ),
                MultiRefineryProvenance(
                    label="Global cargo allocation",
                    source_status=DataStatus.SIMULATED,
                    detail=(
                        "Allocation and contention records are deterministic local solver output, not supplier offers, "
                        "booked cargoes, or logistics instructions."
                    ),
                ),
            ],
            limitations=[
                "No live AIS, tanker availability, port congestion, sanctions, insurance, price, or supplier-offer feed is connected.",
                "Historical seeded route capacities are scaled by the analyst-entered scenario ratio and must be commercially validated before use.",
                "SPR is intentionally not modelled here because this multi-refinery endpoint has no globally finite reserve allocation constraint; it cannot sum a bridge independently per refinery.",
                "This output does not execute, authorize, reserve, or redirect any cargo and requires human review before any external action.",
            ],
            rationale=rationale,
        )

    @staticmethod
    def _create_solver() -> pywraplp.Solver:
        """Use integer capacities so a shared route cannot be oversold by rounding."""

        for solver_name in ("SCIP", "CBC_MIXED_INTEGER_PROGRAMMING"):
            solver = pywraplp.Solver.CreateSolver(solver_name)
            if solver is not None:
                return solver
        raise RuntimeError("An integer optimisation solver is unavailable")

    def _solve(
        self,
        request: MultiRefineryPortfolioRequest,
        options_by_refinery: list[list[AlternativeRouteOption]],
        effective_capacity: dict[str, int],
    ) -> dict[tuple[int, int], int]:
        solver = self._create_solver()
        variables: dict[tuple[int, int], pywraplp.Variable] = {}

        for refinery_index, options in enumerate(options_by_refinery):
            for option_index, option in enumerate(options):
                variables[(refinery_index, option_index)] = solver.IntVar(
                    0,
                    effective_capacity[option.route],
                    f"allocation_{refinery_index}_{option_index}",
                )

        for refinery_index, demand_line in enumerate(request.demand_lines):
            refinery_variables = [
                variables[(refinery_index, option_index)]
                for option_index in range(len(options_by_refinery[refinery_index]))
            ]
            if refinery_variables:
                solver.Add(solver.Sum(refinery_variables) <= demand_line.required_volume_bpd)

        for route, capacity in effective_capacity.items():
            route_variables = [
                variable
                for (refinery_index, option_index), variable in variables.items()
                if options_by_refinery[refinery_index][option_index].route == route
            ]
            if route_variables:
                solver.Add(solver.Sum(route_variables) <= capacity)

        objective = solver.Objective()
        for (refinery_index, option_index), variable in variables.items():
            option = options_by_refinery[refinery_index][option_index]
            # Allocate as much compatible supply as possible first. Price and
            # route risk only select among equal-volume feasible scenarios.
            seeded_cost = PRICE_BY_GRADE.get(option.crude_grade, 84.0)
            tie_breaker = int(round((seeded_cost + option.route_risk_score * 5) * 100))
            objective.SetCoefficient(variable, _VOLUME_PRIORITY - tie_breaker)
        objective.SetMaximization()

        solve_status = solver.Solve()
        if solve_status != pywraplp.Solver.OPTIMAL:
            raise RuntimeError("The multi-refinery allocation solver did not return an optimal local scenario")

        allocations: dict[tuple[int, int], int] = {}
        for key, variable in variables.items():
            # The solver uses integer variables. Rounding only protects the
            # API contract from a negligible numerical display artefact.
            allocations[key] = max(0, int(round(variable.solution_value())))

        for route, capacity in effective_capacity.items():
            route_total = sum(
                volume
                for (refinery_index, option_index), volume in allocations.items()
                if options_by_refinery[refinery_index][option_index].route == route
            )
            if route_total > capacity:
                raise RuntimeError(f"global route capacity invariant failed for {route}")
        return allocations

    def _refinery_results(
        self,
        request: MultiRefineryPortfolioRequest,
        options_by_refinery: list[list[AlternativeRouteOption]],
        allocations_by_slot: dict[tuple[int, int], int],
    ) -> list[MultiRefineryResultLine]:
        results: list[MultiRefineryResultLine] = []
        seeded_refinery_names = {profile.name for profile in self.network.refineries()}
        for refinery_index, demand_line in enumerate(request.demand_lines):
            allocations: list[MultiRefineryAllocation] = []
            for option_index, option in enumerate(options_by_refinery[refinery_index]):
                volume = allocations_by_slot.get((refinery_index, option_index), 0)
                if volume:
                    allocations.append(
                        MultiRefineryAllocation(
                            refinery=demand_line.refinery,
                            supplier_country=option.supplier_country,
                            crude_grade=option.crude_grade,
                            route=option.route,
                            volume_bpd=volume,
                            cost_usd_per_bbl=PRICE_BY_GRADE.get(option.crude_grade, 84.0),
                            route_risk_score=option.route_risk_score,
                        )
                    )
            allocations.sort(key=lambda item: (item.cost_usd_per_bbl, item.route, item.crude_grade))
            allocated = sum(item.volume_bpd for item in allocations)
            unserved = demand_line.required_volume_bpd - allocated
            if demand_line.refinery not in seeded_refinery_names:
                fulfillment_status = "UNKNOWN_REFINERY"
                note = (
                    f"{demand_line.refinery} is not present in the local seeded refinery network, so no compatible "
                    "route allocation was attempted."
                )
            elif allocated == demand_line.required_volume_bpd:
                fulfillment_status = "FULLY_ALLOCATED"
                note = "Demand is fully covered by seeded compatible routes under the shared global capacity constraints."
            elif allocated:
                fulfillment_status = "PARTIALLY_ALLOCATED"
                note = "Only part of demand fits within the shared seeded route capacities; the residual remains unserved."
            else:
                fulfillment_status = "UNSERVED"
                note = "No compatible seeded route capacity remains for this refinery under the requested scenario."
            results.append(
                MultiRefineryResultLine(
                    refinery=demand_line.refinery,
                    requested_volume_bpd=demand_line.required_volume_bpd,
                    allocated_volume_bpd=allocated,
                    unserved_volume_bpd=unserved,
                    fulfillment_status=fulfillment_status,
                    compatible_route_count=len(options_by_refinery[refinery_index]),
                    allocations=allocations,
                    demand_source_status=demand_line.source_status,
                    note=note,
                )
            )
        return results

    @staticmethod
    def _route_utilization(
        request: MultiRefineryPortfolioRequest,
        route_metadata: dict[str, AlternativeRouteOption],
        effective_capacity: dict[str, int],
        options_by_refinery: list[list[AlternativeRouteOption]],
        allocations_by_slot: dict[tuple[int, int], int],
    ) -> list[SharedRouteUtilization]:
        utilization: list[SharedRouteUtilization] = []
        for route, option in route_metadata.items():
            allocated = sum(
                volume
                for (refinery_index, option_index), volume in allocations_by_slot.items()
                if options_by_refinery[refinery_index][option_index].route == route
            )
            utilization.append(
                SharedRouteUtilization(
                    route=route,
                    supplier_country=option.supplier_country,
                    seed_capacity_bpd=option.available_volume_bpd,
                    alternative_route_capacity_ratio=request.alternative_route_capacity_ratio,
                    effective_capacity_bpd=effective_capacity[route],
                    allocated_capacity_bpd=allocated,
                    remaining_capacity_bpd=effective_capacity[route] - allocated,
                    transit_days=option.transit_days,
                    route_risk_score=option.route_risk_score,
                )
            )
        return sorted(utilization, key=lambda item: (item.route, item.supplier_country))

    @staticmethod
    def _cargo_contention(
        request: MultiRefineryPortfolioRequest,
        effective_capacity: dict[str, int],
        options_by_refinery: list[list[AlternativeRouteOption]],
        allocations_by_slot: dict[tuple[int, int], int],
    ) -> list[CargoContentionRecord]:
        eligible_refineries_by_route: dict[str, list[int]] = defaultdict(list)
        for refinery_index, options in enumerate(options_by_refinery):
            for route in {option.route for option in options}:
                eligible_refineries_by_route[route].append(refinery_index)

        records: list[CargoContentionRecord] = []
        for route, refinery_indexes in eligible_refineries_by_route.items():
            if len(refinery_indexes) < 2:
                continue
            participants: list[CargoContentionParticipant] = []
            for refinery_index in refinery_indexes:
                demand = request.demand_lines[refinery_index]
                allocated = sum(
                    volume
                    for (allocation_refinery_index, option_index), volume in allocations_by_slot.items()
                    if allocation_refinery_index == refinery_index
                    and options_by_refinery[allocation_refinery_index][option_index].route == route
                )
                # This is a transparent counterfactual: the amount each
                # compatible refinery could try to place on this one route if
                # it sought to cover as much of its demand there as possible.
                scenario_requested = min(demand.required_volume_bpd, effective_capacity[route])
                participants.append(
                    CargoContentionParticipant(
                        refinery=demand.refinery,
                        scenario_requested_volume_bpd=scenario_requested,
                        allocated_volume_bpd=allocated,
                        demand_source_status=demand.source_status,
                    )
                )
            requested = sum(item.scenario_requested_volume_bpd for item in participants)
            allocated = sum(item.allocated_volume_bpd for item in participants)
            contested = requested > effective_capacity[route]
            records.append(
                CargoContentionRecord(
                    route=route,
                    competing_refineries=[item.refinery for item in participants],
                    scenario_requested_capacity_bpd=requested,
                    effective_capacity_bpd=effective_capacity[route],
                    allocated_capacity_bpd=allocated,
                    status="CONTESTED" if contested else "SHARED_WITH_HEADROOM",
                    participants=participants,
                    note=(
                        "Counterfactual compatible scenario demand exceeds the shared seeded route capacity; "
                        "the solver therefore applies one global capacity ledger rather than allocating the route per refinery."
                        if contested
                        else "More than one refinery can use this seeded physical route, but their counterfactual scenario demand remains within its scaled capacity."
                    ),
                )
            )
        return sorted(records, key=lambda item: item.route)

"""Gemini integrations with explicit, deterministic demo fallbacks."""

from __future__ import annotations

import json
import os
import re

import httpx

from petravigil.models import (
    DataStatus,
    GeminiExplanationResponse,
    GeminiSignalProposal,
    GeminiSignalResponse,
)


DEFAULT_MODEL = "gemini-2.5-flash"
DISCLAIMER = "Gemini output is an unverified proposal. Costs, volumes, legal status, and executable actions remain deterministic backend decisions."


# The offline fallback may only name an entity when the submitted text contains
# one of its explicit aliases.  These are deliberately narrow: they are not a
# geography or event-inference model.
FALLBACK_COUNTRY_ALIASES: dict[str, tuple[str, ...]] = {
    "Iraq": ("iraq", "iraqi"),
    "Saudi Arabia": ("saudi arabia", "saudi"),
    "United Arab Emirates": ("united arab emirates", "uae", "emirati"),
    "United States": ("united states", "u.s.", "us", "american"),
    "Guyana": ("guyana", "guyanese"),
    "Nigeria": ("nigeria", "nigerian"),
    "Iran": ("iran", "iranian"),
    "India": ("india", "indian"),
}
FALLBACK_CHOKEPOINT_ALIASES: dict[str, tuple[str, ...]] = {
    "HORMUZ": ("hormuz", "strait of hormuz"),
    "BAB_EL_MANDEB": ("bab el-mandeb", "bab el mandeb", "bab-al-mandab"),
    "SUEZ": ("suez", "suez canal"),
    "MALACCA": ("malacca", "strait of malacca"),
    "CAPE_OF_GOOD_HOPE": ("cape of good hope",),
}


def _contains_alias(text: str, alias: str) -> bool:
    """Return true only for a whole-word textual mention, never an inference."""
    return re.search(rf"(?<!\\w){re.escape(alias)}(?!\\w)", text, flags=re.IGNORECASE) is not None


def _matched_entities(text: str, aliases: dict[str, tuple[str, ...]]) -> list[str]:
    return [canonical for canonical, terms in aliases.items() if any(_contains_alias(text, term) for term in terms)]


class GeminiService:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

    async def extract_signal(self, text: str) -> GeminiSignalResponse:
        if not self.api_key:
            return GeminiSignalResponse(
                provider_status=DataStatus.CACHED_DEMO_RESULT,
                model="offline-demo-fallback",
                proposal=self._fallback_signal(text),
                disclaimer=DISCLAIMER,
            )

        prompt = (
            "Analyze this unverified input for India crude-oil supply-chain relevance. "
            "Return JSON only with energy_relevant, event_type, severity (1-10), confidence (0-1), "
            "affected_countries, affected_chokepoints, time_horizon (IMMEDIATE/DAYS/WEEKS/MONTHS), "
            "summary, evidence_note. Do not invent facts; mark uncertainty in evidence_note.\n\nINPUT:\n"
            + text
        )
        try:
            payload = await self._generate_json(prompt)
            return GeminiSignalResponse(
                provider_status=DataStatus.LIVE_API,
                model=self.model,
                proposal=GeminiSignalProposal.model_validate(payload),
                disclaimer=DISCLAIMER,
            )
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
            return GeminiSignalResponse(
                provider_status=DataStatus.CACHED_DEMO_RESULT,
                model="offline-demo-fallback",
                proposal=self._fallback_signal(text),
                disclaimer=DISCLAIMER,
            )

    async def explain_recommendation(self, supplier: str, grade: str, refinery: str, route: str) -> GeminiExplanationResponse:
        if not self.api_key:
            return self._fallback_explanation(supplier, grade, refinery, route)

        prompt = (
            "Explain the following deterministic procurement recommendation to a decision-maker. "
            "Do not create new prices, legal claims, or capacities. Return JSON only with explanation, "
            "risks (1-4 short strings), and next_question.\n"
            f"Supplier: {supplier}; Grade: {grade}; Refinery: {refinery}; Route: {route}."
        )
        try:
            payload = await self._generate_json(prompt)
            return GeminiExplanationResponse(
                provider_status=DataStatus.LIVE_API,
                model=self.model,
                **payload,
            )
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
            return self._fallback_explanation(supplier, grade, refinery, route)

    async def _generate_json(self, prompt: str) -> dict:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
        }
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(url, params={"key": self.api_key}, json=request_body)
            response.raise_for_status()
        response_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(response_text)

    @staticmethod
    def _fallback_signal(text: str) -> GeminiSignalProposal:
        relevant_terms = ("crude", "oil", "tanker", "shipping", "vessel", "hormuz", "refinery", "sanction", "port", "pipeline")
        lowered_text = text.casefold()
        if not any(term in lowered_text for term in relevant_terms):
            return GeminiSignalProposal(
                energy_relevant=False,
                event_type="UNCLASSIFIED",
                severity=1.0,
                confidence=0.25,
                affected_countries=[],
                affected_chokepoints=[],
                time_horizon="DAYS",
                summary="Cached demo extraction: the submitted text cannot be linked to an energy supply-chain disruption from the available offline evidence.",
                evidence_note="No GEMINI_API_KEY is configured. The offline fallback will not invent a corridor, country, or disruption event for unrelated text.",
            )

        countries = _matched_entities(text, FALLBACK_COUNTRY_ALIASES)
        chokepoints = _matched_entities(text, FALLBACK_CHOKEPOINT_ALIASES)
        if not chokepoints:
            return GeminiSignalProposal(
                energy_relevant=True,
                event_type="UNCLASSIFIED",
                severity=3.0,
                confidence=0.3,
                affected_countries=countries,
                affected_chokepoints=[],
                time_horizon="DAYS",
                summary=(
                    "Cached demo extraction: the submitted text is energy-related, but it does not explicitly "
                    "name a seeded chokepoint. No disruption corridor is proposed."
                ),
                evidence_note=(
                    "No GEMINI_API_KEY is configured. The offline fallback only returns countries and "
                    "chokepoints explicitly mentioned in the submitted text; it will not infer Hormuz or a route."
                ),
            )
        return GeminiSignalProposal(
            energy_relevant=True,
            event_type="SHIPPING_DISRUPTION",
            severity=7.4,
            confidence=0.68,
            affected_countries=countries,
            affected_chokepoints=chokepoints,
            time_horizon="DAYS",
            summary=f"Cached demo extraction: the submitted text may indicate shipping disruption relevant to Indian crude imports. Input preview: {text[:140]}",
            evidence_note=(
                "No GEMINI_API_KEY is configured. This deterministic fallback returns only entities explicitly "
                "matched in the submitted text and is not a live model result."
            ),
        )

    def _fallback_explanation(self, supplier: str, grade: str, refinery: str, route: str) -> GeminiExplanationResponse:
        return GeminiExplanationResponse(
            provider_status=DataStatus.CACHED_DEMO_RESULT,
            model="offline-demo-fallback",
            explanation=(f"{grade} from {supplier} is presented as an alternative for {refinery} because the seeded network marks the grade compatible and {route} avoids the active disruption path."),
            risks=["Longer transit time than Persian Gulf supply.", "Seeded capacity must be confirmed commercially.", "The route and insurance risk can change quickly."],
            next_question="Would you like to compare this option with a lower-cost or higher-resilience portfolio?",
        )

    async def explain_portfolio(self, label: str, rationale: str) -> GeminiExplanationResponse:
        if not self.api_key:
            return GeminiExplanationResponse(provider_status=DataStatus.CACHED_DEMO_RESULT, model="offline-demo-fallback", explanation=f"{label.replace('_', ' ').title()} is a deterministic portfolio generated from seeded compatible routes. {rationale}", risks=["Seeded supplier capacity requires commercial confirmation.", "Route-risk conditions can shift after the simulation.", "Final procurement requires human approval."], next_question="Which trade-off matters more now: lower landed cost or lower corridor exposure?")
        prompt = f"Explain this procurement portfolio in concise executive language. Do not add facts. Return JSON with explanation, risks (1-4), next_question. Portfolio: {label}. Rationale: {rationale}"
        try:
            payload = await self._generate_json(prompt)
            return GeminiExplanationResponse(provider_status=DataStatus.LIVE_API, model=self.model, **payload)
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
            return GeminiExplanationResponse(provider_status=DataStatus.CACHED_DEMO_RESULT, model="offline-demo-fallback", explanation=f"{label.replace('_', ' ').title()} is a deterministic portfolio generated from seeded compatible routes. {rationale}", risks=["Seeded supplier capacity requires commercial confirmation.", "Route-risk conditions can shift after the simulation.", "Final procurement requires human approval."], next_question="Which trade-off matters more now: lower landed cost or lower corridor exposure?")


def get_gemini_service() -> GeminiService:
    return GeminiService()

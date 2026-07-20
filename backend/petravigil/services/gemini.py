"""Gemini integrations with explicit, deterministic demo fallbacks."""

from __future__ import annotations

import json
import os

import httpx

from petravigil.models import (
    DataStatus,
    GeminiExplanationResponse,
    GeminiSignalProposal,
    GeminiSignalResponse,
)


DEFAULT_MODEL = "gemini-2.5-flash"
DISCLAIMER = "Gemini output is an unverified proposal. Costs, volumes, legal status, and executable actions remain deterministic backend decisions."


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
        return GeminiSignalProposal(
            energy_relevant=True,
            event_type="SHIPPING_DISRUPTION",
            severity=7.4,
            confidence=0.68,
            affected_countries=["Iran", "India"],
            affected_chokepoints=["HORMUZ"],
            time_horizon="DAYS",
            summary=f"Cached demo extraction: the submitted text may indicate shipping disruption relevant to Indian crude imports. Input preview: {text[:140]}",
            evidence_note="No GEMINI_API_KEY is configured, so this is a deterministic showcase fallback rather than a live model result.",
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

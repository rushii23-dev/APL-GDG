"""
Captain Cool — sequential multi-agent orchestration pipeline.
Analyst (with tools) → Pressure Architect → Strategist (Captain's mandate).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from google import genai

from agents import (
    AGENT_ANALYST,
    AGENT_PRESSURE_ARCHITECT,
    AGENT_STRATEGIST,
    MODEL_ID,
    AgentInvocationError,
    create_genai_client,
    run_agent,
)
from tools import (
    ANALYST_GEMINI_TOOLS,
    MatchState,
    build_analyst_user_prompt,
    build_pressure_architect_user_prompt,
    build_strategist_user_prompt,
    match_state_from_dict,
)

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Full pipeline output from Captain Cool."""

    match_snapshot: str
    analyst_audit: str
    pressure_audit: str
    strategist_mandate: str
    model: str = MODEL_ID
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_snapshot": self.match_snapshot,
            "analyst_audit": self.analyst_audit,
            "pressure_audit": self.pressure_audit,
            "strategist_mandate": self.strategist_mandate,
            "model": self.model,
            "errors": self.errors,
        }


class CaptainCoolOrchestrator:
    """
    Runs the three-agent IPL strategy pipeline using gemini-3.1-flash-lite.
    """

    def __init__(
        self,
        client: Optional[genai.Client] = None,
        *,
        api_key: Optional[str] = None,
        model: str = MODEL_ID,
    ) -> None:
        self._owns_client = client is None
        self.client = client or create_genai_client(api_key=api_key)
        self.model = model

    def close(self) -> None:
        if self._owns_client and self.client is not None:
            try:
                self.client.close()
            except Exception:
                logger.debug("Client close suppressed", exc_info=True)

    def __enter__(self) -> "CaptainCoolOrchestrator":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def run(self, state: MatchState) -> StrategyResult:
        """
        Execute the full Analyst → Architect → Strategist chain.

        Args:
            state: Normalized live match state.

        Returns:
            StrategyResult with all agent outputs; partial results on soft failures.
        """
        from tools import format_match_state_snapshot

        snapshot = format_match_state_snapshot(state)
        errors: list[str] = []
        analyst_audit = ""
        pressure_audit = ""
        strategist_mandate = ""

        try:
            analyst_audit = run_agent(
                self.client,
                AGENT_ANALYST,
                build_analyst_user_prompt(state),
                model=self.model,
                tools=ANALYST_GEMINI_TOOLS,
            )
        except AgentInvocationError as exc:
            logger.error("Analyst agent failed: %s", exc)
            errors.append(f"Data Analyst: {exc}")
            analyst_audit = (
                "### 📊 Data Analyst Audit\n"
                "- **Match Situation Summary**: Analysis unavailable (API error).\n"
                "- **Venue & Pitch Data**: Refer to raw match snapshot.\n"
                "- **Crucial Match-ups**: Unable to compute — check API key and connectivity."
            )

        try:
            pressure_audit = run_agent(
                self.client,
                AGENT_PRESSURE_ARCHITECT,
                build_pressure_architect_user_prompt(state),
                model=self.model,
            )
        except AgentInvocationError as exc:
            logger.error("Pressure architect failed: %s", exc)
            errors.append(f"Momentum Architect: {exc}")
            pressure_audit = (
                "### 🔥 Psychological Momentum Audit\n"
                "- **The Fear Metric**: Unavailable.\n"
                "- **The Choke Factor**: Unavailable.\n"
                "- **Mental Warfare Tactic**: Re-assess manually from run-rate pressure."
            )

        try:
            strategist_mandate = run_agent(
                self.client,
                AGENT_STRATEGIST,
                build_strategist_user_prompt(state, analyst_audit, pressure_audit),
                model=self.model,
            )
        except AgentInvocationError as exc:
            logger.error("Strategist failed: %s", exc)
            errors.append(f"Strategist: {exc}")
            strategist_mandate = (
                "### 🏆 STRATEGIST'S FINAL MANDATE\n"
                "- **PROPOSED MOVE**: Hold nerve — default to best death bowler on stump line.\n"
                "- **TACTICAL RATIONALE**: Automated mandate failed; fall back to field balance.\n"
                "- **COUNTERFACTUAL ANALYSIS**: Delay risks free hits under rising RRR."
            )

        return StrategyResult(
            match_snapshot=snapshot,
            analyst_audit=analyst_audit,
            pressure_audit=pressure_audit,
            strategist_mandate=strategist_mandate,
            model=self.model,
            errors=errors,
        )

    def run_from_dict(self, payload: dict[str, Any]) -> StrategyResult:
        """Convenience wrapper for UI / API JSON payloads."""
        return self.run(match_state_from_dict(payload))


def run_captain_cool_strategy(
    match_payload: dict[str, Any],
    *,
    api_key: Optional[str] = None,
) -> StrategyResult:
    """
    One-shot entry point for app.py and external callers.

    Args:
        match_payload: Dict compatible with match_state_from_dict().
        api_key: Optional Gemini API key override.

    Returns:
        StrategyResult from the full pipeline.
    """
    with CaptainCoolOrchestrator(api_key=api_key) as orchestrator:
        return orchestrator.run_from_dict(match_payload)

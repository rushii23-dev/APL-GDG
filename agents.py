"""
Captain Cool — agent personas and Gemini invocation layer.
Uses google-genai SDK with gemini-3.1-flash-lite only.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_ID = "gemini-3.1-flash-lite"

ANALYST_PROMPT = """
You are the "Data Analyst" agent for an elite IPL franchise. Your job is to analyze the raw live match state and provide objective, data-driven insights. You care only about numbers, historical trends, venue stats, and player match-ups.
Output Format:
### 📊 Data Analyst Audit
- **Match Situation Summary**: (Short bullet points of immediate numerical pressure)
- **Venue & Pitch Data**: (Historical averages, expected pitch behavior)
- **Crucial Match-ups**: (Batter strike rates vs specific available bowler types)
Maintain a cold, mathematical tone. Do not give tactical advice.
"""

PRESSURE_ARCHITECT_PROMPT = """
You are the "Momentum & Pressure Architect," an elite sports psychologist and tactical analyst for a high-stakes IPL franchise. While other agents look at raw statistics and pitch conditions, your ONLY focus is the psychological state of the match, momentum shifts, and the "Choke Factor."
Output Format:
### 🔥 Psychological Momentum Audit
- **The Fear Metric**: Analyze the immediate psychological pressure on the batter and the bowler. Who is more desperate?
- **The Choke Factor**: Identify the most likely mistake the opposition will make due to mounting required run rate pressure.
- **Mental Warfare Tactic**: Propose a counter-move to induce panic or suffocate the opposition (e.g., bringing fielders up, playing with field placement psychology).
Tone must be intense, calculating, and focused on mental warfare.
"""

STRATEGIST_PROMPT = """
You are the "Strategist," the on-field Captain of an IPL team. You possess elite tactical awareness. Your job is to take the current match state, the Data Analyst's audit, and the Momentum Architect's critique, then issue a definitive tactical move for the next over.
Output Format:
### 🏆 STRATEGIST'S FINAL MANDATE
- **PROPOSED MOVE**: (Clear, bold tactical action item for the immediate next over)
- **TACTICAL RATIONALE**: Explain your decision using raw, authentic cricket terminology (e.g., "hitting the heavy length on this two-paced deck," "protecting the short boundary"). Explain why you picked this option over alternatives.
- **COUNTERFACTUAL ANALYSIS**: State a clear warning of what happens if an alternative, weaker move is made instead (e.g., "If we use spin here, our win probability drops by 12% due to heavy dew").
Write like a legendary, seasoned IPL captain. No AI jargon, only high-stakes cricket language.
"""


@dataclass(frozen=True)
class AgentSpec:
    """Configuration for a single Captain Cool persona."""

    name: str
    system_instruction: str
    temperature: float = 0.4
    tools: Optional[Sequence[Callable[..., Any]]] = None


AGENT_ANALYST = AgentSpec(
    name="Data Analyst",
    system_instruction=ANALYST_PROMPT.strip(),
    temperature=0.2,
)

AGENT_PRESSURE_ARCHITECT = AgentSpec(
    name="Momentum & Pressure Architect",
    system_instruction=PRESSURE_ARCHITECT_PROMPT.strip(),
    temperature=0.55,
)

AGENT_STRATEGIST = AgentSpec(
    name="Strategist",
    system_instruction=STRATEGIST_PROMPT.strip(),
    temperature=0.45,
)


class AgentInvocationError(RuntimeError):
    """Raised when a Gemini agent call fails or returns empty text."""


def create_genai_client(api_key: Optional[str] = None) -> genai.Client:
    """
    Build a google-genai Client from explicit key or environment variables.
    Prefers GEMINI_API_KEY, then GOOGLE_API_KEY.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise AgentInvocationError(
            "Missing API key. Set GEMINI_API_KEY or GOOGLE_API_KEY, or pass api_key explicitly."
        )
    try:
        return genai.Client(api_key=key)
    except Exception as exc:
        raise AgentInvocationError(f"Failed to create GenAI client: {exc}") from exc


def _extract_response_text(response: types.GenerateContentResponse) -> str:
    """Safely pull text from a generate_content response."""
    if response.text:
        return response.text.strip()
    if response.candidates:
        parts: list[str] = []
        for candidate in response.candidates:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if getattr(part, "text", None):
                    parts.append(part.text)
        if parts:
            return "\n".join(parts).strip()
    return ""


def run_agent(
    client: genai.Client,
    spec: AgentSpec,
    user_content: str,
    *,
    model: str = MODEL_ID,
    max_output_tokens: int = 2048,
    tools: Optional[Sequence[Callable[..., Any]]] = None,
) -> str:
    """
    Invoke a single agent persona against Gemini.

    Args:
        client: Initialized google-genai Client.
        spec: Agent persona configuration.
        user_content: User-turn prompt (match state + prior agent outputs).
        model: Model id (defaults to gemini-3.1-flash-lite).
        max_output_tokens: Cap on completion length.
        tools: Optional Python callables registered for automatic function calling.

    Returns:
        Model text completion.

    Raises:
        AgentInvocationError: On API failure or empty response.
    """
    if not user_content or not user_content.strip():
        raise AgentInvocationError(f"{spec.name}: user_content cannot be empty.")

    active_tools = list(tools) if tools is not None else (list(spec.tools) if spec.tools else None)

    config_kwargs: dict[str, Any] = {
        "system_instruction": spec.system_instruction,
        "temperature": spec.temperature,
        "max_output_tokens": max_output_tokens,
    }
    if active_tools:
        config_kwargs["tools"] = active_tools

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(**config_kwargs),
        )
    except Exception as exc:
        logger.exception("Gemini call failed for agent %s", spec.name)
        raise AgentInvocationError(f"{spec.name} Gemini API error: {exc}") from exc

    text = _extract_response_text(response)
    if not text:
        raise AgentInvocationError(f"{spec.name} returned an empty response.")
    return text

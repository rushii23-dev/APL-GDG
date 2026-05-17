"""
Captain Cool — structured cricket intelligence tools for live IPL strategy.
Exposed as Python functions for Gemini automatic function calling.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Curated reference data (demo-grade; replace with live feeds in production)
# ---------------------------------------------------------------------------

VENUE_STATS: dict[str, dict[str, Any]] = {
    "wankhede": {
        "display_name": "Wankhede Stadium, Mumbai",
        "avg_first_innings": 178,
        "avg_second_innings": 165,
        "death_overs_rr": 11.2,
        "powerplay_rr": 8.4,
        "short_boundary_m": 58,
        "long_boundary_m": 72,
        "pitch_type": "two-paced, favors cutters and hard-length seam",
        "dew_factor_late": "moderate after over 15",
        "spin_friendliness": "low-medium",
    },
    "chinnaswamy": {
        "display_name": "M. Chinnaswamy Stadium, Bengaluru",
        "avg_first_innings": 192,
        "avg_second_innings": 181,
        "death_overs_rr": 12.1,
        "powerplay_rr": 9.1,
        "short_boundary_m": 52,
        "long_boundary_m": 68,
        "pitch_type": "flat, high bounce, short square boundaries",
        "dew_factor_late": "low",
        "spin_friendliness": "medium",
    },
    "eden": {
        "display_name": "Eden Gardens, Kolkata",
        "avg_first_innings": 172,
        "avg_second_innings": 158,
        "death_overs_rr": 10.8,
        "powerplay_rr": 7.9,
        "short_boundary_m": 60,
        "long_boundary_m": 74,
        "pitch_type": "slowish deck, grips for spinners in middle overs",
        "dew_factor_late": "high after over 16",
        "spin_friendliness": "high",
    },
    "ahmedabad": {
        "display_name": "Narendra Modi Stadium, Ahmedabad",
        "avg_first_innings": 175,
        "avg_second_innings": 162,
        "death_overs_rr": 10.5,
        "powerplay_rr": 8.0,
        "short_boundary_m": 62,
        "long_boundary_m": 78,
        "pitch_type": "red-soil strip, variable bounce, long straight boundaries",
        "dew_factor_late": "moderate",
        "spin_friendliness": "medium-high",
    },
    "chepauk": {
        "display_name": "MA Chidambaram Stadium, Chennai",
        "avg_first_innings": 168,
        "avg_second_innings": 152,
        "death_overs_rr": 10.2,
        "powerplay_rr": 7.6,
        "short_boundary_m": 61,
        "long_boundary_m": 73,
        "pitch_type": "slow, low bounce, turn for spinners",
        "dew_factor_late": "high",
        "spin_friendliness": "very high",
    },
}

PLAYER_PROFILES: dict[str, dict[str, Any]] = {
    "rohit sharma": {
        "role": "RH batter",
        "ipl_sr": 130.2,
        "vs_pace_sr": 128.0,
        "vs_spin_sr": 134.5,
        "death_sr": 142.0,
        "weakness": "off-stump wide yorkers, early swing",
    },
    "virat kohli": {
        "role": "RH batter",
        "ipl_sr": 131.8,
        "vs_pace_sr": 135.0,
        "vs_spin_sr": 126.0,
        "death_sr": 138.5,
        "weakness": "leg-stump yorkers, extreme pace",
    },
    "jasprit bumrah": {
        "role": "RH pace",
        "ipl_economy": 7.45,
        "death_economy": 6.9,
        "yorker_pct": 0.42,
        "strength": "death yorkers, cross-seam slower balls",
    },
    "rashid khan": {
        "role": "leg-spin",
        "ipl_economy": 6.85,
        "middle_economy": 6.2,
        "wicket_prob_per_over": 0.18,
        "strength": "googly to RH batters, tight leg-stump line",
    },
    "rishabh pant": {
        "role": "LH batter",
        "ipl_sr": 145.0,
        "vs_pace_sr": 148.0,
        "vs_spin_sr": 138.0,
        "death_sr": 155.0,
        "weakness": "short ball into body early in innings",
    },
    "hardik pandya": {
        "role": "RH pace/allrounder",
        "ipl_economy": 8.9,
        "death_economy": 9.4,
        "yorker_pct": 0.22,
        "strength": "hard-length into pitch, short third-man trap",
    },
}


@dataclass
class MatchState:
    """Normalized live match snapshot for all agents."""

    innings: str  # "1st" or "2nd"
    batting_team: str
    bowling_team: str
    venue_key: str
    over: float
    balls_in_over: int
    runs: int
    wickets: int
    target: Optional[int] = None
    striker: str = ""
    non_striker: str = ""
    bowler: str = ""
    last_over_runs: int = 0
    last_over_wickets: int = 0
    available_bowlers: list[str] = field(default_factory=list)
    field_restrictions: str = "none"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize_key(name: str) -> str:
    return name.strip().lower()


def _resolve_venue_key(venue: str) -> str:
    key = _normalize_key(venue)
    if key in VENUE_STATS:
        return key
    for vk, data in VENUE_STATS.items():
        if key in vk or key in data["display_name"].lower():
            return vk
    return "wankhede"


def _resolve_player(name: str) -> Optional[dict[str, Any]]:
    key = _normalize_key(name)
    if key in PLAYER_PROFILES:
        return PLAYER_PROFILES[key]
    for pk, profile in PLAYER_PROFILES.items():
        if key in pk or pk in key:
            return profile
    return None


def get_venue_intelligence(venue: str) -> str:
    """
    Returns historical venue averages, boundary dimensions, and pitch behavior
    for the given IPL ground.

    Args:
        venue: Stadium name or internal key (e.g. 'wankhede', 'Eden Gardens').
    """
    vk = _resolve_venue_key(venue)
    data = VENUE_STATS[vk]
    return json.dumps({"venue_key": vk, **data}, indent=2)


def get_player_profile(player_name: str) -> str:
    """
    Returns IPL statistical profile for a batter or bowler including strike rates,
    economy, and known strengths/weaknesses.

    Args:
        player_name: Full or partial player name.
    """
    profile = _resolve_player(player_name)
    if profile is None:
        return json.dumps(
            {
                "player": player_name,
                "status": "not_in_database",
                "message": "No curated profile; infer from match context.",
            }
        )
    return json.dumps({"player": player_name, **profile}, indent=2)


def compute_pressure_metrics(
    runs: int,
    wickets: int,
    over: float,
    target: Optional[int] = None,
    innings: str = "2nd",
) -> str:
    """
    Computes required run rate, projected par score, and chase pressure index.

    Args:
        runs: Current innings runs.
        wickets: Wickets lost.
        over: Completed overs as decimal (e.g. 18.3).
        target: Chase target (second innings only).
        innings: '1st' or '2nd'.
    """
    balls_bowled = int(over) * 6 + round((over - int(over)) * 10)
    balls_remaining = max(120 - balls_bowled, 0)
    overs_remaining = balls_remaining / 6.0

    result: dict[str, Any] = {
        "innings": innings,
        "runs": runs,
        "wickets": wickets,
        "over": over,
        "balls_bowled": balls_bowled,
        "balls_remaining": balls_remaining,
        "overs_remaining": round(overs_remaining, 2),
        "current_run_rate": round(runs / max(over, 0.1), 2),
        "wickets_in_hand": 10 - wickets,
    }

    if innings.lower().startswith("2") and target is not None:
        runs_needed = max(target - runs, 0)
        rrr = runs_needed / max(overs_remaining, 0.01)
        result.update(
            {
                "target": target,
                "runs_needed": runs_needed,
                "required_run_rate": round(rrr, 2),
                "pressure_index_0_100": min(100, round(rrr * 8 + wickets * 4, 1)),
            }
        )
    else:
        projected_total = round(runs / max(over, 0.1) * 20, 0)
        result["projected_first_innings_total"] = projected_total
        result["pressure_index_0_100"] = round(wickets * 6 + max(0, 160 - projected_total) * 0.2, 1)

    return json.dumps(result, indent=2)


def get_batter_bowler_matchup(batter: str, bowler: str) -> str:
    """
    Estimates tactical matchup edges between striker and current bowler using
    curated IPL archetype stats (pace vs spin, death overs, etc.).

    Args:
        batter: Striker name.
        bowler: Current bowler name.
    """
    bat = _resolve_player(batter) or {"role": "unknown batter", "ipl_sr": 130.0}
    bowl = _resolve_player(bowler) or {"role": "unknown bowler", "ipl_economy": 8.5}

    bat_role = bat.get("role", "")
    bowl_role = bowl.get("role", "")

    if "spin" in bowl_role.lower():
        batter_edge_sr = bat.get("vs_spin_sr", bat.get("ipl_sr", 130))
    else:
        batter_edge_sr = bat.get("vs_pace_sr", bat.get("ipl_sr", 130))

    over_phase = "middle"
    recommendation = "neutral"
    if batter_edge_sr >= 140:
        recommendation = "batter_favored_attack_length"
    elif batter_edge_sr <= 125:
        recommendation = "bowler_favored_defensive_lengths"

    payload = {
        "batter": batter,
        "bowler": bowler,
        "batter_profile": bat,
        "bowler_profile": bowl,
        "estimated_batter_sr_vs_type": batter_edge_sr,
        "phase_assumed": over_phase,
        "matchup_edge": recommendation,
    }
    return json.dumps(payload, indent=2)


def format_match_state_snapshot(state: MatchState) -> str:
    """Human-readable match card for agent prompts."""
    pressure = json.loads(
        compute_pressure_metrics(
            runs=state.runs,
            wickets=state.wickets,
            over=state.over,
            target=state.target,
            innings=state.innings,
        )
    )
    venue = json.loads(get_venue_intelligence(state.venue_key))

    lines = [
        "=== LIVE MATCH STATE ===",
        f"Innings: {state.innings} | {state.batting_team} bat vs {state.bowling_team}",
        f"Score: {state.runs}/{state.wickets} in {state.over} overs",
        f"Striker: {state.striker} | Non-striker: {state.non_striker}",
        f"Current bowler: {state.bowler}",
        f"Last over: {state.last_over_runs} runs, {state.last_over_wickets} wicket(s)",
        f"Venue: {venue.get('display_name', state.venue_key)}",
        f"Field restrictions: {state.field_restrictions}",
        f"Available bowlers: {', '.join(state.available_bowlers) or 'not specified'}",
        f"Pressure metrics: {json.dumps(pressure)}",
    ]
    if state.target is not None:
        lines.append(f"Chase target: {state.target}")
    if state.notes:
        lines.append(f"Captain notes: {state.notes}")
    return "\n".join(lines)


def build_analyst_user_prompt(state: MatchState) -> str:
    """User turn for the Data Analyst — encourages tool use for numbers."""
    snapshot = format_match_state_snapshot(state)
    return (
        f"{snapshot}\n\n"
        "Use your tools to pull venue intelligence, pressure metrics, and any relevant "
        "player profiles or matchups. Produce ONLY the Data Analyst Audit in the required format. "
        "No tactical recommendations."
    )


def build_pressure_architect_user_prompt(state: MatchState) -> str:
    """User turn for the Momentum & Pressure Architect."""
    snapshot = format_match_state_snapshot(state)
    return (
        f"{snapshot}\n\n"
        "Ignore raw database lookups unless they sharpen psychological reads. "
        "Produce ONLY the Psychological Momentum Audit in the required format."
    )


def build_strategist_user_prompt(
    state: MatchState,
    analyst_audit: str,
    pressure_audit: str,
) -> str:
    """User turn for the Strategist — synthesizes prior agent outputs."""
    snapshot = format_match_state_snapshot(state)
    return (
        f"{snapshot}\n\n"
        "--- DATA ANALYST AUDIT ---\n"
        f"{analyst_audit}\n\n"
        "--- MOMENTUM & PRESSURE ARCHITECT AUDIT ---\n"
        f"{pressure_audit}\n\n"
        "Issue your FINAL MANDATE for the very next over only. "
        "Use authentic IPL captain language."
    )


def match_state_from_dict(data: dict[str, Any]) -> MatchState:
    """Construct MatchState from UI / API payload with safe defaults."""
    over_raw = data.get("over", 0.0)
    try:
        over_val = float(over_raw)
    except (TypeError, ValueError):
        over_val = 0.0

    available = data.get("available_bowlers", [])
    if isinstance(available, str):
        available = [b.strip() for b in available.split(",") if b.strip()]

    target_raw = data.get("target")
    target: Optional[int]
    if target_raw in (None, "", 0, "0"):
        target = None
    else:
        try:
            target = int(target_raw)
        except (TypeError, ValueError):
            target = None

    return MatchState(
        innings=str(data.get("innings", "2nd")),
        batting_team=str(data.get("batting_team", "Batting XI")),
        bowling_team=str(data.get("bowling_team", "Bowling XI")),
        venue_key=_resolve_venue_key(str(data.get("venue", "wankhede"))),
        over=over_val,
        balls_in_over=int(data.get("balls_in_over", 0)),
        runs=int(data.get("runs", 0)),
        wickets=int(data.get("wickets", 0)),
        target=target,
        striker=str(data.get("striker", "")),
        non_striker=str(data.get("non_striker", "")),
        bowler=str(data.get("bowler", "")),
        last_over_runs=int(data.get("last_over_runs", 0)),
        last_over_wickets=int(data.get("last_over_wickets", 0)),
        available_bowlers=list(available),
        field_restrictions=str(data.get("field_restrictions", "none")),
        notes=str(data.get("notes", "")),
    )


# Tools registered with Gemini for the Data Analyst agent
ANALYST_GEMINI_TOOLS: list[Any] = [
    get_venue_intelligence,
    get_player_profile,
    compute_pressure_metrics,
    get_batter_bowler_matchup,
]

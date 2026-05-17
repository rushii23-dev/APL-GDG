"""
Cric-Oracle Pro — FastAPI backend serving the enterprise UI and agentic API.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDMxAdPPs9RjJP426ChlvgYQ9SOiArAXco")

from agents import AgentInvocationError, create_genai_client
from data import IPL_TEAMS_2026
from orchestrator import CaptainCoolOrchestrator
from tools import VENUE_STATS, match_state_from_dict, compute_pressure_metrics

import json

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Cric-Oracle Pro", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def serve_frontend():
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/teams")
async def list_teams():
    return {"teams": list(IPL_TEAMS_2026.keys())}


@app.get("/api/players/{team_name}")
async def list_players(team_name: str):
    team = unquote(team_name)
    players = IPL_TEAMS_2026.get(team, [])
    return {"team": team, "players": players}


@app.get("/api/venues")
async def list_venues():
    venues = [{"key": k, "name": v["display_name"]} for k, v in VENUE_STATS.items()]
    return {"venues": venues}


class MatchRequest(BaseModel):
    innings: str = "2nd"
    batting_team: str = ""
    bowling_team: str = ""
    venue: str = "wankhede"
    over: float = 0.0
    balls_in_over: int = 0
    runs: int = 0
    wickets: int = 0
    target: Optional[int] = None
    striker: str = ""
    non_striker: str = ""
    bowler: str = ""
    available_bowlers: list[str] = []
    last_over_runs: int = 0
    last_over_wickets: int = 0
    field_restrictions: str = "none"
    notes: str = ""


@app.post("/api/metrics")
async def get_metrics(req: MatchRequest):
    """Quick pressure metrics without running the full agent pipeline."""
    try:
        state = match_state_from_dict(req.model_dump())
        metrics = json.loads(compute_pressure_metrics(
            runs=state.runs, wickets=state.wickets,
            over=state.over, target=state.target, innings=state.innings,
        ))
        return {"success": True, "metrics": metrics}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/analyze")
async def analyze_match(req: MatchRequest):
    """Run the full multi-agent Gemini pipeline."""
    try:
        with CaptainCoolOrchestrator() as orch:
            result = orch.run_from_dict(req.model_dump())
        return {
            "success": True,
            "data": {
                "match_snapshot": result.match_snapshot,
                "analyst_audit": result.analyst_audit,
                "pressure_audit": result.pressure_audit,
                "strategist_mandate": result.strategist_mandate,
                "errors": result.errors,
            },
        }
    except AgentInvocationError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

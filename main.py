"""
Cric-Oracle Pro v3.0 — FastAPI engine with Jinja2 templates + Live Radar.
"""
import os
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import asyncio
import random
import json
from cricbuzz import fetch_latest_ipl_live
 
# Toggle to use Cricbuzz live feed when available. Persisted to disk.
CRICBUZZ_FLAG_FILE = Path(__file__).resolve().parent / ".cricbuzz_enabled.json"

def get_cricbuzz_enabled():
    try:
        if CRICBUZZ_FLAG_FILE.exists():
            return json.loads(CRICBUZZ_FLAG_FILE.read_text()).get("enabled", False)
    except Exception:
        return False
    return False

def set_cricbuzz_enabled_flag(v: bool):
    try:
        CRICBUZZ_FLAG_FILE.write_text(json.dumps({"enabled": bool(v)}))
        return True
    except Exception:
        return False

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
os.environ.setdefault("GEMINI_API_KEY", "AIzaSyDMxAdPPs9RjJP426ChlvgYQ9SOiArAXco")

from google import genai
from google.genai import types
from data import IPL_TEAMS_2026

app = FastAPI(title="Cric-Oracle Engine v3.0")
_BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(_BASE / "templates"))

# Serve static assets
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY missing from environment.")
client = genai.Client(api_key=api_key)
MODEL = "gemini-3.1-flash-lite"


class MatchState(BaseModel):
    batting_team: str
    bowling_team: str
    striker: str
    non_striker: str
    bowler: str
    score: str
    overs: str
    target: str


@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/teams")
async def list_teams():
    return {"teams": list(IPL_TEAMS_2026.keys())}


@app.get("/api/players/{team_name}")
async def list_players(team_name: str):
    from urllib.parse import unquote
    team = unquote(team_name)
    players = IPL_TEAMS_2026.get(team, [])
    return {"team": team, "players": players}


# ── Live Radar State (shared simulated state) ──
LIVE_STATE = {
    "match": "RCB vs PBKS",
    "venue": "Dharamshala",
    "batting_team": "Royal Challengers Bengaluru",
    "bowling_team": "Punjab Kings",
    "score": "159/3",
    "overs": "15.2",
    "striker": "Virat Kohli (58*)",
    "non_striker": "Venkatesh Iyer (39*)",
    "bowler": "Azmatullah Omarzai",
    "target": "1st Innings",
    "current_run_rate": "10.37",
}


@app.get("/api/live-radar")
async def get_live_radar():
    """Return the current simulated live state as JSON."""
    return LIVE_STATE


@app.post("/api/cricbuzz/enable")
async def set_cricbuzz_toggle(payload: dict):
    """Enable or disable the Cricbuzz live integration.

    POST body: { "enabled": true }
    """
    enabled = bool(payload.get("enabled", False))
    set_cricbuzz_enabled_flag(enabled)
    return {"use_cricbuzz": get_cricbuzz_enabled()}


@app.get("/api/cricbuzz/status")
async def cricbuzz_status():
    return {"use_cricbuzz": get_cricbuzz_enabled()}


@app.websocket("/ws/live-radar")
async def websocket_live_radar(ws: WebSocket):
    """WebSocket endpoint that streams simulated live updates every 2 seconds.

    The updates mutate a simple in-memory state (LIVE_STATE) so both HTTP
    and WS clients observe the same values.
    """
    await ws.accept()
    try:
        while True:
            # If the Cricbuzz integration is enabled, attempt to fetch real live IPL data
            if get_cricbuzz_enabled():
                try:
                    data = await asyncio.to_thread(fetch_latest_ipl_live)
                    if data:
                        # merge returned fields into LIVE_STATE (only non-empty)
                        for k, v in data.items():
                            if v:
                                LIVE_STATE[k] = v
                        await ws.send_text(json.dumps(LIVE_STATE))
                        await asyncio.sleep(2)
                        continue
                except Exception:
                    # fallback to simulated updates on error
                    pass
            # parse current score
            try:
                runs, wk = map(int, LIVE_STATE.get("score", "0/0").split("/"))
            except Exception:
                runs, wk = 0, 0

            # parse overs as overs.balls (e.g., 15.2)
            try:
                ov_str = LIVE_STATE.get("overs", "0.0")
                ov_parts = ov_str.split('.')
                ov_full = int(ov_parts[0])
                balls = int(ov_parts[1]) if len(ov_parts) > 1 else 0
            except Exception:
                ov_full, balls = 0, 0

            # Simulate an event
            # small chance of wicket
            # If this is a T20 match and we've reached 20 overs, stop scoring
            match_over = False
            try:
                ov_check = float(LIVE_STATE.get("overs", "0.0"))
                if ov_check >= 20.0:
                    match_over = True
            except Exception:
                match_over = False

            if match_over:
                runs_added = 0
            elif random.random() < 0.06:
                # wicket: no runs added, wicket increments
                wk += 1
                runs_added = 0
            else:
                runs_added = random.choices([0,1,2,3,4,6], weights=[30,30,15,5,15,5])[0]
                runs += runs_added

            # advance one ball
            if not match_over:
                balls += 1
                if balls >= 6:
                    ov_full += 1
                    balls = 0

            # If we've reached or exceeded 20 overs, clamp to 20.0 and mark finished
            if ov_full >= 20:
                ov_full = 20
                balls = 0

            # update LIVE_STATE
            LIVE_STATE["score"] = f"{runs}/{wk}"
            LIVE_STATE["overs"] = f"{ov_full}.{balls}"
            # simple run rate
            try:
                overs_float = ov_full + balls / 6.0
                LIVE_STATE["current_run_rate"] = f"{(runs / overs_float) if overs_float>0 else 0:.2f}"
            except Exception:
                LIVE_STATE["current_run_rate"] = "0.00"

            # occasionally swap striker on odd runs
            if runs_added % 2 == 1:
                LIVE_STATE["striker"], LIVE_STATE["non_striker"] = LIVE_STATE.get("non_striker"), LIVE_STATE.get("striker")

            # send update
            await ws.send_text(json.dumps(LIVE_STATE))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


# ── Multi-Agent Strategy Pipeline ──
@app.post("/api/strategize")
async def strategize(state: MatchState):
    try:
        context = (
            f"Score: {state.score} in {state.overs} overs. Target: {state.target}. "
            f"{state.batting_team} vs {state.bowling_team}. "
            f"Striker: {state.striker}. Non-Striker: {state.non_striker}. "
            f"Bowler: {state.bowler}."
        )

        # Agent 1 — Data Analyst
        analyst_res = client.models.generate_content(
            model=MODEL,
            contents=context,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are an IPL Data Analyst. Provide strict, objective analysis "
                    "of the match state, key match-ups, and venue conditions in 3-4 "
                    "punchy bullet points. Use numbers and stats. No fluff."
                ),
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )

        # Agent 2 — Momentum Architect
        arch_res = client.models.generate_content(
            model=MODEL,
            contents=f"State: {context}\nAnalyst: {analyst_res.text}",
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a Momentum & Pressure Architect. Ignore raw math. "
                    "Analyze the psychological pressure, fear metric, choke factor, "
                    "and mental momentum in 3-4 intense bullet points. Be calculating."
                ),
                temperature=0.55,
                max_output_tokens=1024,
            ),
        )

        # Agent 3 — Captain's Mandate
        capt_res = client.models.generate_content(
            model=MODEL,
            contents=(
                f"State: {context}\nAnalyst: {analyst_res.text}\n"
                f"Architect: {arch_res.text}"
            ),
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You are a legendary IPL Captain issuing a FINAL MANDATE. "
                    "Synthesize the analyst data and architect's momentum read. "
                    "Issue ONE bold, definitive tactical mandate for the next over. "
                    "Write in authentic, high-stakes cricket captain language. "
                    "Output one powerful paragraph."
                ),
                temperature=0.45,
                max_output_tokens=1024,
            ),
        )

        return {
            "analyst": analyst_res.text,
            "architect": arch_res.text,
            "captain": capt_res.text,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/update-state')
async def update_state(state: MatchState):
    """Update the shared LIVE_STATE from the UI controls."""
    try:
        LIVE_STATE['batting_team'] = state.batting_team
        LIVE_STATE['bowling_team'] = state.bowling_team
        LIVE_STATE['striker'] = state.striker
        LIVE_STATE['non_striker'] = state.non_striker
        LIVE_STATE['bowler'] = state.bowler
        LIVE_STATE['score'] = state.score
        LIVE_STATE['overs'] = state.overs
        LIVE_STATE['target'] = state.target
        return {'status': 'ok', 'live_state': LIVE_STATE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/debate')
async def start_debate(payload: dict):
    # Minimal stub: return an acknowledgement and short simulated debate note
    return {'status': 'ok', 'message': 'Debate initiated among AI agents. Use AI RECOMMENDATION to fetch outputs.'}


@app.post('/api/deploy')
async def deploy_strategy(payload: dict):
    # Minimal stub: simulate applying a strategy and return confirmation
    return {'status': 'ok', 'message': 'Strategy deployed to the field. Captain notified.'}


@app.post('/api/impact')
async def impact_player(payload: dict):
    # Minimal stub: simulate player impact (e.g., substitution) and return current LIVE_STATE
    return {'status': 'ok', 'message': 'Player impact registered.', 'live_state': LIVE_STATE}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

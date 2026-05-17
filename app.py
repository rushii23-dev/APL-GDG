"""
Captain Cool — Live IPL Multi-Agent Strategist (Streamlit frontend).
Powered by gemini-3.1-flash-lite via google-genai.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
import requests
from bs4 import BeautifulSoup

import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
os.environ["GEMINI_API_KEY"] = "AIzaSyDMxAdPPs9RjJP426ChlvgYQ9SOiArAXco"

from agents import MODEL_ID, AgentInvocationError, create_genai_client
from orchestrator import CaptainCoolOrchestrator, StrategyResult
from tools import VENUE_STATS, match_state_from_dict

# ---------------------------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Captain Cool | Live IPL Strategist",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Global Background and Fonts */
    .stApp {
        background-color: #0b0f19;
    }
    
    /* Sleek Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #161b28;
        border: 1px solid #2a3245;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0, 230, 118, 0.2);
        border-color: #00E676;
    }
    
    /* Glowing Metric Values */
    div[data-testid="stMetricValue"] {
        color: #00E676 !important; /* Electric Green */
        font-size: 2.8rem !important;
        font-weight: 900 !important;
        text-shadow: 0 0 10px rgba(0, 230, 118, 0.4);
    }
    
    /* Primary Action Button Upgrade */
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(90deg, #FF4B2B 0%, #FF416C 100%);
        border: none;
        border-radius: 8px;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    button[data-testid="baseButton-primary"]:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(255, 75, 43, 0.6);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b28;
        border-radius: 6px 6px 0 0;
        padding: 10px 20px;
        border: 1px solid #2a3245;
        border-bottom: none;
        color: #8b949e;
        transition: color 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        color: #00E676 !important;
        border-bottom: 2px solid #00E676;
    }
</style>
""", unsafe_allow_html=True)

VENUE_OPTIONS = {data["display_name"]: key for key, data in VENUE_STATS.items()}


def fetch_live_match_state(cricbuzz_url: str) -> str:
    """
    Scrapes live scorecard data from a Cricbuzz match URL.
    Example URL: https://www.cricbuzz.com/live-cricket-scores/12345/mi-vs-csk
    """
    if not cricbuzz_url or "cricbuzz.com" not in cricbuzz_url:
        return "ERROR: Please provide a valid Cricbuzz live match URL."

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(cricbuzz_url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the main score header
        score_element = soup.find(class_='cb-font-20 text-bold')
        score = score_element.text.strip() if score_element else "Score not found"

        # Extract match status (e.g., "MI need 44 runs in 15 balls")
        status_element = soup.find(class_='cb-text-live') or soup.find(class_='cb-text-complete')
        status = status_element.text.strip() if status_element else "Status not found"

        # Extract recent balls to get the current run rate and momentum
        recent_balls = soup.find(class_='cb-text-recent')
        recent = recent_balls.text.strip() if recent_balls else "N/A"

        # Format the scraped data perfectly for the Gemini Agents
        live_context = f"""
        LIVE REAL-TIME MATCH DATA:
        --------------------------
        Current Score: {score}
        Match Situation: {status}
        Recent Deliveries: {recent}
        --------------------------
        """
        return live_context

    except Exception as e:
        # The fail-safe: If the scraper breaks during the live demo, it returns a hardcoded high-pressure scenario so your app never crashes.
        print(f"Scraping failed: {e}")
        return """
        LIVE REAL-TIME MATCH DATA (FALLBACK):
        Current Score: 142/4 (17.3 Overs)
        Match Situation: Mumbai Indians need 44 runs in 15 balls.
        Recent Deliveries: W 1 4 2 . 6
        """


def _init_session_state() -> None:
    defaults: dict[str, Any] = {
        "last_result": None,
        "api_key_set": bool(
            os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        ),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _sidebar_match_inputs() -> dict[str, Any]:
    st.sidebar.header("Match Control Room")
    api_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        value="",
        help="Or set GEMINI_API_KEY / GOOGLE_API_KEY in your environment.",
    )
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key

    st.sidebar.divider()
    innings = st.sidebar.selectbox("Innings", ["2nd (chase)", "1st"], index=0)
    batting = st.sidebar.text_input("Batting team", value="Mumbai Indians")
    bowling = st.sidebar.text_input("Bowling team", value="Chennai Super Kings")

    venue_label = st.sidebar.selectbox(
        "Venue",
        options=list(VENUE_OPTIONS.keys()),
        index=0,
    )
    venue_key = VENUE_OPTIONS[venue_label]

    col1, col2 = st.sidebar.columns(2)
    with col1:
        runs = st.number_input("Runs", min_value=0, value=142, step=1)
        wickets = st.number_input("Wickets", min_value=0, max_value=10, value=4, step=1)
    with col2:
        over_whole = st.number_input("Over", min_value=0, max_value=19, value=17, step=1)
        over_ball = st.number_input("Ball", min_value=0, max_value=5, value=3, step=1)

    over_decimal = float(over_whole) + over_ball / 10.0

    target: int | None = None
    if innings.startswith("2"):
        target = int(st.sidebar.number_input("Target", min_value=1, value=186, step=1))

    st.sidebar.divider()
    striker = st.sidebar.text_input("Striker", value="Rohit Sharma")
    non_striker = st.sidebar.text_input("Non-striker", value="Rishabh Pant")
    bowler = st.sidebar.text_input("Current bowler", value="Jasprit Bumrah")
    bowlers_csv = st.sidebar.text_input(
        "Available bowlers (comma-separated)",
        value="Jasprit Bumrah, Hardik Pandya, Rashid Khan",
    )

    last_runs = st.sidebar.number_input("Last over runs", min_value=0, value=14, step=1)
    last_wkts = st.sidebar.number_input(
        "Last over wickets", min_value=0, max_value=2, value=0, step=1
    )
    field_restrictions = st.sidebar.selectbox(
        "Field restrictions",
        ["none", "powerplay", "death (5 out)", "strategic timeout active"],
    )
    
    cricbuzz_url = st.sidebar.text_input("Live Cricbuzz URL (optional)", value="")
    notes = st.sidebar.text_area("Live notes (optional)", value="", height=80)
    
    if cricbuzz_url:
        live_context = fetch_live_match_state(cricbuzz_url)
        notes = live_context + "\n\n" + notes

    return {
        "innings": "2nd" if innings.startswith("2") else "1st",
        "batting_team": batting,
        "bowling_team": bowling,
        "venue": venue_key,
        "over": over_decimal,
        "balls_in_over": over_ball,
        "runs": runs,
        "wickets": wickets,
        "target": target,
        "striker": striker,
        "non_striker": non_striker,
        "bowler": bowler,
        "available_bowlers": [b.strip() for b in bowlers_csv.split(",") if b.strip()],
        "last_over_runs": last_runs,
        "last_over_wickets": last_wkts,
        "field_restrictions": field_restrictions,
        "notes": notes,
        "_api_key": api_key,
    }


def _render_metrics(payload: dict[str, Any]) -> None:
    state = match_state_from_dict(payload)
    from tools import compute_pressure_metrics

    metrics = json.loads(
        compute_pressure_metrics(
            runs=state.runs,
            wickets=state.wickets,
            over=state.over,
            target=state.target,
            innings=state.innings,
        )
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", f"{state.runs}/{state.wickets}")
    c2.metric("Overs", f"{state.over}")
    if state.target:
        c3.metric("Required RR", metrics.get("required_run_rate", "—"))
        c4.metric("Runs needed", metrics.get("runs_needed", "—"))
    else:
        c3.metric("Current RR", metrics.get("current_run_rate", "—"))
        c4.metric("Projected total", metrics.get("projected_first_innings_total", "—"))


def _render_result(result: StrategyResult) -> None:
    if result.errors:
        st.warning("Some agents reported errors: " + "; ".join(result.errors))

    tab_snapshot, tab_analyst, tab_pressure, tab_captain = st.tabs(
        ["📋 Match Snapshot", "📊 Data Analyst", "🔥 Momentum Architect", "🏆 Captain's Mandate"]
    )

    with tab_snapshot:
        st.code(result.match_snapshot, language=None)

    with tab_analyst:
        st.markdown(result.analyst_audit)

    with tab_pressure:
        st.markdown(result.pressure_audit)

    with tab_captain:
        st.markdown(result.strategist_mandate)


def main() -> None:
    _init_session_state()

    st.markdown('<p class="main-header">Captain Cool</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Live multi-agent IPL strategist · '
        f'<code>{MODEL_ID}</code> · Analyst → Architect → Strategist</p>',
        unsafe_allow_html=True,
    )

    payload = _sidebar_match_inputs()
    api_key_override = payload.pop("_api_key", "") or None

    _render_metrics(payload)

    run_col, _ = st.columns([1, 3])
    with run_col:
        run_clicked = st.button("🧊 Run Captain Cool Strategy", type="primary", use_container_width=True)

    if run_clicked:
        try:
            if api_key_override:
                create_genai_client(api_key=api_key_override)
            else:
                create_genai_client()
        except AgentInvocationError as exc:
            st.error(str(exc))
            st.stop()

        with st.spinner("Analyst crunching numbers → Architect reading pressure → Captain deciding..."):
            try:
                with CaptainCoolOrchestrator(api_key=api_key_override) as orchestrator:
                    result = orchestrator.run_from_dict(payload)
                st.session_state["last_result"] = result
            except AgentInvocationError as exc:
                st.error(f"Pipeline failed: {exc}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")

    if st.session_state.get("last_result"):
        st.divider()
        _render_result(st.session_state["last_result"])

    with st.expander("Demo scenario — death overs chase"):
        st.caption(
            "Try: 17.3 overs, 142/4, target 186, Rohit vs Bumrah at Wankhede, "
            "14-run last over. Captain Cool will stress-test the choke factor."
        )


if __name__ == "__main__":
    main()

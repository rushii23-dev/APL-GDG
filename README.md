# Captain Cool — Cric-Oracle Pro

A lightweight FastAPI web app that simulates and (optionally) sources live IPL match scores, provides a live "radar" UI, and runs a small multi-agent strategy pipeline driven by an LLM. The UI mirrors a Captain/Analyst/Architect decision interface for in-play tactical recommendations.

This repository contains a local development demo intended for experimentation and UX prototyping.

## Key features

- Real-time live radar UI served at `/` (WebSocket updates from `/ws/live-radar`).
- Toggle to attempt live-score scraping from Cricbuzz (best-effort) via `/api/cricbuzz/enable`.
- Multi-agent strategy endpoint `/api/strategize` that uses Google GenAI (Gemini) to produce Analyst, Architect, and Captain outputs.
- Several UI action endpoints: `/api/update-state`, `/api/debate`, `/api/deploy`, `/api/impact`.
- Clean, responsive UI in `templates/index.html` with a left live-entry panel and large hero action area.

## Files of interest

- [main.py](main.py) — FastAPI app, WebSocket server, endpoints, and live-state simulation.
- [cricbuzz.py](cricbuzz.py) — Best-effort scraper that tries mobile/desktop Cricbuzz and ESPN fallback for score snippets.
- [templates/index.html](templates/index.html) — Front-end UI template. Buttons are wired to the backend.
- [requirements.txt](requirements.txt) — Python dependencies.

## Quick start (development)

1. Create a Python virtual environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

2. (Optional) Set environment variables. The app expects a Gemini API key for the AI pipeline (optional). Create a `.env` file or set `GEMINI_API_KEY` in the environment:

```
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

3. Run the app:

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

4. Open the UI at: http://127.0.0.1:8000

## Useful API endpoints

- `GET /api/live-radar` — current `LIVE_STATE` JSON.
- `POST /api/cricbuzz/enable` — body `{ "enabled": true }` to enable Cricbuzz scraping.
- `GET /api/cricbuzz/status` — check whether scraping is enabled.
- `POST /api/strategize` — run the LLM multi-agent pipeline (expects a MatchState JSON body).
- `POST /api/update-state` — update the shared live state with UI values.
- `POST /api/debate`, `/api/deploy`, `/api/impact` — UI action stubs that return confirmations.
- WebSocket: `ws://127.0.0.1:8000/ws/live-radar` — subscribe to live-state updates.

## Notes on live scores and scraping

- The built-in `cricbuzz.py` scraper is best-effort and uses simple HTML/meta parsing. It may fail if Cricbuzz changes markup or blocks requests.
- For production-accurate live scores, use a dedicated sports data API (recommended). I can add adapters for providers like CricAPI, SportRadar, or similar if you provide credentials.

## Troubleshooting

- If the UI cannot connect to the WebSocket, ensure the uvicorn server is running and port `8000` is available.
- If `GEMINI_API_KEY` is not set, the `/api/strategize` endpoint will fail — either set the key or avoid the AI button.
- If scraping fails frequently, enable the toggle only for testing or switch to a paid API.

## Development & Contributing

- The project has been initialized as a Git repository and recent changes were pushed to the remote you provided during work.
- Create feature branches, run the server locally, and open a pull request.

## License

This repository is provided as-is for prototyping and development. No license specified.

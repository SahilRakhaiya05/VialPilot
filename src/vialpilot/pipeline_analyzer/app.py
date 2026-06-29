"""VialPilot Pipeline Analyzer (Dash + Plotly)."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Optional

import requests
from dash import Input, Output, State, dcc, html, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from visualizer.app import create_app as _create_base_app  # noqa: E402
from visualizer.data_processor import LogProcessor  # noqa: E402
from visualizer.components import create_error_alert  # noqa: E402
from visualizer.styles import COLORS  # noqa: E402

VIALPILOT_API = "http://127.0.0.1:7860"


def create_vialpilot_analyzer(debug: bool = False):
    """Extend the log visualizer with VialPilot run loading."""
    app = _create_base_app(debug=debug)

    run_loader = dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4("Load VialPilot Run", className="mb-2"),
                    html.P("Pull agent timeline from a saved VialPilot run.",
                           className="text-muted small"),
                ], width=12),
                dbc.Col([
                    dbc.InputGroup([
                        dbc.Input(id="vp-run-id", placeholder="Paste run UUID from /runs …", type="text"),
                        dbc.Button("Load Run", id="vp-load-run", color="primary"),
                        dbc.Button(html.A("← VialPilot", href=f"{VIALPILOT_API}/", target="_blank"),
                                   color="secondary", outline=True),
                    ]),
                ], width=12),
            ]),
            html.Div(id="vp-load-status", className="mt-2"),
        ]),
    ], className="mb-3", color="light")

    # Prepend run loader after header in layout
    original_children = app.layout.children  # type: ignore[attr-defined]
    app.layout.children = [original_children[0], run_loader] + list(original_children[1:])  # type: ignore

    @app.callback(
        [Output("log-store", "data", allow_duplicate=True),
         Output("vp-load-status", "children")],
        Input("vp-load-run", "n_clicks"),
        State("vp-run-id", "value"),
        prevent_initial_call=True,
    )
    def load_vialpilot_run(n_clicks, run_id: Optional[str]):
        if not run_id or not str(run_id).strip():
            return no_update, create_error_alert("Enter a run ID from VialPilot history.")
        run_id = str(run_id).strip()
        try:
            resp = requests.get(f"{VIALPILOT_API}/api/runs/{run_id}/pipeline-logs", timeout=15)
            resp.raise_for_status()
            log_lines = resp.text.splitlines()
            processor = LogProcessor()
            logs = processor.parse_logs(log_lines)
            if not logs:
                return no_update, create_error_alert("No log entries in this run.")
            info = dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                f"Loaded VialPilot run ",
                html.Code(run_id[:8] + "…"),
                f" — {len(logs)} log entries",
            ], color="success", className="mb-0")
            return {"logs": logs, "filename": f"vialpilot_{run_id[:8]}.log"}, info
        except Exception as exc:
            return no_update, create_error_alert(f"Failed to load run: {exc}")

    # Rebrand header via clientside is hard; title already set in base app
    return app


def start_analyzer(port: int = 8050, debug: bool = False) -> None:
    app = create_vialpilot_analyzer(debug=debug)
    app.run(debug=debug, host="0.0.0.0", port=port, use_reloader=False)


def start_analyzer_thread(port: int = 8050) -> threading.Thread:
    t = threading.Thread(target=start_analyzer, kwargs={"port": port, "debug": False}, daemon=True)
    t.start()
    return t
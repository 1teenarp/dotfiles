#!/usr/bin/env python3
# -------------------------------------------------------------------------
#  Model‑Hub Flask app – updated version
#  * Dynamic reference URLs (no hard‑coded “localhost”)
#  * URL can be opened in a new tab – only for ACTIVE models
#  * Full model parameters from models.yaml are displayed
# -------------------------------------------------------------------------

import json
import re
import subprocess
import yaml
import os
from flask import Flask, render_template_string, request

app = Flask(__name__)
CONFIG_FILE = "models.yaml"


# -------------------------------------------------------------------------
#  Helper: capture a quick nvtop snapshot (used only for the little monitor)
# -------------------------------------------------------------------------
def get_nvtop_output():
    """Captures nvtop snapshot with timeout and strips ANSI escape codes."""
    try:
        env = os.environ.copy()
        env["TERM"] = "vt100"
        env["COLUMNS"] = "120"

        cmd = ["nvtop", "-p", "-d", "1"]
        out = subprocess.check_output(
            cmd, env=env, stderr=subprocess.STDOUT, timeout=1.5
        ).decode("utf-8", errors="ignore")

        # Remove ANSI colour codes – otherwise HTML would contain garbage chars
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", out)
    except subprocess.TimeoutExpired:
        return "Error: nvtop timed out. Run `nvtop` manually to verify access."
    except Exception as e:
        return f"Error: {e}\nMake sure nvtop is installed (sudo apt install nvtop)."


# -------------------------------------------------------------------------
#  Helper: enrich the model dict with runtime info (active flag, URL, JSON)
# -------------------------------------------------------------------------
def get_live_data():
    """Read models.yaml and add runtime information (active, url, json)."""
    if not os.path.exists(CONFIG_FILE):
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            raw = yaml.safe_load(f) or {}
        models = raw.get("models", {})
    except Exception:
        return {}

    # Check tmux session existence → active flag
    for key in models:
        res = subprocess.run(
            ["tmux", "has-session", "-t", f"svc-{key}"], capture_output=True
        )
        models[key]["active"] = (res.returncode == 0)

    # Build the reference URL **from the request host** and the model's own port
    # Example:  http://spark-c081:30000/v1
    for key, cfg in models.items():
        cfg["url"] = f"{request.scheme}://{request.host.split(':')[0]}:{cfg.get('port', 0)}"
        cfg["config_json"] = json.dumps(cfg, indent=2)   # pretty‑print for the UI
    return models


# -------------------------------------------------------------------------
#  Flask route – main page
# -------------------------------------------------------------------------
@app.route("/")
def index():
    models = get_live_data()
    nvtop_out = get_nvtop_output()

    # -----------------------------------------------------------------
    #  Template – note the new parts:
    #   • {{ model.url }}  → clickable, opens in a new tab (only if active)
    #   • <pre>{{ model.config_json }}</pre> → shows *all* parameters
    # -----------------------------------------------------------------
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="2">
        <title>Model Hub</title>
        <style>
            body { background:#0d1117; color:#c9d1d9; font-family:-apple-system, sans-serif;
                  padding:20px; margin:0; }
            .container { max-width:1200px; margin:auto; }
            .header { border-bottom:1px solid #30363d; margin-bottom:20px;
                      padding-bottom:10px; }
            .nvtop-box {
                background:#000; color:#58a6ff; padding:15px; border-radius:6px;
                font-family:monospace; white-space:pre; overflow-x:auto;
                font-size:11px; border:1px solid #30363d; margin-bottom:30px;
                min-height:100px;
            }
            .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr));
                    gap:15px; }
            .card { background:#161b22; border:1px solid #30363d; padding:15px;
                    border-radius:8px; position:relative; }
            .active-border { border-color:#238636; border-left:4px solid #238636; }
            .dot { height:8px; width:8px; border-radius:50%; display:inline-block;
                    margin-right:8px; }
            .dot-active { background:#3fb950; box-shadow:0 0 5px #238636; }
            .dot-idle { background:#484f58; }
            code { background:#010409; color:#ff7b72; display:block; padding:8px;
                    border-radius:4px; margin-top:10px; font-size:11px;
                    border:1px solid #30363d; overflow:auto; }
            .label { font-size:11px; color:#8b949e; text-transform:uppercase;
                    margin-bottom:10px; display:block; }
            pre { background:#000; color:#ff7b72; padding:10px; border-radius:4px;
                  font-size:11px; overflow:auto; margin-top:8px; }
            details { margin-top:6px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span style="float:right; color:#8b949e; font-size:12px;">
                    Auto‑refresh: 2s
                </span>
                <h2 style="margin:0;">Inference Hub</h2>
            </div>

            <span class="label">GPU Resource Monitor (nvtop)</span>
            <div class="nvtop-box">{{ nvtop_out }}</div>

            <span class="label">Model Registry</span>
            <div class="grid">
                {% for name, cfg in models.items() %}
                <div class="card {{ 'active-border' if cfg.active else '' }}">
                    <div style="display:flex; justify-content:space-between;
                                align-items:flex-start;">
                        <strong>{{ name }}</strong>
                        <span class="dot {{ 'dot-active' if cfg.active else 'dot-idle' }}"></span>
                    </div>

                    <div style="font-size:12px; color:#8b949e; margin-top:5px;">
                        Port: {{ cfg.port }} | {{ cfg.type }}
                    </div>

                    <!-- 1️⃣  Open‑in‑new‑tab link (only when ACTIVE) -->
                    {% if cfg.active %}
                        <a href="{{ cfg.url }}" target="_blank"
                           style="position:absolute; top:8px; right:8px; color:#238636;">
                            📂 Open
                        </a>
                    {% endif %}

                    <code> {{ cfg.url }} </code>

                    <!-- 2️⃣  Show *all* parameters from models.yaml -->
                    <details>
                        <summary>Parameters</summary>
                        <pre>{{ cfg.config_json }}</pre>
                    </details>
                </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(template,
                                  models=models,
                                  nvtop_out=nvtop_out)


# -------------------------------------------------------------------------
#  Run the Flask dev server (threaded so the GPU call does not block)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)


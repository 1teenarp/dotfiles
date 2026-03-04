"""Flask web dashboard for the inference manager."""

import json
import os
import re
import subprocess

from flask import Flask, render_template_string, request

import registry
from backends import get_backend, load_all_backends

app = Flask(__name__)


def get_nvtop_output():
    """Capture nvtop snapshot with timeout."""
    try:
        env = os.environ.copy()
        env["TERM"] = "vt100"
        env["COLUMNS"] = "120"
        out = subprocess.check_output(
            ["nvtop", "-p", "-d", "1"],
            env=env, stderr=subprocess.STDOUT, timeout=1.5,
        ).decode("utf-8", errors="ignore")
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", out)
    except subprocess.TimeoutExpired:
        return "Error: nvtop timed out."
    except Exception as e:
        return f"Error: {e}"


@app.route("/")
def index():
    load_all_backends()
    data = registry.load()
    models = data.get("models", {})

    # Add runtime info
    for key, cfg in models.items():
        backend = get_backend(key, cfg)
        cfg["active"] = backend.is_running()
        cfg["url"] = f"{request.scheme}://{request.host.split(':')[0]}:{cfg.get('port', 0)}"
        cfg["config_json"] = json.dumps(cfg, indent=2)

    nvtop_out = get_nvtop_output()

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="refresh" content="30">
        <link rel="icon" type="image/png" sizes="32x32" href="https://zelda.nintendo.com/assets/icons/favicon-32x32.png">
        <title>Model Hub v2</title>
        <style>
            body { background:#0d1117; color:#c9d1d9; font-family:-apple-system, sans-serif;
                   padding:20px; margin:0; }
            .container { max-width:1200px; margin:auto; }
            .header { border-bottom:1px solid #30363d; margin-bottom:20px; padding-bottom:10px; }
            .nvtop-box {
                background:#000; color:#58a6ff; padding:15px; border-radius:6px;
                font-family:monospace; white-space:pre; overflow-x:auto;
                font-size:11px; border:1px solid #30363d; margin-bottom:30px;
                min-height:100px;
            }
            .grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr)); gap:15px; }
            .card { background:#161b22; border:1px solid #30363d; padding:15px;
                    border-radius:8px; position:relative; }
            .active-border { border-color:#238636; border-left:4px solid #238636; }
            .dot { height:8px; width:8px; border-radius:50%; display:inline-block; margin-right:8px; }
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
            .star { color:#e3b341; margin-left:6px; }
            .badge { font-size:10px; padding:2px 6px; border-radius:4px;
                     background:#1f2937; color:#8b949e; margin-left:6px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span style="float:right; color:#8b949e; font-size:12px;">Auto-refresh: 30s</span>
                <h2 style="margin:0;">Inference Hub <span class="badge">v2</span></h2>
            </div>

            <span class="label">GPU Resource Monitor (nvtop)</span>
            <div class="nvtop-box">{{ nvtop_out }}</div>

            <span class="label">Model Registry</span>
            <div class="grid">
                {% for name, cfg in models.items() %}
                <div class="card {{ 'active-border' if cfg.active else '' }}">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <strong>{{ name }}
                            {% if cfg.starred %}<span class="star">&#9733;</span>{% endif %}
                        </strong>
                        <span class="dot {{ 'dot-active' if cfg.active else 'dot-idle' }}"></span>
                    </div>
                    <div style="font-size:12px; color:#8b949e; margin-top:5px;">
                        Port: {{ cfg.port }} | {{ cfg.backend }}
                    </div>
                    {% if cfg.active %}
                        <a href="{{ cfg.url }}" target="_blank"
                           style="position:absolute; top:8px; right:28px; color:#238636; text-decoration:none;">
                            Open
                        </a>
                    {% endif %}
                    <code>{{ cfg.url }}</code>
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
    return render_template_string(template, models=models, nvtop_out=nvtop_out)


def serve():
    """Start the Flask dashboard."""
    app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    serve()

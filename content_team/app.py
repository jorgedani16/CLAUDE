#!/usr/bin/env python3
"""
Content Team — Local Web App
Run: python app.py
Then open: http://localhost:8080
"""

import json
import os
import time
from datetime import datetime, date
from pathlib import Path
import queue
import threading

from flask import Flask, render_template, request, redirect, url_for, flash, Response, send_file, jsonify

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
SETTINGS_FILE = BASE_DIR / "data" / "settings.json"

app = Flask(__name__)
app.secret_key = "la-merced-content-team"

OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ── Default settings pre-filled for La Merced ──────────────────────────────

DEFAULT_SETTINGS = {
    "api_key": "",
    "business_name": "Pastelería La Merced",
    "instagram_handle": "@pastelerialamerced",
    "location": "Valencia, España",
    "website": "pastelerialamerced.es",
    "niche": "Tartas personalizadas hechas a medida para bodas, cumpleaños, baby showers y eventos especiales. Diseño totalmente personalizado online. Recogida en Valencia.",
    "target_audience": "Hombres y mujeres de 20 a 40 años en Valencia que tienen un evento próximo y buscan una tarta única y personalizada.",
    "brand_voice": "Directo, cercano, artesanal. Habla como un dueño de pastelería local que ama lo que hace. Sin corporativismo.",
    "main_cta": "Diseña la tuya ahora — visita el enlace en la descripción ■",
    "ga4_property_id": "",
    "google_credentials_path": "",
    "search_console_site_url": "https://pastelerialamerced.es",
    "squarespace_api_key": "",
}

DEFAULT_METRICS = {
    "week": "",
    "account": {
        "followers": 0,
        "followers_gained_this_week": 0,
        "visitas_perfil_reel_promedio": 0,
        "reach": 0,
    },
    "top_posts": [{}, {}, {}],
    "worst_post": {},
    "ventas_configurador_semana": 0,
    "leads_whatsapp_semana": 0,
    "resenas_google_total": 0,
    "competitors_observed": [{}],
    "manual_notes": "",
}

AGENTS_META = [
    {"id": "analyst",    "name": "Data Analyst",       "role": "Lee tus datos y encuentra qué funciona", "emoji": "📊"},
    {"id": "strategist", "name": "Content Strategist",  "role": "Define el plan de contenido semanal",     "emoji": "🧠"},
    {"id": "ideator",    "name": "Ideator",             "role": "30+ ideas → 7 ganadoras",                "emoji": "💡"},
    {"id": "scripter",   "name": "Scripter",            "role": "Escribe los guiones listos para grabar",  "emoji": "✍️"},
    {"id": "publisher",  "name": "Publishing Manager",  "role": "Agenda + checklist DM funnel",            "emoji": "📅"},
]

# ── Helpers ─────────────────────────────────────────────────────────────────

def load_settings():
    if SETTINGS_FILE.exists():
        s = json.loads(SETTINGS_FILE.read_text())
        return {**DEFAULT_SETTINGS, **s}
    return DEFAULT_SETTINGS.copy()

def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False))

def load_metrics():
    p = DATA_DIR / "metrics_input.json"
    if p.exists():
        return json.loads(p.read_text())
    return DEFAULT_METRICS.copy()

def save_metrics(m):
    p = DATA_DIR / "metrics_input.json"
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False))

def load_auto_metrics():
    """Load the most recent auto_metrics file if available."""
    files = sorted(DATA_DIR.glob("auto_metrics_*.json"), reverse=True)
    if files:
        try:
            return json.loads(files[0].read_text())
        except Exception:
            pass
    return None

def get_last_run():
    prefixes = [
        ("1_analyst_brief", "📊 Analyst Brief"),
        ("2_content_strategy", "🧠 Strategy"),
        ("3_ideas", "💡 Ideas"),
        ("4_scripts", "✍️ Scripts"),
        ("5_publishing_plan", "📅 Publishing Plan"),
    ]
    result = []
    for prefix, label in prefixes:
        files = sorted(OUTPUT_DIR.glob(f"{prefix}_*.md"), reverse=True)
        if files:
            d = files[0].stem.split("_")[-1]
            result.append({"label": label, "date": d, "file": files[0].name})
    return result if result else None

def get_outputs():
    order = ["1_analyst_brief", "2_content_strategy", "3_ideas", "4_scripts", "5_publishing_plan"]
    labels = {
        "1_analyst_brief":    ("📊", "Data Analyst Brief"),
        "2_content_strategy": ("🧠", "Content Strategy"),
        "3_ideas":            ("💡", "Ideas (30+ brainstorm → 7 ganadoras)"),
        "4_scripts":          ("✍️", "Guiones listos para grabar"),
        "5_publishing_plan":  ("📅", "Plan de Publicación"),
    }
    outputs = []
    for prefix in order:
        files = sorted(OUTPUT_DIR.glob(f"{prefix}_*.md"), reverse=True)
        if files:
            f = files[0]
            emoji, label = labels[prefix]
            d = f.stem.split("_")[-1]
            outputs.append({
                "filename": f.name,
                "label": label,
                "emoji": emoji,
                "date": d,
                "content": f.read_text(),
            })
    return outputs

def greeting():
    h = datetime.now().hour
    if h < 12: return "morning"
    if h < 18: return "afternoon"
    return "evening"

def get_api_status(settings, auto_data=None):
    """Return status dict for each API integration."""
    statuses = {}

    # GA4
    if not settings.get("ga4_property_id") or not settings.get("google_credentials_path"):
        statuses["ga4"] = "not_configured"
    elif auto_data and "ga4" in auto_data and "error" in auto_data["ga4"]:
        statuses["ga4"] = "error"
    elif auto_data and "ga4" in auto_data:
        statuses["ga4"] = "connected"
    else:
        statuses["ga4"] = "not_configured"

    # Search Console
    if not settings.get("google_credentials_path") or not settings.get("search_console_site_url"):
        statuses["sc"] = "not_configured"
    elif auto_data and "sc" in auto_data and "error" in auto_data["sc"]:
        statuses["sc"] = "error"
    elif auto_data and "sc" in auto_data:
        statuses["sc"] = "connected"
    else:
        statuses["sc"] = "not_configured"

    # Squarespace
    if not settings.get("squarespace_api_key"):
        statuses["sq"] = "not_configured"
    elif auto_data and "sq" in auto_data and "error" in auto_data["sq"]:
        statuses["sq"] = "error"
    elif auto_data and "sq" in auto_data:
        statuses["sq"] = "connected"
    else:
        statuses["sq"] = "not_configured"

    return statuses

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
        active="home",
        settings=load_settings(),
        last_run=get_last_run(),
        greeting=greeting(),
    )

@app.route("/setup", methods=["GET", "POST"])
def setup():
    s = load_settings()
    if request.method == "POST":
        for k in DEFAULT_SETTINGS:
            if k in request.form:
                s[k] = request.form[k].strip()
        save_settings(s)
        flash("Configuración guardada.", "success")
        return redirect(url_for("setup"))
    return render_template("setup.html", active="setup", settings=s)

@app.route("/metrics", methods=["GET", "POST"])
def metrics():
    m = load_metrics()
    settings = load_settings()
    auto_data = load_auto_metrics()
    api_status = get_api_status(settings, auto_data)

    if request.method == "POST":
        f = request.form
        m["week"] = str(date.today())
        m["account"] = {
            "followers": int(f.get("followers") or 0),
            "followers_gained_this_week": int(f.get("followers_gained") or 0),
            "visitas_perfil_reel_promedio": int(f.get("visitas_perfil_reel") or 0),
            "reach": int(f.get("reach") or 0),
        }
        m["ventas_configurador_semana"] = int(f.get("ventas_configurador") or 0)
        m["leads_whatsapp_semana"] = int(f.get("leads_whatsapp") or 0)
        m["resenas_google_total"] = int(f.get("resenas_google") or 0)

        m["top_posts"] = []
        for i in range(3):
            m["top_posts"].append({
                "type": f.get(f"top_type_{i}", "Reel"),
                "hook": f.get(f"top_hook_{i}", ""),
                "views": int(f.get(f"top_views_{i}") or 0),
                "visitas_perfil": int(f.get(f"top_visitas_perfil_{i}") or 0),
                "likes": int(f.get(f"top_likes_{i}") or 0),
                "comments": int(f.get(f"top_comments_{i}") or 0),
                "shares": int(f.get(f"top_shares_{i}") or 0),
                "saves": int(f.get(f"top_saves_{i}") or 0),
                "outcome": f.get(f"top_outcome_{i}", ""),
            })
        m["worst_post"] = {
            "type": f.get("bad_type", "Reel"),
            "hook": f.get("bad_hook", ""),
            "views": int(f.get("bad_views") or 0),
            "outcome": f.get("bad_outcome", ""),
        }
        m["competitors_observed"] = [{
            "handle": f.get("comp_handle", ""),
            "viral_post_hook": f.get("comp_hook", ""),
            "approx_views": f.get("comp_views", ""),
            "notes": f.get("comp_notes", ""),
        }]
        m["manual_notes"] = f.get("manual_notes", "")
        save_metrics(m)
        flash("Métricas guardadas.", "success")
        return redirect(url_for("metrics"))

    return render_template("metrics.html",
        active="metrics",
        m=m,
        auto_data=auto_data,
        api_status=api_status,
    )

@app.route("/api/pull-data", methods=["POST"])
def api_pull_data():
    """Pull data from all 3 integrations and save to data/auto_metrics_{date}.json"""
    settings = load_settings()

    from integrations import ga4, search_console, squarespace

    ga4_data = ga4.pull(
        settings.get("ga4_property_id", ""),
        settings.get("google_credentials_path", ""),
    )
    sc_data = search_console.pull(
        settings.get("search_console_site_url", ""),
        settings.get("google_credentials_path", ""),
    )
    sq_data = squarespace.pull(settings.get("squarespace_api_key", ""))

    result = {
        "pulled_at": datetime.now().isoformat(),
        "ga4": ga4_data,
        "sc": sc_data,
        "sq": sq_data,
    }

    today = date.today().isoformat()
    out_path = DATA_DIR / f"auto_metrics_{today}.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return jsonify(result)

@app.route("/run")
def run_page():
    import json as _json
    return render_template("run.html",
        active="run",
        settings=load_settings(),
        agents=AGENTS_META,
        agents_json=_json.dumps(AGENTS_META),
    )

@app.route("/api/run", methods=["POST"])
def api_run():
    only = request.args.get("only")
    settings = load_settings()
    instagram_metrics = load_metrics()

    def generate():
        def emit(data):
            return f"data: {json.dumps(data)}\n\n"

        try:
            from agents import data_analyst, content_strategist, ideator, scripter, publishing_manager
            import config as cfg

            os.environ["ANTHROPIC_API_KEY"] = settings["api_key"]
            cfg.ANTHROPIC_API_KEY = settings["api_key"]
            cfg.NICHE = settings.get("niche", cfg.NICHE)
            cfg.BRAND_VOICE = settings.get("brand_voice", cfg.BRAND_VOICE)
            cfg.TARGET_AUDIENCE = settings.get("target_audience", cfg.TARGET_AUDIENCE)
            cfg.INSTAGRAM_HANDLE = settings.get("instagram_handle", cfg.INSTAGRAM_HANDLE)

            agents_to_run = [only] if only else ["analyst", "strategist", "ideator", "scripter", "publisher"]

            def latest(prefix):
                files = sorted(OUTPUT_DIR.glob(f"{prefix}_*.md"), reverse=True)
                return files[0].read_text() if files else ""

            brief = strategy = ideas = scripts = None

            if "analyst" in agents_to_run:
                yield emit({"type": "agent_start", "agent": "analyst", "message": "El Analista está leyendo tus datos..."})
                # Load auto metrics if available
                auto_data = load_auto_metrics()
                ga4_data = auto_data.get("ga4", {"error": "not configured"}) if auto_data else {"error": "not configured"}
                sc_data = auto_data.get("sc", {"error": "not configured"}) if auto_data else {"error": "not configured"}
                sq_data = auto_data.get("sq", {"error": "not configured"}) if auto_data else {"error": "not configured"}

                brief = data_analyst.run(instagram_metrics, ga4_data, sc_data, sq_data)
                yield emit({"type": "agent_done", "agent": "analyst", "message": "Brief del analista listo"})
            else:
                brief = latest("1_analyst_brief")

            if "strategist" in agents_to_run:
                yield emit({"type": "agent_start", "agent": "strategist", "message": "El Estratega está construyendo el plan semanal..."})
                strategy = content_strategist.run(brief)
                yield emit({"type": "agent_done", "agent": "strategist", "message": "Estrategia lista"})
            else:
                strategy = latest("2_content_strategy")

            if "ideator" in agents_to_run:
                yield emit({"type": "agent_start", "agent": "ideator", "message": "El Ideador está generando 30+ ideas..."})
                ideas = ideator.run(strategy)
                yield emit({"type": "agent_done", "agent": "ideator", "message": "7 ideas ganadoras seleccionadas"})
            else:
                ideas = latest("3_ideas")

            if "scripter" in agents_to_run:
                yield emit({"type": "agent_start", "agent": "scripter", "message": "El Guionista está escribiendo los 7 guiones..."})
                scripts = scripter.run(ideas)
                yield emit({"type": "agent_done", "agent": "scripter", "message": "Guiones listos"})
            else:
                scripts = latest("4_scripts")

            if "publisher" in agents_to_run:
                yield emit({"type": "agent_start", "agent": "publisher", "message": "El Director de Publicación está armando la agenda..."})
                publishing_manager.run(scripts, strategy or latest("2_content_strategy"))
                yield emit({"type": "agent_done", "agent": "publisher", "message": "Plan de publicación listo"})

            yield emit({"type": "done"})

        except Exception as e:
            yield emit({"type": "error", "message": str(e)})

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/outputs")
def outputs():
    outs = get_outputs()
    last_date = outs[0]["date"] if outs else None
    return render_template("outputs.html", active="outputs", outputs=outs, last_run_date=last_date)

@app.route("/download/<filename>")
def download(filename):
    p = OUTPUT_DIR / filename
    if not p.exists():
        return "File not found", 404
    return send_file(str(p), as_attachment=True)


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  La Merced Content Team")
    print("  Abre esto en tu navegador:")
    print("  → http://localhost:8080")
    print("=" * 50 + "\n")
    app.run(debug=False, port=8080)

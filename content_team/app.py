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
    "instagram_account_id": "",
    "instagram_access_token": "",
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


# ── Video tracking ────────────────────────────────────────────────────────────

VIDEOS_FILE = DATA_DIR / "videos.json"


def load_videos() -> list:
    if VIDEOS_FILE.exists():
        return json.loads(VIDEOS_FILE.read_text(encoding="utf-8"))
    return []


def save_videos(videos: list):
    VIDEOS_FILE.write_text(json.dumps(videos, indent=2, ensure_ascii=False), encoding="utf-8")


def get_video(video_id: str):
    return next((v for v in load_videos() if v["id"] == video_id), None)


def update_video(video_id: str, updates: dict):
    videos = load_videos()
    for v in videos:
        if v["id"] == video_id:
            v.update(updates)
    save_videos(videos)


def videos_by_batch(videos: list) -> list:
    batches = {}
    for v in videos:
        bn = v.get("batch_num", 1)
        if bn not in batches:
            batches[bn] = {"num": bn, "date": v.get("batch_date", ""), "videos": []}
        batches[bn]["videos"].append(v)
    return sorted(batches.values(), key=lambda b: b["num"], reverse=True)


def next_batch_info(videos: list) -> tuple[int, int]:
    if not videos:
        return 1, 1
    last = videos[-1]
    last_batch = last.get("batch_num", 1)
    # count videos in last batch
    same_batch = [v for v in videos if v.get("batch_num") == last_batch]
    return last_batch, len(same_batch) + 1


@app.route("/videos")
def videos_list():
    videos = load_videos()
    return render_template("videos.html", active="videos", batches=videos_by_batch(videos))


@app.route("/videos/register", methods=["GET", "POST"])
def video_register():
    settings = load_settings()
    videos = load_videos()

    if request.method == "GET":
        batch_num, video_num = next_batch_info(videos)
        return render_template("video_register.html",
            active="videos",
            today=date.today().isoformat(),
            next_batch=batch_num,
            next_video_in_batch=video_num,
        )

    f = request.form
    batch_num = int(f.get("batch_num", 1))
    video_num = int(f.get("video_num", 1))
    video_id = f"B{batch_num}V{video_num}"

    # Check for duplicate
    if any(v["id"] == video_id for v in videos):
        flash(f"El ID {video_id} ya existe. Cambia el número de batch o vídeo.", "error")
        return redirect(url_for("video_register"))

    if not settings.get("api_key"):
        flash("Configura tu API key en Ajustes antes de registrar vídeos.", "error")
        return redirect(url_for("video_register"))

    # Build base video record
    video = {
        "id": video_id,
        "batch_num": batch_num,
        "batch_date": f.get("date", str(date.today())),
        "idea": f.get("idea", ""),
        "hook": f.get("hook", ""),
        "type_hint": f.get("type_hint", ""),
        "cta_placement": f.get("cta_placement", "before_payoff"),
        "upload_time": f.get("upload_time", "18:00"),
        "date": f.get("date", str(date.today())),
        "type": "",
        "cta_flag": "",
        "cta_flag_reason": "",
        "ai_summary": "",
        "ai_improvement": "",
    }

    # Run AI analysis
    try:
        import config as cfg
        cfg.ANTHROPIC_API_KEY = settings["api_key"]
        from agents.video_analyzer import analyze_registration
        analysis = analyze_registration(
            video["idea"], video["hook"], video["type_hint"], video["cta_placement"]
        )
        video.update({
            "type": analysis.get("type", video["type_hint"] or "Skit"),
            "cta_flag": analysis.get("cta_flag", ""),
            "cta_flag_reason": analysis.get("cta_flag_reason", ""),
            "ai_summary": analysis.get("ai_summary", ""),
            "ai_improvement": analysis.get("ai_improvement", ""),
        })
    except Exception as e:
        flash(f"Advertencia: el análisis IA falló ({e}). Vídeo guardado sin análisis.", "warning")
        video["type"] = video["type_hint"] or "Skit"
        video["cta_flag"] = "correcto" if video["cta_placement"] == "before_payoff" else "problema"

    videos.append(video)
    save_videos(videos)
    flash(f"Vídeo {video_id} registrado correctamente.", "success")
    return redirect(url_for("videos_list"))


@app.route("/videos/<video_id>")
def video_detail(video_id):
    video = get_video(video_id)
    if not video:
        flash("Vídeo no encontrado.", "error")
        return redirect(url_for("videos_list"))
    return render_template("video_detail.html", active="videos", video=video)


@app.route("/videos/<video_id>/metrics/<period>", methods=["GET", "POST"])
def video_metrics(video_id, period):
    if period not in ("24h", "48h"):
        return redirect(url_for("videos_list"))

    video = get_video(video_id)
    if not video:
        flash("Vídeo no encontrado.", "error")
        return redirect(url_for("videos_list"))

    settings = load_settings()

    if request.method == "GET":
        existing = video.get(f"metrics_{period}", {})
        return render_template("video_metrics.html",
            active="videos",
            video=video,
            period=period,
            existing=existing,
        )

    f = request.form
    metrics = {
        "views": int(f.get("views") or 0),
        "shares": int(f.get("shares") or 0),
        "saves": int(f.get("saves") or 0),
        "visitas_perfil": int(f.get("visitas_perfil") or 0),
        "bio_link_taps": int(f.get("bio_link_taps") or 0),
        "follows": int(f.get("follows") or 0),
        "recorded_at": datetime.now().isoformat(),
    }

    # AI decision
    try:
        import config as cfg
        cfg.ANTHROPIC_API_KEY = settings["api_key"]
        from agents.video_analyzer import analyze_24h, analyze_48h

        video_copy = dict(video)
        if period == "24h":
            video_copy["metrics_24h"] = metrics
            result = analyze_24h(video_copy)
            metrics["decision"] = result.get("decision", "ESPERA")
            metrics["razon"] = result.get("razon", "")
        else:
            video_copy["metrics_48h"] = metrics
            result = analyze_48h(video_copy)
            metrics["decision_final"] = result.get("decision_final", "PUBLICA")
            metrics["diagnostico"] = result.get("diagnostico", "")
            metrics["repetir"] = result.get("repetir", False)
            metrics["repetir_razon"] = result.get("repetir_razon", "")
    except Exception as e:
        flash(f"Advertencia: el análisis IA falló ({e}). Métricas guardadas sin decisión.", "warning")
        if period == "24h":
            metrics["decision"] = "ESPERA"
        else:
            metrics["decision_final"] = "PUBLICA"

    update_video(video_id, {f"metrics_{period}": metrics})
    flash(f"Métricas {period} guardadas para {video_id}.", "success")
    return redirect(url_for("videos_list"))



# ── Cowork JSON API ──────────────────────────────────────────────────────────
# Cowork calls these endpoints directly with JSON — no form interaction needed.

@app.route("/api/status")
def api_status():
    """Cowork calls this first to see what needs updating today."""
    videos = load_videos()
    today = str(date.today())

    needs_registration = []   # videos posted today not yet in app
    needs_24h = []
    needs_48h = []

    from datetime import timedelta
    yesterday = str((date.today() - timedelta(days=1)).isoformat())
    two_days_ago = str((date.today() - timedelta(days=2)).isoformat())

    for v in videos:
        if v.get("date") == yesterday and not v.get("metrics_24h"):
            needs_24h.append({"id": v["id"], "hook": v["hook"], "date": v["date"]})
        if v.get("date") == two_days_ago and not v.get("metrics_48h"):
            needs_48h.append({"id": v["id"], "hook": v["hook"], "date": v["date"]})

    # next batch/video numbers for registration
    batch_num, video_num = next_batch_info(videos)

    return jsonify({
        "today": today,
        "yesterday": yesterday,
        "two_days_ago": two_days_ago,
        "next_batch_num": batch_num,
        "next_video_num": video_num,
        "needs_24h_metrics": needs_24h,
        "needs_48h_metrics": needs_48h,
        "message": "Call /api/videos/register to add today's videos, /api/videos/<id>/metrics/<24h|48h> to log metrics.",
    })


@app.route("/api/videos/register", methods=["POST"])
def api_video_register():
    """
    Cowork POSTs one video at a time.
    Body (JSON): { batch_num, video_num, idea, hook, type_hint, cta_placement, date, upload_time }
    cta_placement: "before_payoff" | "after" | "none" | "description_only"
    """
    settings = load_settings()
    if not settings.get("api_key"):
        return jsonify({"error": "No API key configured"}), 400

    data = request.get_json(force=True) or {}
    videos = load_videos()

    batch_num = int(data.get("batch_num", 1))
    video_num = int(data.get("video_num", 1))
    video_id = f"B{batch_num}V{video_num}"

    if any(v["id"] == video_id for v in videos):
        return jsonify({"error": f"{video_id} already exists"}), 409

    video = {
        "id": video_id,
        "batch_num": batch_num,
        "batch_date": data.get("date", str(date.today())),
        "idea": data.get("idea", data.get("hook", "")),
        "hook": data.get("hook", ""),
        "type_hint": data.get("type_hint", ""),
        "cta_placement": data.get("cta_placement", "before_payoff"),
        "upload_time": data.get("upload_time", "18:00"),
        "date": data.get("date", str(date.today())),
        "cowork_description": data.get("cowork_description", ""),
        "cowork_why_worked": data.get("cowork_why_worked", ""),
        "cowork_why_didnt": data.get("cowork_why_didnt", ""),
        "type": "", "cta_flag": "", "cta_flag_reason": "", "ai_summary": "", "ai_improvement": "",
    }

    try:
        import config as cfg
        cfg.ANTHROPIC_API_KEY = settings["api_key"]
        from agents.video_analyzer import analyze_registration
        analysis = analyze_registration(video["idea"], video["hook"], video["type_hint"], video["cta_placement"])
        video.update({
            "type": analysis.get("type", video["type_hint"] or "Skit"),
            "cta_flag": analysis.get("cta_flag", ""),
            "cta_flag_reason": analysis.get("cta_flag_reason", ""),
            "ai_summary": analysis.get("ai_summary", ""),
            "ai_improvement": analysis.get("ai_improvement", ""),
        })
    except Exception as e:
        video["type"] = video["type_hint"] or "Skit"
        video["cta_flag"] = "correcto" if video["cta_placement"] == "before_payoff" else "problema"

    videos.append(video)
    save_videos(videos)
    return jsonify({"ok": True, "id": video_id, "type": video["type"], "cta_flag": video["cta_flag"], "ai_summary": video["ai_summary"]})


@app.route("/api/videos/<video_id>/metrics/<period>", methods=["POST"])
def api_video_metrics(video_id, period):
    """
    Cowork POSTs metrics for a specific video.
    Body (JSON): { views, shares, saves, visitas_perfil, bio_link_taps, follows }
    """
    if period not in ("24h", "48h"):
        return jsonify({"error": "period must be 24h or 48h"}), 400

    settings = load_settings()
    video = get_video(video_id)
    if not video:
        return jsonify({"error": f"Video {video_id} not found"}), 404

    data = request.get_json(force=True) or {}
    metrics = {
        "views": int(data.get("views") or 0),
        "shares": int(data.get("shares") or 0),
        "saves": int(data.get("saves") or 0),
        "visitas_perfil": int(data.get("visitas_perfil") or 0),
        "bio_link_taps": int(data.get("bio_link_taps") or 0),
        "follows": int(data.get("follows") or 0),
        "cowork_performance_notes": data.get("cowork_performance_notes", ""),
        "recorded_at": datetime.now().isoformat(),
    }

    try:
        import config as cfg
        cfg.ANTHROPIC_API_KEY = settings["api_key"]
        from agents.video_analyzer import analyze_24h, analyze_48h
        video_copy = dict(video)
        if period == "24h":
            video_copy["metrics_24h"] = metrics
            result = analyze_24h(video_copy)
            metrics["decision"] = result.get("decision", "ESPERA")
            metrics["razon"] = result.get("razon", "")
        else:
            video_copy["metrics_48h"] = metrics
            result = analyze_48h(video_copy)
            metrics["decision_final"] = result.get("decision_final", "PUBLICA")
            metrics["diagnostico"] = result.get("diagnostico", "")
            metrics["repetir"] = result.get("repetir", False)
            metrics["repetir_razon"] = result.get("repetir_razon", "")
    except Exception:
        metrics["decision"] = "ESPERA" if period == "24h" else None
        metrics["decision_final"] = "PUBLICA" if period == "48h" else None

    update_video(video_id, {f"metrics_{period}": metrics})
    return jsonify({"ok": True, "id": video_id, "period": period, "metrics": metrics})


# ── Instagram weekly report ───────────────────────────────────────────────────

INSTAGRAM_FILE = DATA_DIR / "instagram_weekly.json"

COWORK_PROMPT = """Conecta con mi cuenta de Instagram Business y extrae los datos de los ÚLTIMOS 7 DÍAS.
Necesito que me des la siguiente información estructurada — responde exactamente con estos campos:

1. CUENTA
   - Seguidores totales actuales
   - Seguidores ganados esta semana (diferencia 7 días)
   - Alcance total (reach) de la semana
   - Impresiones totales de la semana
   - Visitas al perfil totales de la semana
   - Clics al enlace de bio (link in bio) totales de la semana

2. TOP 3 REELS (los 3 con más visitas al perfil)
   Para cada uno:
   - Fecha de publicación
   - Hook / primer texto o situación visible en el vídeo
   - Reproducciones (views)
   - Visitas al perfil generadas por este reel
   - Likes, comentarios, shares, guardados
   - Porcentaje de retención media (si está disponible)

3. PEOR REEL DE LA SEMANA (el que menos visitas al perfil generó)
   - Hook
   - Reproducciones
   - Visitas al perfil
   - Likes

4. ENGAGEMENT RATE medio de la semana (si está disponible)

5. FORMATO QUE MEJOR FUNCIONÓ esta semana (Reel largo >30s / Reel corto <15s / Carrusel / Foto)

Devuelve todo en texto claro y ordenado para que yo lo pueda copiar en mi app."""


def load_instagram_weekly():
    if INSTAGRAM_FILE.exists():
        return json.loads(INSTAGRAM_FILE.read_text())
    return {}


def save_instagram_weekly(data):
    INSTAGRAM_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


@app.route("/instagram", methods=["GET", "POST"])
def instagram_page():
    saved = load_instagram_weekly()
    report = saved.get("report")

    # Clear report if user wants to update
    if request.args.get("reset"):
        saved.pop("report", None)
        save_instagram_weekly(saved)
        return redirect(url_for("instagram_page"))

    if request.method == "POST":
        settings = load_settings()
        if not settings.get("api_key"):
            flash("Configura tu API key de Claude en Ajustes primero.", "error")
            return redirect(url_for("instagram_page"))

        f = request.form

        top_posts = []
        for i in range(3):
            top_posts.append({
                "type": f.get(f"top_type_{i}", ""),
                "hook": f.get(f"top_hook_{i}", ""),
                "views": int(f.get(f"top_views_{i}") or 0),
                "profile_visits": int(f.get(f"top_profile_visits_{i}") or 0),
                "likes": int(f.get(f"top_likes_{i}") or 0),
                "comments": int(f.get(f"top_comments_{i}") or 0),
                "shares": int(f.get(f"top_shares_{i}") or 0),
                "saves": int(f.get(f"top_saves_{i}") or 0),
            })

        data = {
            "week": str(date.today()),
            "followers_total": int(f.get("followers_total") or 0),
            "followers_gained": int(f.get("followers_gained") or 0),
            "reach": int(f.get("reach") or 0),
            "impressions": int(f.get("impressions") or 0),
            "profile_visits": int(f.get("profile_visits") or 0),
            "bio_link_clicks": int(f.get("bio_link_clicks") or 0),
            "top_posts": top_posts,
            "worst_post": {
                "type": f.get("worst_type", ""),
                "hook": f.get("worst_hook", ""),
                "views": int(f.get("worst_views") or 0),
                "profile_visits": int(f.get("worst_profile_visits") or 0),
                "reason": f.get("worst_reason", ""),
            },
            "ventas_configurador": int(f.get("ventas_configurador") or 0),
            "leads_whatsapp": int(f.get("leads_whatsapp") or 0),
            "competitor": {
                "handle": f.get("comp_handle", ""),
                "hook": f.get("comp_hook", ""),
                "views": f.get("comp_views", ""),
                "format": f.get("comp_format", ""),
            },
            "notes": f.get("notes", ""),
        }

        try:
            import config as cfg
            cfg.ANTHROPIC_API_KEY = settings["api_key"]
            from agents.instagram_analyzer import analyze_week
            report = analyze_week(data)
            data["report"] = report
            save_instagram_weekly(data)
            flash("Análisis completado.", "success")
        except Exception as e:
            flash(f"Error al analizar: {e}", "error")
            save_instagram_weekly(data)
            return redirect(url_for("instagram_page"))

        return redirect(url_for("instagram_page"))

    return render_template("instagram.html",
        active="instagram",
        cowork_prompt=COWORK_PROMPT,
        saved=saved,
        report=report,
    )


@app.route("/api/sync", methods=["POST"])
def api_sync():
    """Manual sync trigger — runs the same job as the daily scheduler."""
    from scheduler import run_daily_sync
    ctx = _scheduler_context()
    try:
        results = run_daily_sync(ctx)
        return jsonify({"ok": True, "results": results})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync-log")
def api_sync_log():
    log_path = DATA_DIR / "sync_log.json"
    if log_path.exists():
        return jsonify(json.loads(log_path.read_text()))
    return jsonify([])


def _scheduler_context():
    return {
        "settings": load_settings,
        "save_settings": save_settings,
        "load_videos": load_videos,
        "save_videos": save_videos,
        "get_video": get_video,
        "update_video": update_video,
        "next_batch_info": next_batch_info,
        "DATA_DIR": str(DATA_DIR),
    }


def start_scheduler():
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from scheduler import run_daily_sync
        ctx = _scheduler_context()
        sched = BackgroundScheduler()
        sched.add_job(lambda: run_daily_sync(ctx), "cron", hour=21, minute=0)
        sched.start()
        print("  ✓ Sync automático activo — corre cada día a las 21:00")
    except ImportError:
        print("  ⚠ APScheduler no instalado — sync manual disponible en /api/sync")
    except Exception as e:
        print(f"  ⚠ Scheduler error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  La Merced Content Team")
    print("  Abre esto en tu navegador:")
    print("  → http://localhost:8080")
    print("=" * 50 + "\n")
    start_scheduler()
    app.run(debug=False, port=8080)

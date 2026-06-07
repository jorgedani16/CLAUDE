"""
Daily sync scheduler — runs at 21:00 every day.
Pulls Instagram data and auto-fills video metrics.
Started automatically when app.py boots.
"""
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

log = logging.getLogger("scheduler")


def run_daily_sync(app_context: dict):
    """
    Main daily job. Called by APScheduler at 21:00.
    app_context: { settings, load_videos, save_videos, get_video, update_video,
                   next_batch_info, DATA_DIR, anthropic_key }
    """
    settings = app_context["settings"]()
    account_id = settings.get("instagram_account_id", "")
    token = settings.get("instagram_access_token", "")

    if not account_id or not token:
        log.info("Instagram not configured — skipping sync")
        return

    log.info("Daily sync started")
    results = {"date": str(date.today()), "registered": [], "metrics_24h": [], "metrics_48h": [], "errors": []}

    try:
        from integrations.instagram import pull_recent_posts, refresh_token

        # Refresh token silently (keeps it alive beyond 60 days)
        new_token = refresh_token(token)
        if new_token != token:
            s = settings.copy()
            s["instagram_access_token"] = new_token
            app_context["save_settings"](s)
            token = new_token

        posts = pull_recent_posts(account_id, token, days=3)
        videos = app_context["load_videos"]()

        today = str(date.today())
        yesterday = str((date.today() - timedelta(days=1)))
        two_days_ago = str((date.today() - timedelta(days=2)))

        # ── Register today's new videos ─────────────────────────────────────
        today_posts = [p for p in posts if p["date"] == today]
        existing_dates = [v for v in videos if v.get("date") == today]
        new_posts = today_posts[len(existing_dates):]  # posts not yet registered

        if new_posts:
            batch_num, video_num = app_context["next_batch_info"](videos)
            api_key = settings.get("api_key", "")

            for post in new_posts:
                video_id = f"B{batch_num}V{video_num}"
                hook = (post["caption"].split("\n")[0] or post["caption"])[:100]
                video = {
                    "id": video_id,
                    "batch_num": batch_num,
                    "batch_date": today,
                    "idea": post["caption"][:200] or hook,
                    "hook": hook,
                    "type_hint": "",
                    "cta_placement": "before_payoff",
                    "upload_time": post["time"],
                    "date": today,
                    "ig_id": post["ig_id"],
                    "permalink": post["permalink"],
                    "type": "", "cta_flag": "", "cta_flag_reason": "",
                    "ai_summary": "", "ai_improvement": "",
                }
                if api_key:
                    try:
                        import config as cfg
                        cfg.ANTHROPIC_API_KEY = api_key
                        from agents.video_analyzer import analyze_registration
                        analysis = analyze_registration(video["idea"], video["hook"], "", "before_payoff")
                        video.update({
                            "type": analysis.get("type", "Skit"),
                            "cta_flag": analysis.get("cta_flag", ""),
                            "cta_flag_reason": analysis.get("cta_flag_reason", ""),
                            "ai_summary": analysis.get("ai_summary", ""),
                            "ai_improvement": analysis.get("ai_improvement", ""),
                        })
                    except Exception as e:
                        video["type"] = "Skit"
                        video["cta_flag"] = "correcto"
                        results["errors"].append(f"AI analysis failed for {video_id}: {e}")

                videos.append(video)
                results["registered"].append(video_id)
                video_num += 1

            app_context["save_videos"](videos)

        # ── 24h metrics ────────────────────────────────────────────────────
        yesterday_posts = {p["ig_id"]: p for p in posts if p["date"] == yesterday}
        for v in videos:
            if v.get("date") == yesterday and not v.get("metrics_24h"):
                ig_id = v.get("ig_id")
                post = yesterday_posts.get(ig_id)
                if not post:
                    # Try matching by position in day
                    day_vids = sorted([x for x in videos if x.get("date") == yesterday], key=lambda x: x["id"])
                    day_posts = [p for p in posts if p["date"] == yesterday]
                    idx = next((i for i, x in enumerate(day_vids) if x["id"] == v["id"]), None)
                    if idx is not None and idx < len(day_posts):
                        post = day_posts[idx]

                if post:
                    metrics = {
                        "views": post["views"],
                        "shares": post["shares"],
                        "saves": post["saves"],
                        "visitas_perfil": post["profile_visits"],
                        "bio_link_taps": post["bio_link_taps"],
                        "follows": post["follows"],
                        "recorded_at": datetime.now().isoformat(),
                    }
                    api_key = settings.get("api_key", "")
                    if api_key:
                        try:
                            import config as cfg
                            cfg.ANTHROPIC_API_KEY = api_key
                            from agents.video_analyzer import analyze_24h
                            v_copy = dict(v)
                            v_copy["metrics_24h"] = metrics
                            result = analyze_24h(v_copy)
                            metrics["decision"] = result.get("decision", "ESPERA")
                            metrics["razon"] = result.get("razon", "")
                        except Exception as e:
                            metrics["decision"] = "ESPERA"
                            results["errors"].append(f"24h AI failed for {v['id']}: {e}")
                    else:
                        metrics["decision"] = "ESPERA"

                    app_context["update_video"](v["id"], {"metrics_24h": metrics, "ig_id": post["ig_id"]})
                    results["metrics_24h"].append({"id": v["id"], "decision": metrics.get("decision")})

        # ── 48h metrics ────────────────────────────────────────────────────
        two_days_posts = {p["ig_id"]: p for p in posts if p["date"] == two_days_ago}
        videos = app_context["load_videos"]()  # reload after 24h updates
        for v in videos:
            if v.get("date") == two_days_ago and not v.get("metrics_48h"):
                ig_id = v.get("ig_id")
                post = two_days_posts.get(ig_id)
                if not post:
                    day_vids = sorted([x for x in videos if x.get("date") == two_days_ago], key=lambda x: x["id"])
                    day_posts = [p for p in posts if p["date"] == two_days_ago]
                    idx = next((i for i, x in enumerate(day_vids) if x["id"] == v["id"]), None)
                    if idx is not None and idx < len(day_posts):
                        post = day_posts[idx]

                if post:
                    metrics = {
                        "views": post["views"],
                        "shares": post["shares"],
                        "saves": post["saves"],
                        "visitas_perfil": post["profile_visits"],
                        "bio_link_taps": post["bio_link_taps"],
                        "follows": post["follows"],
                        "recorded_at": datetime.now().isoformat(),
                    }
                    api_key = settings.get("api_key", "")
                    if api_key:
                        try:
                            import config as cfg
                            cfg.ANTHROPIC_API_KEY = api_key
                            from agents.video_analyzer import analyze_48h
                            v_copy = dict(v)
                            v_copy["metrics_48h"] = metrics
                            result = analyze_48h(v_copy)
                            metrics["decision_final"] = result.get("decision_final", "PUBLICA")
                            metrics["diagnostico"] = result.get("diagnostico", "")
                            metrics["repetir"] = result.get("repetir", False)
                            metrics["repetir_razon"] = result.get("repetir_razon", "")
                        except Exception as e:
                            metrics["decision_final"] = "PUBLICA"
                            results["errors"].append(f"48h AI failed for {v['id']}: {e}")
                    else:
                        metrics["decision_final"] = "PUBLICA"

                    app_context["update_video"](v["id"], {"metrics_48h": metrics})
                    results["metrics_48h"].append({"id": v["id"], "decision_final": metrics.get("decision_final")})

    except Exception as e:
        results["errors"].append(str(e))
        log.error(f"Sync error: {e}")

    # Save sync log
    log_path = Path(app_context["DATA_DIR"]) / "sync_log.json"
    try:
        history = json.loads(log_path.read_text()) if log_path.exists() else []
        history.insert(0, results)
        log_path.write_text(json.dumps(history[:30], indent=2, ensure_ascii=False))
    except Exception:
        pass

    log.info(f"Sync done: {results}")
    return results

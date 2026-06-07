"""
Instagram Graph API integration.
Pulls last 7 days of account + post metrics.

Requirements:
- INSTAGRAM_ACCOUNT_ID: your Instagram Business Account ID
- INSTAGRAM_ACCESS_TOKEN: long-lived access token from Meta

How to get these:
1. Go to developers.facebook.com → My Apps → Create App
2. Add Instagram Graph API product
3. Connect your Instagram Business account
4. Generate a long-lived access token (valid 60 days, can be refreshed)
"""
import requests
from datetime import datetime, timedelta, date


BASE_URL = "https://graph.instagram.com/v21.0"


def pull(account_id: str, access_token: str) -> dict:
    if not account_id or not access_token:
        return {"error": "not configured"}

    try:
        since = int((datetime.now() - timedelta(days=7)).timestamp())
        until = int(datetime.now().timestamp())
        params = {"access_token": access_token}

        # ── Account-level insights ──────────────────────────────────────────
        metrics = [
            "reach", "impressions", "profile_views",
            "accounts_engaged", "follower_count",
        ]
        r = requests.get(
            f"{BASE_URL}/{account_id}/insights",
            params={
                **params,
                "metric": ",".join(metrics),
                "period": "day",
                "since": since,
                "until": until,
            },
            timeout=15,
        )
        r.raise_for_status()
        insights_raw = r.json().get("data", [])

        def sum_metric(name):
            for m in insights_raw:
                if m["name"] == name:
                    return sum(v["value"] for v in m.get("values", []))
            return 0

        account_insights = {
            "reach_7d": sum_metric("reach"),
            "impressions_7d": sum_metric("impressions"),
            "profile_views_7d": sum_metric("profile_views"),
            "accounts_engaged_7d": sum_metric("accounts_engaged"),
        }

        # ── Follower count (latest) ─────────────────────────────────────────
        r2 = requests.get(
            f"{BASE_URL}/{account_id}",
            params={**params, "fields": "followers_count,username"},
            timeout=10,
        )
        r2.raise_for_status()
        account_data = r2.json()
        followers = account_data.get("followers_count", 0)
        username = account_data.get("username", "")

        # ── Recent media ────────────────────────────────────────────────────
        r3 = requests.get(
            f"{BASE_URL}/{account_id}/media",
            params={
                **params,
                "fields": "id,caption,media_type,timestamp,permalink",
                "limit": 20,
            },
            timeout=15,
        )
        r3.raise_for_status()
        media_list = r3.json().get("data", [])

        # Filter to last 7 days
        cutoff = datetime.now() - timedelta(days=7)
        recent_media = [
            m for m in media_list
            if datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None) > cutoff
        ]

        # ── Per-post insights ───────────────────────────────────────────────
        post_insights = []
        for media in recent_media[:10]:  # max 10 posts
            media_id = media["id"]
            try:
                ri = requests.get(
                    f"{BASE_URL}/{media_id}/insights",
                    params={
                        **params,
                        "metric": "reach,impressions,likes,comments,shares,saved,video_views,profile_visits,follows",
                    },
                    timeout=10,
                )
                ri.raise_for_status()
                ins = {i["name"]: i["values"][0]["value"] if i.get("values") else i.get("value", 0)
                       for i in ri.json().get("data", [])}
                post_insights.append({
                    "id": media_id,
                    "caption_preview": (media.get("caption", "") or "")[:80],
                    "type": media.get("media_type", ""),
                    "timestamp": media["timestamp"],
                    "permalink": media.get("permalink", ""),
                    "reach": ins.get("reach", 0),
                    "impressions": ins.get("impressions", 0),
                    "likes": ins.get("likes", 0),
                    "comments": ins.get("comments", 0),
                    "shares": ins.get("shares", 0),
                    "saves": ins.get("saved", 0),
                    "views": ins.get("video_views", 0),
                    "profile_visits": ins.get("profile_visits", 0),
                    "follows": ins.get("follows", 0),
                })
            except Exception:
                continue

        # Sort by profile_visits (key metric)
        post_insights.sort(key=lambda p: p["profile_visits"], reverse=True)

        top_posts = post_insights[:3]
        worst_post = post_insights[-1] if post_insights else {}

        # Avg profile visits per reel
        reel_posts = [p for p in post_insights if p["type"] == "VIDEO"]
        avg_profile_visits = (
            round(sum(p["profile_visits"] for p in reel_posts) / len(reel_posts))
            if reel_posts else 0
        )

        return {
            "username": username,
            "followers": followers,
            "reach_7d": account_insights["reach_7d"],
            "impressions_7d": account_insights["impressions_7d"],
            "profile_views_7d": account_insights["profile_views_7d"],
            "accounts_engaged_7d": account_insights["accounts_engaged_7d"],
            "avg_profile_visits_per_reel": avg_profile_visits,
            "top_posts": top_posts,
            "worst_post": worst_post,
            "total_posts_this_week": len(recent_media),
        }

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return {"error": "Token inválido o expirado. Genera uno nuevo en developers.facebook.com"}
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}

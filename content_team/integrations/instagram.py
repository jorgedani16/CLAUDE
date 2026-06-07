"""
Instagram Graph API — sync engine.
Pulls recent posts and matches them to registered videos by date.
Runs daily at 21:00 via the scheduler.
"""
import requests
from datetime import datetime, timedelta, date


BASE_URL = "https://graph.instagram.com/v21.0"


def _post_metrics(media_id: str, token: str) -> dict:
    try:
        r = requests.get(
            f"{BASE_URL}/{media_id}/insights",
            params={
                "access_token": token,
                "metric": "reach,impressions,likes,comments,shares,saved,video_views,profile_visits,follows",
            },
            timeout=10,
        )
        r.raise_for_status()
        ins = {}
        for item in r.json().get("data", []):
            val = item["values"][0]["value"] if item.get("values") else item.get("value", 0)
            ins[item["name"]] = val
        return ins
    except Exception:
        return {}


def pull_recent_posts(account_id: str, token: str, days: int = 7) -> list:
    """Returns list of recent posts with metrics. Used by sync engine."""
    if not account_id or not token:
        return []
    try:
        r = requests.get(
            f"{BASE_URL}/{account_id}/media",
            params={
                "access_token": token,
                "fields": "id,caption,media_type,timestamp,permalink",
                "limit": 30,
            },
            timeout=15,
        )
        r.raise_for_status()
        media_list = r.json().get("data", [])

        cutoff = datetime.now() - timedelta(days=days)
        posts = []
        for m in media_list:
            ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")).replace(tzinfo=None)
            if ts < cutoff:
                continue
            ins = _post_metrics(m["id"], token)
            posts.append({
                "ig_id": m["id"],
                "caption": (m.get("caption") or "")[:200],
                "media_type": m.get("media_type", ""),
                "timestamp": m["timestamp"],
                "date": ts.strftime("%Y-%m-%d"),
                "time": ts.strftime("%H:%M"),
                "permalink": m.get("permalink", ""),
                "views": ins.get("video_views", 0),
                "shares": ins.get("shares", 0),
                "saves": ins.get("saved", 0),
                "profile_visits": ins.get("profile_visits", 0),
                "bio_link_taps": 0,  # not available at post level
                "follows": ins.get("follows", 0),
                "likes": ins.get("likes", 0),
                "comments": ins.get("comments", 0),
                "reach": ins.get("reach", 0),
            })
        return sorted(posts, key=lambda p: p["timestamp"])
    except requests.exceptions.HTTPError as e:
        return []
    except Exception:
        return []


def pull_account(account_id: str, token: str) -> dict:
    """Weekly account-level summary for the Instagram report page."""
    if not account_id or not token:
        return {"error": "not configured"}
    try:
        since = int((datetime.now() - timedelta(days=7)).timestamp())
        until = int(datetime.now().timestamp())

        r = requests.get(
            f"{BASE_URL}/{account_id}/insights",
            params={
                "access_token": token,
                "metric": "reach,impressions,profile_views,accounts_engaged",
                "period": "day",
                "since": since,
                "until": until,
            },
            timeout=15,
        )
        r.raise_for_status()
        raw = r.json().get("data", [])

        def s(name):
            for m in raw:
                if m["name"] == name:
                    return sum(v["value"] for v in m.get("values", []))
            return 0

        r2 = requests.get(
            f"{BASE_URL}/{account_id}",
            params={"access_token": token, "fields": "followers_count,username"},
            timeout=10,
        )
        r2.raise_for_status()
        acct = r2.json()

        posts = pull_recent_posts(account_id, token, days=7)
        video_posts = [p for p in posts if p["media_type"] == "VIDEO"]
        avg_pv = (
            round(sum(p["profile_visits"] for p in video_posts) / len(video_posts))
            if video_posts else 0
        )
        top = sorted(posts, key=lambda p: p["profile_visits"], reverse=True)

        return {
            "username": acct.get("username", ""),
            "followers": acct.get("followers_count", 0),
            "reach_7d": s("reach"),
            "impressions_7d": s("impressions"),
            "profile_views_7d": s("profile_views"),
            "accounts_engaged_7d": s("accounts_engaged"),
            "avg_profile_visits_per_reel": avg_pv,
            "top_posts": top[:3],
            "worst_post": top[-1] if top else {},
            "total_posts_this_week": len(posts),
        }
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return {"error": "Token inválido o expirado — genera uno nuevo en developers.facebook.com"}
        return {"error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def refresh_token(token: str) -> str:
    """Refresh a long-lived token (valid 60 days). Returns new token or original."""
    try:
        r = requests.get(
            "https://graph.instagram.com/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": token},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("access_token", token)
    except Exception:
        return token

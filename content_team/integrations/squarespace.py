from datetime import date, timedelta, timezone, datetime
import requests


def pull(api_key: str) -> dict:
    if not api_key:
        return {"error": "not configured"}
    try:
        seven_days_ago = (
            datetime.now(timezone.utc) - timedelta(days=7)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "La-Merced-Content-Team/1.0",
        }
        params = {"fulfilledAfter": seven_days_ago}

        resp = requests.get(
            "https://api.squarespace.com/1.0/commerce/orders",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        orders_raw = data.get("result", [])
        orders_count = len(orders_raw)
        total_revenue = sum(
            float(o.get("grandTotal", {}).get("value", 0)) for o in orders_raw
        )
        avg_order_value = round(total_revenue / orders_count, 2) if orders_count > 0 else 0.0

        last_10 = orders_raw[:10]
        orders_summary = [
            {
                "id": o.get("id", ""),
                "total": float(o.get("grandTotal", {}).get("value", 0)),
                "date": o.get("fulfilledOn", o.get("createdOn", "")),
            }
            for o in last_10
        ]

        return {
            "orders_count": orders_count,
            "total_revenue_eur": round(total_revenue, 2),
            "avg_order_value_eur": avg_order_value,
            "orders": orders_summary,
        }

    except Exception as e:
        return {"error": str(e)}

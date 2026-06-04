from datetime import date, timedelta


def pull(site_url: str, credentials_path: str) -> dict:
    if not site_url or not credentials_path:
        return {"error": "not configured"}
    try:
        import google.oauth2.service_account as sa
        from googleapiclient.discovery import build

        credentials = sa.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=credentials)

        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=7)).isoformat()

        # Overall totals
        overview = (
            service.searchanalytics()
            .query(
                siteUrl=site_url,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": [],
                },
            )
            .execute()
        )

        rows_overview = overview.get("rows", [{}])
        totals = rows_overview[0] if rows_overview else {}
        total_clicks = int(totals.get("clicks", 0))
        total_impressions = int(totals.get("impressions", 0))
        avg_ctr = round(totals.get("ctr", 0.0) * 100, 2)
        avg_position = round(totals.get("position", 0.0), 1)

        # Top queries
        queries_resp = (
            service.searchanalytics()
            .query(
                siteUrl=site_url,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["query"],
                    "rowLimit": 10,
                    "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
                },
            )
            .execute()
        )
        top_queries = [
            {
                "query": r["keys"][0],
                "clicks": int(r.get("clicks", 0)),
                "impressions": int(r.get("impressions", 0)),
            }
            for r in queries_resp.get("rows", [])
        ]

        # Top pages
        pages_resp = (
            service.searchanalytics()
            .query(
                siteUrl=site_url,
                body={
                    "startDate": start_date,
                    "endDate": end_date,
                    "dimensions": ["page"],
                    "rowLimit": 5,
                    "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
                },
            )
            .execute()
        )
        top_pages = [
            {"page": r["keys"][0], "clicks": int(r.get("clicks", 0))}
            for r in pages_resp.get("rows", [])
        ]

        return {
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_ctr_pct": avg_ctr,
            "avg_position": avg_position,
            "top_queries": top_queries,
            "top_pages": top_pages,
        }

    except Exception as e:
        return {"error": str(e)}

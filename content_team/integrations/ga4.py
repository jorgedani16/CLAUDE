from datetime import date, timedelta


def pull(property_id: str, credentials_path: str) -> dict:
    if not property_id or not credentials_path:
        return {"error": "not configured"}
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest,
            DateRange,
            Dimension,
            Metric,
            FilterExpression,
            Filter,
            FilterExpressionList,
        )
        import google.oauth2.service_account as sa

        credentials = sa.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=credentials)

        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=7)).isoformat()
        date_range = DateRange(start_date=start_date, end_date=end_date)

        # Sessions by page path
        page_report = client.run_report(
            RunReportRequest(
                property=f"properties/{property_id}",
                date_ranges=[date_range],
                dimensions=[Dimension(name="pagePath"), Dimension(name="sessionDefaultChannelGrouping")],
                metrics=[Metric(name="sessions")],
            )
        )

        configurator_visits = 0
        configurator_conversions = 0
        source_map = {}
        landing_map = {}

        for row in page_report.rows:
            page = row.dimension_values[0].value
            channel = row.dimension_values[1].value
            sessions = int(row.metric_values[0].value)

            if "configurador" in page or "pedido" in page:
                configurator_visits += sessions
                if "pedido-confirmado" in page:
                    configurator_conversions += sessions

            source_map[channel] = source_map.get(channel, 0) + sessions
            landing_map[page] = landing_map.get(page, 0) + sessions

        conversion_rate = (
            round(configurator_conversions / configurator_visits * 100, 2)
            if configurator_visits > 0
            else 0.0
        )

        top_sources = sorted(source_map.items(), key=lambda x: x[1], reverse=True)[:5]
        top_pages = sorted(landing_map.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "configurator_visits": configurator_visits,
            "configurator_conversions": configurator_conversions,
            "conversion_rate_pct": conversion_rate,
            "top_traffic_sources": [{"source": s, "sessions": n} for s, n in top_sources],
            "top_landing_pages": [{"page": p, "sessions": n} for p, n in top_pages],
        }

    except Exception as e:
        return {"error": str(e)}

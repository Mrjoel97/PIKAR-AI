"""Google Search Console & Analytics Tool.

Fetches SEO performance data from Google Search Console (search queries,
click-through rates, indexing status) and website traffic from Google
Analytics 4 (GA4).

Auth approaches:
1. Service account JSON (for server-to-server access)
2. User OAuth via connected_accounts (for per-user data)
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.mcp.config import get_mcp_config
from app.mcp.security.audit_logger import log_mcp_call

logger = logging.getLogger(__name__)


class GoogleSEOTool:
    """Fetches SEO data from Google Search Console and GA4."""

    def __init__(self):
        self.config = get_mcp_config()
        self._credentials = None

    def _get_service_account_token(self) -> Optional[str]:
        """Get access token from service account credentials.

        Uses google-auth library if available, falls back to manual JWT.
        """
        sa_json = self.config.google_seo_service_account_json
        if not sa_json:
            return None

        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            if self._credentials is None or not self._credentials.valid:
                info = json.loads(sa_json) if isinstance(sa_json, str) else sa_json
                self._credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=[
                        "https://www.googleapis.com/auth/webmasters.readonly",
                        "https://www.googleapis.com/auth/analytics.readonly",
                    ],
                )
            if not self._credentials.valid:
                self._credentials.refresh(Request())
            return self._credentials.token
        except ImportError:
            logger.warning("google-auth not installed. Install with: pip install google-auth")
            return None
        except Exception as e:
            logger.error("Failed to get service account token: %s", e)
            return None

    def _get_token(self, user_id: Optional[str] = None) -> Optional[str]:
        """Get access token, preferring user OAuth, falling back to service account."""
        if user_id:
            from app.social.connector import get_social_connector
            connector = get_social_connector()
            token = connector.get_access_token(user_id, "google_search_console")
            if token:
                return token

        return self._get_service_account_token()

    async def get_search_performance(
        self,
        site_url: str,
        start_date: str,
        end_date: str,
        dimensions: Optional[List[str]] = None,
        row_limit: int = 100,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query Google Search Console for search performance data.

        Args:
            site_url: The site URL as registered in GSC (e.g. "https://example.com").
            start_date: Start date in YYYY-MM-DD format.
            end_date: End date in YYYY-MM-DD format.
            dimensions: Grouping dimensions — "query", "page", "country", "device", "date".
            row_limit: Max rows to return (default: 100, max: 25000).
            user_id: Optional user ID for OAuth-based access.

        Returns:
            Dict with rows containing clicks, impressions, CTR, and position per dimension.
        """
        token = self._get_token(user_id)
        if not token:
            return {
                "success": False,
                "error": "Google Search Console not configured. Set GOOGLE_SEO_SERVICE_ACCOUNT_JSON or connect via OAuth.",
            }

        if dimensions is None:
            dimensions = ["query"]

        start_time = time.time()
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": min(row_limit, 25000),
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # URL-encode the site_url for the API path
                encoded_site = site_url.replace(":", "%3A").replace("/", "%2F")
                resp = await client.post(
                    f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                duration_ms = int((time.time() - start_time) * 1000)

                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"GSC API error ({resp.status_code}): {resp.text}",
                        "duration_ms": duration_ms,
                    }

                data = resp.json()
                rows = data.get("rows", [])

                return {
                    "success": True,
                    "site_url": site_url,
                    "date_range": {"start": start_date, "end": end_date},
                    "dimensions": dimensions,
                    "total_rows": len(rows),
                    "rows": [
                        {
                            "keys": row.get("keys", []),
                            "clicks": row.get("clicks", 0),
                            "impressions": row.get("impressions", 0),
                            "ctr": round(row.get("ctr", 0) * 100, 2),
                            "position": round(row.get("position", 0), 1),
                        }
                        for row in rows
                    ],
                    "duration_ms": duration_ms,
                }
        except Exception as e:
            return {"success": False, "error": f"GSC query failed: {e!s}"}

    async def get_top_queries(
        self,
        site_url: str,
        limit: int = 25,
        days: int = 28,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get top search queries driving traffic to the site.

        Convenience method that calls get_search_performance with
        query dimension and sorts by clicks.

        Args:
            site_url: The site URL.
            limit: Number of top queries to return.
            days: Lookback period in days.
            user_id: Optional user ID.

        Returns:
            Dict with top queries ranked by clicks.
        """
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = await self.get_search_performance(
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["query"],
            row_limit=limit,
            user_id=user_id,
        )

        if result.get("success") and result.get("rows"):
            result["rows"] = sorted(
                result["rows"],
                key=lambda r: r.get("clicks", 0),
                reverse=True,
            )[:limit]
            result["summary"] = {
                "total_clicks": sum(r.get("clicks", 0) for r in result["rows"]),
                "total_impressions": sum(r.get("impressions", 0) for r in result["rows"]),
                "avg_ctr": round(
                    sum(r.get("ctr", 0) for r in result["rows"]) / max(len(result["rows"]), 1), 2
                ),
                "avg_position": round(
                    sum(r.get("position", 0) for r in result["rows"]) / max(len(result["rows"]), 1), 1
                ),
            }

        return result

    async def get_top_pages(
        self,
        site_url: str,
        limit: int = 25,
        days: int = 28,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get top-performing pages by organic search traffic.

        Args:
            site_url: The site URL.
            limit: Number of top pages to return.
            days: Lookback period in days.
            user_id: Optional user ID.

        Returns:
            Dict with top pages ranked by clicks.
        """
        from datetime import datetime, timedelta

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = await self.get_search_performance(
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            dimensions=["page"],
            row_limit=limit,
            user_id=user_id,
        )

        if result.get("success") and result.get("rows"):
            result["rows"] = sorted(
                result["rows"],
                key=lambda r: r.get("clicks", 0),
                reverse=True,
            )[:limit]

        return result

    async def get_indexing_status(
        self,
        site_url: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get indexing coverage status from Google Search Console.

        Args:
            site_url: The site URL as registered in GSC.
            user_id: Optional user ID.

        Returns:
            Dict with sitemaps and their indexing status.
        """
        token = self._get_token(user_id)
        if not token:
            return {"success": False, "error": "Google Search Console not configured."}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                encoded_site = site_url.replace(":", "%3A").replace("/", "%2F")
                resp = await client.get(
                    f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/sitemaps",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    return {"success": False, "error": f"GSC API error ({resp.status_code}): {resp.text}"}

                sitemaps = resp.json().get("sitemap", [])
                return {
                    "success": True,
                    "site_url": site_url,
                    "sitemaps": [
                        {
                            "path": sm.get("path"),
                            "type": sm.get("type"),
                            "last_submitted": sm.get("lastSubmitted"),
                            "last_downloaded": sm.get("lastDownloaded"),
                            "warnings": sm.get("warnings", 0),
                            "errors": sm.get("errors", 0),
                            "contents": sm.get("contents", []),
                        }
                        for sm in sitemaps
                    ],
                }
        except Exception as e:
            return {"success": False, "error": f"Indexing status failed: {e!s}"}

    async def get_ga4_traffic(
        self,
        property_id: str,
        start_date: str = "30daysAgo",
        end_date: str = "today",
        dimensions: Optional[List[str]] = None,
        metrics: Optional[List[str]] = None,
        limit: int = 100,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query Google Analytics 4 Data API for website traffic data.

        Args:
            property_id: GA4 property ID (e.g. "properties/123456789").
            start_date: Start date (YYYY-MM-DD or relative like "30daysAgo").
            end_date: End date (YYYY-MM-DD or "today").
            dimensions: GA4 dimensions (e.g. ["date", "sessionSource", "pagePath"]).
            metrics: GA4 metrics (e.g. ["sessions", "activeUsers", "screenPageViews"]).
            limit: Max rows to return.
            user_id: Optional user ID.

        Returns:
            Dict with traffic data rows.
        """
        token = self._get_token(user_id)
        if not token:
            return {"success": False, "error": "Google Analytics not configured."}

        if dimensions is None:
            dimensions = ["date"]
        if metrics is None:
            metrics = ["sessions", "activeUsers", "screenPageViews", "bounceRate"]

        # Ensure property_id has the right format
        if not property_id.startswith("properties/"):
            property_id = f"properties/{property_id}"

        start_time = time.time()
        payload = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": d} for d in dimensions],
            "metrics": [{"name": m} for m in metrics],
            "limit": min(limit, 10000),
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                duration_ms = int((time.time() - start_time) * 1000)

                if resp.status_code != 200:
                    return {
                        "success": False,
                        "error": f"GA4 API error ({resp.status_code}): {resp.text}",
                        "duration_ms": duration_ms,
                    }

                data = resp.json()
                raw_rows = data.get("rows", [])
                metric_headers = [m.get("name") for m in data.get("metricHeaders", [])]
                dimension_headers = [d.get("name") for d in data.get("dimensionHeaders", [])]

                rows = []
                for row in raw_rows:
                    row_dict = {}
                    for i, dh in enumerate(dimension_headers):
                        row_dict[dh] = row.get("dimensionValues", [{}])[i].get("value", "")
                    for i, mh in enumerate(metric_headers):
                        row_dict[mh] = row.get("metricValues", [{}])[i].get("value", "0")
                    rows.append(row_dict)

                return {
                    "success": True,
                    "property_id": property_id,
                    "date_range": {"start": start_date, "end": end_date},
                    "dimensions": dimensions,
                    "metrics": metrics,
                    "total_rows": len(rows),
                    "rows": rows,
                    "totals": {
                        mh: data.get("totals", [{}])[0].get("metricValues", [{}])[i].get("value", "0")
                        for i, mh in enumerate(metric_headers)
                    } if data.get("totals") else {},
                    "duration_ms": duration_ms,
                }
        except Exception as e:
            return {"success": False, "error": f"GA4 query failed: {e!s}"}


# Singleton
_google_seo_tool: Optional[GoogleSEOTool] = None


def _get_google_seo_tool() -> GoogleSEOTool:
    """Get the singleton Google SEO tool instance."""
    global _google_seo_tool
    if _google_seo_tool is None:
        _google_seo_tool = GoogleSEOTool()
    return _google_seo_tool


async def search_console_performance(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: Optional[List[str]] = None,
    row_limit: int = 100,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query Google Search Console search performance data."""
    tool = _get_google_seo_tool()
    result = await tool.get_search_performance(
        site_url=site_url,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        row_limit=row_limit,
        user_id=user_id,
    )

    log_mcp_call(
        tool_name="google_search_console",
        query_sanitized=f"search_performance:{site_url}",
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        user_id=user_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )
    return result


async def ga4_traffic_report(
    property_id: str,
    start_date: str = "30daysAgo",
    end_date: str = "today",
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Query Google Analytics 4 for website traffic data."""
    tool = _get_google_seo_tool()
    result = await tool.get_ga4_traffic(
        property_id=property_id,
        start_date=start_date,
        end_date=end_date,
        dimensions=dimensions,
        metrics=metrics,
        user_id=user_id,
    )

    log_mcp_call(
        tool_name="google_analytics_4",
        query_sanitized=f"traffic_report:{property_id}",
        success=result.get("success", False),
        response_status="success" if result.get("success") else "error",
        user_id=user_id,
        error_message=result.get("error"),
        duration_ms=result.get("duration_ms"),
    )
    return result

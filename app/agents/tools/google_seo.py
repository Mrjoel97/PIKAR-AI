"""Google SEO Agent Tools.

ADK-compatible tools for fetching SEO performance data from Google
Search Console and website traffic from Google Analytics 4 (GA4).
"""

import asyncio
from typing import Any, Dict, List, Optional


def get_seo_performance(
    site_url: str,
    days: int = 28,
    dimensions: Optional[List[str]] = None,
    limit: int = 50,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get SEO performance data from Google Search Console.

    Fetches search queries, clicks, impressions, CTR, and average
    position from the user's Google Search Console property. Use this
    to understand which queries drive organic traffic.

    Args:
        site_url: The site URL as registered in GSC
                  (e.g. "https://example.com").
        days: Lookback period in days (default: 28).
        dimensions: Grouping dimensions. Options: "query", "page",
                    "country", "device", "date". Default: ["query"].
        limit: Max rows to return (default: 50).
        user_id: Optional user ID for OAuth-based access.

    Returns:
        Dictionary with search performance rows containing clicks,
        impressions, CTR percentage, and average position.
    """
    from datetime import datetime, timedelta
    from app.mcp.tools.google_seo import search_console_performance

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    search_console_performance(
                        site_url=site_url,
                        start_date=start_date,
                        end_date=end_date,
                        dimensions=dimensions,
                        row_limit=limit,
                        user_id=user_id,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                search_console_performance(
                    site_url=site_url,
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=dimensions,
                    row_limit=limit,
                    user_id=user_id,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_top_search_queries(
    site_url: str,
    limit: int = 25,
    days: int = 28,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get top search queries driving organic traffic to the site.

    Returns queries ranked by clicks with CTR and position data.
    Use this to identify SEO opportunities and content gaps.

    Args:
        site_url: The site URL as registered in GSC.
        limit: Number of top queries to return (default: 25).
        days: Lookback period in days (default: 28).
        user_id: Optional user ID.

    Returns:
        Dictionary with ranked queries and summary statistics.
    """
    from app.mcp.tools.google_seo import _get_google_seo_tool

    tool = _get_google_seo_tool()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    tool.get_top_queries(
                        site_url=site_url,
                        limit=limit,
                        days=days,
                        user_id=user_id,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                tool.get_top_queries(
                    site_url=site_url,
                    limit=limit,
                    days=days,
                    user_id=user_id,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_top_pages(
    site_url: str,
    limit: int = 25,
    days: int = 28,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get top pages by organic search traffic.

    Returns pages ranked by clicks from organic search. Use this to
    identify high-performing content and underperforming pages.

    Args:
        site_url: The site URL as registered in GSC.
        limit: Number of top pages to return (default: 25).
        days: Lookback period in days (default: 28).
        user_id: Optional user ID.

    Returns:
        Dictionary with ranked pages and their SEO metrics.
    """
    from app.mcp.tools.google_seo import _get_google_seo_tool

    tool = _get_google_seo_tool()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    tool.get_top_pages(
                        site_url=site_url,
                        limit=limit,
                        days=days,
                        user_id=user_id,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                tool.get_top_pages(
                    site_url=site_url,
                    limit=limit,
                    days=days,
                    user_id=user_id,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_indexing_status(
    site_url: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check Google Search Console indexing coverage status.

    Returns sitemap details and indexing errors/warnings. Use this
    to identify pages that aren't being indexed.

    Args:
        site_url: The site URL as registered in GSC.
        user_id: Optional user ID.

    Returns:
        Dictionary with sitemaps and their indexing status.
    """
    from app.mcp.tools.google_seo import _get_google_seo_tool

    tool = _get_google_seo_tool()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    tool.get_indexing_status(site_url=site_url, user_id=user_id),
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(
                tool.get_indexing_status(site_url=site_url, user_id=user_id)
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_website_traffic(
    property_id: str,
    start_date: str = "30daysAgo",
    end_date: str = "today",
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get website traffic data from Google Analytics 4.

    Fetches sessions, users, pageviews, bounce rate, and other
    GA4 metrics. Use this for traffic analysis and content performance.

    Args:
        property_id: GA4 property ID (numeric, e.g. "123456789").
        start_date: Start date (YYYY-MM-DD or relative like "30daysAgo").
        end_date: End date (YYYY-MM-DD or "today").
        dimensions: GA4 dimensions to group by. Common options:
                    "date", "sessionSource", "pagePath", "country",
                    "deviceCategory".
        metrics: GA4 metrics to fetch. Common options:
                 "sessions", "activeUsers", "screenPageViews",
                 "bounceRate", "averageSessionDuration".
        user_id: Optional user ID.

    Returns:
        Dictionary with traffic data rows and totals.
    """
    from app.mcp.tools.google_seo import ga4_traffic_report

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    ga4_traffic_report(
                        property_id=property_id,
                        start_date=start_date,
                        end_date=end_date,
                        dimensions=dimensions,
                        metrics=metrics,
                        user_id=user_id,
                    ),
                )
                return future.result(timeout=60)
        else:
            return loop.run_until_complete(
                ga4_traffic_report(
                    property_id=property_id,
                    start_date=start_date,
                    end_date=end_date,
                    dimensions=dimensions,
                    metrics=metrics,
                    user_id=user_id,
                )
            )
    except Exception as e:
        return {"success": False, "error": str(e)}


GOOGLE_SEO_TOOLS = [
    get_seo_performance,
    get_top_search_queries,
    get_top_pages,
    get_indexing_status,
    get_website_traffic,
]

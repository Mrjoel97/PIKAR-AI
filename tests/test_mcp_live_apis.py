"""
Live API Test Script for MCP Tools (Tavily & Firecrawl)

This script tests the actual MCP tool integration with real API calls.
Requires TAVILY_API_KEY and FIRECRAWL_API_KEY environment variables.

Usage:
    python tests/test_mcp_live_apis.py
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from app/.env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "app" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded environment from: {env_path}")


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_result(success: bool, message: str):
    """Print a formatted result."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")


async def test_config():
    """Test MCP configuration loading."""
    print_section("Testing MCP Configuration")
    
    from app.mcp.config import get_mcp_config
    
    config = get_mcp_config()
    
    tavily_configured = config.is_tavily_configured()
    firecrawl_configured = config.is_firecrawl_configured()
    
    print_result(tavily_configured, f"Tavily API configured: {tavily_configured}")
    print_result(firecrawl_configured, f"Firecrawl API configured: {firecrawl_configured}")
    
    return tavily_configured, firecrawl_configured


async def test_pii_filter():
    """Test PII filter sanitization."""
    print_section("Testing PII Filter")
    
    from app.mcp.security.pii_filter import PIIFilter
    
    pii_filter = PIIFilter()
    
    # Test cases
    test_cases = [
        ("john@example.com", "Contact john@example.com"),
        ("555-123-4567", "Call me at 555-123-4567"),
        ("4111-1111-1111-1111", "My card is 4111-1111-1111-1111"),
        ("No PII here", "No PII here"),  # Should remain unchanged
    ]
    
    all_passed = True
    for expected_removed, text in test_cases:
        result = pii_filter.sanitize(text)
        contains_pii = expected_removed in result
        passed = not contains_pii if expected_removed != text else (result == text)
        print_result(passed, f"Sanitize '{text[:30]}...' -> '{result[:30]}...'")
        if not passed:
            all_passed = False
    
    return all_passed


async def test_tavily_search(tavily_configured: bool):
    """Test live Tavily web search."""
    print_section("Testing Tavily Web Search (LIVE API)")
    
    if not tavily_configured:
        print("⚠️  SKIPPED: Tavily API key not configured")
        return False
    
    from app.mcp.tools.web_search import TavilySearchTool
    
    search_tool = TavilySearchTool()
    
    # Test search query
    query = "latest AI news 2024"
    print(f"\nSearching for: '{query}'")
    
    result = await search_tool.search(query, max_results=3)
    
    success = result.get("success", False)
    print_result(success, f"Search returned success: {success}")
    
    if success:
        results = result.get("results", [])
        print(f"\n📊 Found {len(results)} results:")
        for i, r in enumerate(results, 1):
            print(f"   {i}. {r.get('title', 'No title')[:50]}...")
            print(f"      URL: {r.get('url', 'N/A')[:60]}...")
    else:
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    return success


async def test_firecrawl_scrape(firecrawl_configured: bool):
    """Test live Firecrawl web scraping."""
    print_section("Testing Firecrawl Web Scraping (LIVE API)")
    
    if not firecrawl_configured:
        print("⚠️  SKIPPED: Firecrawl API key not configured")
        return False
    
    from app.mcp.tools.web_scrape import FirecrawlScrapeTool
    
    scrape_tool = FirecrawlScrapeTool()
    
    # Test scrape URL (use a simple, reliable page)
    url = "https://example.com"
    print(f"\nScraping URL: {url}")
    
    result = await scrape_tool.scrape(url)
    
    success = result.get("success", False)
    print_result(success, f"Scrape returned success: {success}")
    
    if success:
        content = result.get("content", "")
        title = result.get("title", "No title")
        print(f"\n📄 Page Title: {title}")
        print(f"   Content length: {len(content)} characters")
        print(f"   Content preview: {content[:200]}...")
    else:
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    return success


async def test_agent_tools():
    """Test the ADK-compatible agent tool wrappers."""
    print_section("Testing ADK Agent Tool Wrappers")
    
    from app.mcp.agent_tools import mcp_web_search, mcp_web_scrape, get_mcp_agent_tools
    
    # Test tool list
    tools = get_mcp_agent_tools()
    print_result(len(tools) == 3, f"Got {len(tools)} MCP tools")
    
    # Test tool names
    tool_names = [t.__name__ for t in tools]
    expected_names = ["mcp_web_search", "mcp_web_scrape", "mcp_generate_landing_page"]
    all_present = all(name in tool_names for name in expected_names)
    print_result(all_present, f"All expected tools present: {tool_names}")
    
    return all_present


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print(" MCP Live API Test Suite")
    print(f" Started: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Run tests
    tavily_ok, firecrawl_ok = await test_config()
    pii_ok = await test_pii_filter()
    tools_ok = await test_agent_tools()
    
    # Live API tests (only if configured)
    tavily_search_ok = await test_tavily_search(tavily_ok)
    firecrawl_scrape_ok = await test_firecrawl_scrape(firecrawl_ok)
    
    # Summary
    print_section("Test Summary")
    results = [
        ("Configuration", tavily_ok or firecrawl_ok),
        ("PII Filter", pii_ok),
        ("Agent Tools", tools_ok),
        ("Tavily Search", tavily_search_ok if tavily_ok else None),
        ("Firecrawl Scrape", firecrawl_scrape_ok if firecrawl_ok else None),
    ]
    
    for name, result in results:
        if result is None:
            print(f"⏭️  {name}: SKIPPED (not configured)")
        else:
            print_result(result, name)
    
    all_passed = all(r for r in [pii_ok, tools_ok] if r is not None)
    print(f"\n{'✅ All core tests passed!' if all_passed else '❌ Some tests failed.'}")


if __name__ == "__main__":
    asyncio.run(main())


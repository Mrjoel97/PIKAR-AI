"""Deep Research Tool.

Provides comprehensive research capabilities that automatically use
audited web search (Tavily) and web scraping (Firecrawl) wrappers.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.mcp.tools.web_scrape import FirecrawlScrapeTool, web_scrape
from app.mcp.tools.web_search import TavilySearchTool, web_search_with_context
from app.rag.knowledge_vault import ingest_document_content

logger = logging.getLogger(__name__)


class DeepResearchTool:
    """Orchestrates comprehensive research using multiple sources and skills."""

    def __init__(self):
        self.search_tool = TavilySearchTool()
        self.scrape_tool = FirecrawlScrapeTool()
        self.max_retries = 2
        self.retry_delay_seconds = 0.5
        self._search_cache: Dict[Tuple[str, int, str], Dict[str, Any]] = {}
        self._scrape_cache: Dict[str, Dict[str, Any]] = {}

    def _ensure_runtime_state(self) -> None:
        """Backfill runtime attributes for tests that bypass __init__."""
        if not hasattr(self, "search_tool"):
            self.search_tool = TavilySearchTool()
        if not hasattr(self, "scrape_tool"):
            self.scrape_tool = FirecrawlScrapeTool()
        if not hasattr(self, "max_retries"):
            self.max_retries = 2
        if not hasattr(self, "retry_delay_seconds"):
            self.retry_delay_seconds = 0.5
        if not hasattr(self, "_search_cache"):
            self._search_cache = {}
        if not hasattr(self, "_scrape_cache"):
            self._scrape_cache = {}

    async def research(
        self,
        topic: str,
        research_type: str = "comprehensive",
        depth: str = "deep",
        num_sources: int = 10,
        scrape_top_n: int = 5,
        user_id: Optional[str] = None,
        save_to_vault: bool = True,
    ) -> Dict[str, Any]:
        """Perform deep research on a topic using multiple sources."""
        self._ensure_runtime_state()

        results: Dict[str, Any] = {
            "topic": topic,
            "research_type": research_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sources": [],
            "scraped_content": [],
            "key_findings": [],
            "synthesis": "",
            "citations": [],
            "contradictions": [],
            "recommended_next_questions": [],
            "confidence_score": 0.0,
            "saved_to_vault": False,
            "pipeline": [
                "query_planning",
                "search",
                "ranking",
                "scrape",
                "synthesis",
                "vault_save",
            ],
            "provider_status": {
                "search": {"provider": "tavily", "successful_queries": 0, "failed_queries": 0},
                "scrape": {"provider": "firecrawl", "successful_urls": 0, "failed_urls": 0},
            },
            "limitations": [],
        }

        try:
            logger.info("Starting deep research on: %s", topic)

            search_queries = self._generate_search_queries(topic, research_type)
            results["search_queries"] = search_queries[:3]
            all_search_results: List[Dict[str, Any]] = []

            for query in search_queries[:3]:
                search_result = await self._search_with_retry(
                    query=query,
                    max_results=num_sources,
                    depth=depth,
                    user_id=user_id,
                )

                if search_result.get("success"):
                    results["provider_status"]["search"]["successful_queries"] += 1
                else:
                    results["provider_status"]["search"]["failed_queries"] += 1
                    error = search_result.get("error")
                    if error:
                        results["limitations"].append(f"Search query failed for '{query}': {error}")

                if search_result.get("results"):
                    all_search_results.extend(search_result["results"])

                if search_result.get("answer") and not results.get("quick_answer"):
                    results["quick_answer"] = search_result["answer"]

            unique_results = self._deduplicate_results(all_search_results)
            ranked_results = self._rank_sources(unique_results, topic)
            results["sources"] = ranked_results[:num_sources]
            logger.info("Found %s ranked sources", len(results["sources"]))

            top_urls = [source["url"] for source in results["sources"][:scrape_top_n] if source.get("url")]
            scrape_tasks = [self._scrape_with_retry(url=url, user_id=user_id) for url in top_urls]
            scrape_results = await asyncio.gather(*scrape_tasks, return_exceptions=True)

            for url, scrape_result in zip(top_urls, scrape_results):
                if isinstance(scrape_result, Exception):
                    results["provider_status"]["scrape"]["failed_urls"] += 1
                    results["limitations"].append(f"Scrape failed for '{url}': {scrape_result}")
                    continue

                if scrape_result.get("success") and scrape_result.get("markdown"):
                    results["provider_status"]["scrape"]["successful_urls"] += 1
                    markdown = scrape_result["markdown"]
                    results["scraped_content"].append(
                        {
                            "url": url,
                            "title": scrape_result.get("metadata", {}).get("title", ""),
                            "content": markdown[:5000],
                            "word_count": len(markdown.split()),
                        }
                    )
                else:
                    results["provider_status"]["scrape"]["failed_urls"] += 1
                    error = scrape_result.get("error")
                    if error:
                        results["limitations"].append(f"Scrape failed for '{url}': {error}")

            logger.info("Scraped %s pages in detail", len(results["scraped_content"]))

            results["key_findings"] = self._extract_key_findings(
                results["sources"],
                results["scraped_content"],
                research_type,
            )
            results["contradictions"] = self._find_contradictions(results["sources"])
            results["recommended_next_questions"] = self._recommend_next_questions(
                topic,
                research_type,
                results["sources"],
                results["contradictions"],
            )
            results["synthesis"] = self._synthesize_findings(
                topic,
                results["key_findings"],
                results["sources"],
                research_type,
                results["contradictions"],
            )
            results["citations"] = self._build_citations(results["sources"])
            results["confidence_score"] = self._calculate_confidence(
                sources=results["sources"],
                scraped_content=results["scraped_content"],
                contradictions=results["contradictions"],
                provider_status=results["provider_status"],
            )

            if save_to_vault and user_id:
                try:
                    vault_content = self._build_vault_content(results)
                    await ingest_document_content(
                        content=vault_content,
                        title=f"Research: {topic}",
                        document_type="research_report",
                        user_id=user_id,
                        metadata={
                            "research_type": research_type,
                            "num_sources": len(results["sources"]),
                            "topic": topic,
                            "confidence_score": results["confidence_score"],
                        },
                    )
                    results["saved_to_vault"] = True
                    logger.info("Research saved to Knowledge Vault for user %s", user_id)
                except Exception as exc:
                    logger.warning("Failed to save to vault: %s", exc)
                    results["limitations"].append(f"Vault save failed: {exc}")
            elif save_to_vault and not user_id:
                results["limitations"].append("Vault save skipped because no user_id was provided.")

            if not results["sources"]:
                results["limitations"].append("No search sources were returned for this topic.")

            results["success"] = True
            results["message"] = (
                f"Completed {research_type} research with {len(results['sources'])} ranked sources"
            )
        except Exception as exc:
            logger.error("Research failed: %s", exc, exc_info=True)
            results["success"] = False
            results["error"] = str(exc)

        return results

    async def _search_with_retry(
        self,
        query: str,
        max_results: int,
        depth: str,
        user_id: Optional[str],
    ) -> Dict[str, Any]:
        """Execute search through the audited wrapper layer with retry support."""
        cache_key = (query, max_results, depth)
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        search_depth = "advanced" if depth == "deep" else "basic"
        last_result: Dict[str, Any] = {"success": False, "error": "Search did not run"}

        for attempt in range(self.max_retries + 1):
            if self._should_use_wrapper_search():
                result = await web_search_with_context(
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_answer=True,
                    agent_name="deep_research",
                    user_id=user_id,
                )
            else:
                result = await self.search_tool.search(
                    query=query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_answer=True,
                )

            last_result = result
            if result.get("success", bool(result.get("results"))):
                normalized = dict(result)
                normalized.setdefault("success", True)
                self._search_cache[cache_key] = normalized
                return normalized

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))

        return last_result

    async def _scrape_with_retry(self, url: str, user_id: Optional[str]) -> Dict[str, Any]:
        """Execute scraping through the audited wrapper layer with retry support."""
        if url in self._scrape_cache:
            return self._scrape_cache[url]

        last_result: Dict[str, Any] = {"success": False, "error": "Scrape did not run", "url": url}

        for attempt in range(self.max_retries + 1):
            if self._should_use_wrapper_scrape():
                result = await web_scrape(
                    url=url,
                    extract_content=True,
                    formats=["markdown"],
                    wait_for=0,
                    agent_name="deep_research",
                    user_id=user_id,
                )
            else:
                result = await self.scrape_tool.scrape(
                    url=url,
                    formats=["markdown"],
                    only_main_content=True,
                )

            last_result = result
            if result.get("success") and result.get("markdown"):
                self._scrape_cache[url] = result
                return result

            if attempt < self.max_retries:
                await asyncio.sleep(self.retry_delay_seconds * (attempt + 1))

        return last_result

    def _should_use_wrapper_search(self) -> bool:
        return type(self.search_tool) is TavilySearchTool

    def _should_use_wrapper_scrape(self) -> bool:
        return type(self.scrape_tool) is FirecrawlScrapeTool

    def _deduplicate_results(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen_urls = set()
        unique_results = []
        for result in search_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        return unique_results

    def _rank_sources(self, sources: List[Dict[str, Any]], topic: str) -> List[Dict[str, Any]]:
        """Rank sources using provider score and topic overlap."""
        topic_terms = {term.lower() for term in topic.split() if len(term) > 2}

        def sort_key(source: Dict[str, Any]) -> tuple[float, int]:
            content = f"{source.get('title', '')} {source.get('content', '')}".lower()
            overlap = sum(1 for term in topic_terms if term in content)
            score = float(source.get("score") or 0.0)
            return (score, overlap)

        return sorted(sources, key=sort_key, reverse=True)

    def _generate_search_queries(self, topic: str, research_type: str) -> List[str]:
        """Generate multiple search queries based on research type."""
        base_queries = [topic]

        if research_type == "market":
            base_queries.extend(
                [
                    f"{topic} market size 2024 2025",
                    f"{topic} industry trends",
                    f"{topic} market analysis report",
                    f"{topic} growth forecast",
                ]
            )
        elif research_type == "competitor":
            base_queries.extend(
                [
                    f"{topic} competitors comparison",
                    f"{topic} alternatives",
                    f"{topic} vs comparison",
                    f"best {topic} companies",
                ]
            )
        elif research_type == "technical":
            base_queries.extend(
                [
                    f"{topic} how it works",
                    f"{topic} technical documentation",
                    f"{topic} architecture explained",
                    f"{topic} best practices",
                ]
            )
        else:
            base_queries.extend(
                [
                    f"{topic} overview",
                    f"{topic} guide",
                    f"{topic} explained",
                    f"what is {topic}",
                ]
            )

        return base_queries

    def _extract_key_findings(
        self,
        sources: List[Dict[str, Any]],
        scraped_content: List[Dict[str, Any]],
        research_type: str,
    ) -> List[str]:
        """Extract key findings from sources and scraped content."""
        del research_type
        findings = []

        for source in sources[:10]:
            content = source.get("content", "")
            if content and len(content) > 50:
                sentences = content.split(". ")
                if sentences:
                    finding = sentences[0].strip()
                    if finding and len(finding) > 20:
                        findings.append(finding)

        for scraped in scraped_content[:3]:
            content = scraped.get("content", "")
            paragraphs = content.split("\n\n")
            for paragraph in paragraphs[:2]:
                if paragraph and len(paragraph) > 100:
                    finding = paragraph[:300].strip()
                    if finding not in findings:
                        findings.append(finding)

        return findings[:10]

    def _synthesize_findings(
        self,
        topic: str,
        key_findings: List[str],
        sources: List[Dict[str, Any]],
        research_type: str,
        contradictions: List[str],
    ) -> str:
        """Synthesize findings into a coherent summary."""
        synthesis_parts = []

        if research_type == "market":
            synthesis_parts.append(f"Market research on '{topic}' reveals several key insights:")
        elif research_type == "competitor":
            synthesis_parts.append(f"Competitive analysis of '{topic}' shows:")
        elif research_type == "technical":
            synthesis_parts.append(f"Technical analysis of '{topic}' indicates:")
        else:
            synthesis_parts.append(f"Research on '{topic}' provides the following insights:")

        for index, finding in enumerate(key_findings[:5], 1):
            synthesis_parts.append(f"\n{index}. {finding}")

        if contradictions:
            synthesis_parts.append("\n\nPotential contradictions or open questions:")
            for contradiction in contradictions[:3]:
                synthesis_parts.append(f"\n- {contradiction}")

        synthesis_parts.append(f"\n\nThis analysis is based on {len(sources)} ranked sources.")
        return "".join(synthesis_parts)

    def _find_contradictions(self, sources: List[Dict[str, Any]]) -> List[str]:
        """Surface weak contradictions by comparing similar snippets."""
        statements = []
        contradictions = []

        for source in sources[:8]:
            snippet = source.get("content", "")
            if not snippet:
                continue
            normalized = " ".join(snippet.split())[:240]
            statements.append((source.get("title") or source.get("url") or "Source", normalized))

        seen_fragments = {}
        for label, statement in statements:
            prefix = statement[:80].lower()
            if prefix in seen_fragments and seen_fragments[prefix] != statement:
                contradictions.append(
                    f"{label} differs from another source on a similar claim: '{statement[:120]}'"
                )
            else:
                seen_fragments[prefix] = statement

        return contradictions[:5]

    def _recommend_next_questions(
        self,
        topic: str,
        research_type: str,
        sources: List[Dict[str, Any]],
        contradictions: List[str],
    ) -> List[str]:
        """Recommend follow-up questions that deepen the research."""
        questions = [
            f"What changed most recently in {topic} during 2025 and 2026?",
            f"Which assumptions about {topic} still need primary-source validation?",
        ]

        if research_type == "market":
            questions.append(f"What is the most defensible TAM/SAM/SOM estimate for {topic}?")
        elif research_type == "competitor":
            questions.append(f"Which competitors in {topic} are winning on pricing, speed, or distribution?")
        elif research_type == "technical":
            questions.append(f"What are the main technical risks or scaling constraints for {topic}?")

        if contradictions:
            questions.append(f"Which contradictory claims about {topic} can be resolved with primary sources?")

        if not sources:
            questions.append(f"Which official sites or databases should be searched next for {topic}?")

        return questions[:4]

    def _build_citations(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "number": index + 1,
                "title": source.get("title", "Untitled"),
                "url": source.get("url", ""),
                "snippet": source.get("content", "")[:200],
            }
            for index, source in enumerate(sources[:10])
        ]

    def _calculate_confidence(
        self,
        sources: List[Dict[str, Any]],
        scraped_content: List[Dict[str, Any]],
        contradictions: List[str],
        provider_status: Dict[str, Any],
    ) -> float:
        """Estimate confidence from source breadth, scrape depth, and provider health."""
        source_score = min(len(sources) / 8.0, 1.0)
        scrape_score = min(len(scraped_content) / 4.0, 1.0)

        search_status = provider_status.get("search", {})
        scrape_status = provider_status.get("scrape", {})
        total_queries = search_status.get("successful_queries", 0) + search_status.get("failed_queries", 0)
        total_scrapes = scrape_status.get("successful_urls", 0) + scrape_status.get("failed_urls", 0)

        search_health = (
            search_status.get("successful_queries", 0) / total_queries if total_queries else 0.0
        )
        scrape_health = (
            scrape_status.get("successful_urls", 0) / total_scrapes if total_scrapes else 0.0
        )
        contradiction_penalty = min(len(contradictions) * 0.08, 0.24)

        confidence = (
            (source_score * 0.4)
            + (scrape_score * 0.25)
            + (search_health * 0.2)
            + (scrape_health * 0.15)
        )
        confidence -= contradiction_penalty
        return round(max(0.0, min(confidence, 1.0)), 2)

    def _build_vault_content(self, results: Dict[str, Any]) -> str:
        """Build the persisted research document."""
        findings = "\n".join(f"- {finding}" for finding in results["key_findings"]) or "- None captured"
        citations = "\n".join(
            f"[{citation['number']}] {citation['title']} - {citation['url']}"
            for citation in results["citations"]
        ) or "- No citations captured"
        contradictions = "\n".join(f"- {item}" for item in results["contradictions"]) or "- None detected"
        next_questions = "\n".join(f"- {item}" for item in results["recommended_next_questions"]) or "- None suggested"

        return f"""# Research: {results['topic']}

## Type: {results['research_type']}
## Date: {results['timestamp']}
## Confidence Score: {results['confidence_score']}

## Key Findings
{findings}

## Synthesis
{results['synthesis']}

## Contradictions / Open Questions
{contradictions}

## Recommended Next Questions
{next_questions}

## Sources
{citations}
"""


# Singleton instance
_research_tool: Optional[DeepResearchTool] = None


def get_research_tool() -> DeepResearchTool:
    """Get singleton research tool instance."""
    global _research_tool
    if _research_tool is None:
        _research_tool = DeepResearchTool()
    return _research_tool


async def deep_research(
    topic: str,
    research_type: str = "comprehensive",
    depth: str = "deep",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform comprehensive research on a topic using web search and scraping."""
    tool = get_research_tool()
    return await tool.research(
        topic=topic,
        research_type=research_type,
        depth=depth,
        user_id=user_id,
        save_to_vault=True,
    )


async def quick_research(topic: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Perform quick research on a topic."""
    tool = get_research_tool()
    return await tool.research(
        topic=topic,
        research_type="comprehensive",
        depth="quick",
        num_sources=5,
        scrape_top_n=2,
        user_id=user_id,
        save_to_vault=False,
    )


async def market_research(topic: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Perform market research on a topic."""
    tool = get_research_tool()
    return await tool.research(
        topic=topic,
        research_type="market",
        depth="deep",
        num_sources=15,
        scrape_top_n=5,
        user_id=user_id,
        save_to_vault=True,
    )


async def competitor_research(
    topic: str,
    competitors: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform competitor analysis."""
    tool = get_research_tool()

    research_topic = topic
    if competitors:
        research_topic = f"{topic} vs {' vs '.join(competitors[:3])}"

    return await tool.research(
        topic=research_topic,
        research_type="competitor",
        depth="deep",
        num_sources=15,
        scrape_top_n=5,
        user_id=user_id,
        save_to_vault=True,
    )


DEEP_RESEARCH_TOOLS = [
    deep_research,
    quick_research,
    market_research,
    competitor_research,
]

DEEP_RESEARCH_TOOLS_MAP = {
    "deep_research": deep_research,
    "quick_research": quick_research,
    "market_research": market_research,
    "competitor_research": competitor_research,
}


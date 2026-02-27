"""Deep Research Tool.

Provides comprehensive research capabilities that automatically use
web search (Tavily) and web scraping (Firecrawl) along with research
skills from the skills registry.

This tool is designed to be triggered automatically when users:
- Present an idea for evaluation
- Ask for market research
- Request competitor analysis
- Need information gathering on any topic
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.mcp.tools.web_search import TavilySearchTool
from app.mcp.tools.web_scrape import FirecrawlScrapeTool
from app.rag.knowledge_vault import ingest_document_content

logger = logging.getLogger(__name__)


class DeepResearchTool:
    """Orchestrates comprehensive research using multiple sources and skills."""
    
    def __init__(self):
        self.search_tool = TavilySearchTool()
        self.scrape_tool = FirecrawlScrapeTool()
    
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
        """Perform deep research on a topic using multiple sources.
        
        This method:
        1. Searches the web using Tavily for broad coverage
        2. Scrapes top results using Firecrawl for detailed content
        3. Synthesizes findings with citations
        4. Optionally saves to Knowledge Vault for future reference
        
        Args:
            topic: The research topic or question
            research_type: Type of research - "comprehensive", "market", "competitor", "technical"
            depth: Research depth - "quick", "standard", "deep"
            num_sources: Number of sources to search
            scrape_top_n: Number of top results to scrape for full content
            user_id: User ID for saving to vault
            save_to_vault: Whether to save findings to Knowledge Vault
            
        Returns:
            Comprehensive research results with sources and synthesis
        """
        results = {
            "topic": topic,
            "research_type": research_type,
            "timestamp": datetime.utcnow().isoformat(),
            "sources": [],
            "scraped_content": [],
            "key_findings": [],
            "synthesis": "",
            "citations": [],
        }
        
        try:
            # Step 1: Broad web search
            logger.info(f"Starting deep research on: {topic}")
            
            search_queries = self._generate_search_queries(topic, research_type)
            all_search_results = []
            
            for query in search_queries[:3]:  # Use top 3 query variations
                search_result = await self.search_tool.search(
                    query=query,
                    max_results=num_sources,
                    search_depth="advanced" if depth == "deep" else "basic",
                    include_answer=True,
                )
                
                if search_result.get("results"):
                    all_search_results.extend(search_result["results"])
                    
                if search_result.get("answer"):
                    results["quick_answer"] = search_result["answer"]
            
            # Deduplicate by URL
            seen_urls = set()
            unique_results = []
            for r in all_search_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(r)
            
            results["sources"] = unique_results[:num_sources]
            logger.info(f"Found {len(results['sources'])} unique sources")
            
            # Step 2: Scrape top results for detailed content
            top_urls = [r["url"] for r in results["sources"][:scrape_top_n] if r.get("url")]
            
            for url in top_urls:
                try:
                    scrape_result = await self.scrape_tool.scrape(
                        url=url,
                        formats=["markdown"],
                        only_main_content=True,
                    )
                    
                    if scrape_result.get("success") and scrape_result.get("markdown"):
                        results["scraped_content"].append({
                            "url": url,
                            "title": scrape_result.get("metadata", {}).get("title", ""),
                            "content": scrape_result["markdown"][:5000],  # Limit content size
                            "word_count": len(scrape_result["markdown"].split()),
                        })
                except Exception as e:
                    logger.warning(f"Failed to scrape {url}: {e}")
            
            logger.info(f"Scraped {len(results['scraped_content'])} pages in detail")
            
            # Step 3: Extract key findings
            results["key_findings"] = self._extract_key_findings(
                results["sources"],
                results["scraped_content"],
                research_type
            )
            
            # Step 4: Generate synthesis
            results["synthesis"] = self._synthesize_findings(
                topic,
                results["key_findings"],
                results["sources"],
                research_type
            )
            
            # Step 5: Build citations
            results["citations"] = [
                {
                    "number": i + 1,
                    "title": s.get("title", "Untitled"),
                    "url": s.get("url", ""),
                    "snippet": s.get("content", "")[:200],
                }
                for i, s in enumerate(results["sources"][:10])
            ]
            
            # Step 6: Save to Knowledge Vault if requested
            if save_to_vault and user_id:
                try:
                    vault_content = f"""# Research: {topic}

## Type: {research_type}
## Date: {results['timestamp']}

## Key Findings
{chr(10).join('- ' + f for f in results['key_findings'])}

## Synthesis
{results['synthesis']}

## Sources
{chr(10).join(f"[{i+1}] {c['title']} - {c['url']}" for i, c in enumerate(results['citations']))}
"""
                    await ingest_document_content(
                        content=vault_content,
                        title=f"Research: {topic}",
                        document_type="research_report",
                        user_id=user_id,
                        metadata={
                            "research_type": research_type,
                            "num_sources": len(results["sources"]),
                            "topic": topic,
                        }
                    )
                    results["saved_to_vault"] = True
                    logger.info(f"Research saved to Knowledge Vault for user {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to save to vault: {e}")
                    results["saved_to_vault"] = False
            
            results["success"] = True
            results["message"] = f"Completed {research_type} research with {len(results['sources'])} sources"
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            results["success"] = False
            results["error"] = str(e)
        
        return results
    
    def _generate_search_queries(self, topic: str, research_type: str) -> List[str]:
        """Generate multiple search queries based on research type."""
        base_queries = [topic]
        
        if research_type == "market":
            base_queries.extend([
                f"{topic} market size 2024 2025",
                f"{topic} industry trends",
                f"{topic} market analysis report",
                f"{topic} growth forecast",
            ])
        elif research_type == "competitor":
            base_queries.extend([
                f"{topic} competitors comparison",
                f"{topic} alternatives",
                f"{topic} vs comparison",
                f"best {topic} companies",
            ])
        elif research_type == "technical":
            base_queries.extend([
                f"{topic} how it works",
                f"{topic} technical documentation",
                f"{topic} architecture explained",
                f"{topic} best practices",
            ])
        else:  # comprehensive
            base_queries.extend([
                f"{topic} overview",
                f"{topic} guide",
                f"{topic} explained",
                f"what is {topic}",
            ])
        
        return base_queries
    
    def _extract_key_findings(
        self,
        sources: List[Dict],
        scraped_content: List[Dict],
        research_type: str
    ) -> List[str]:
        """Extract key findings from sources and scraped content."""
        findings = []
        
        # Extract from search result snippets
        for source in sources[:10]:
            content = source.get("content", "")
            if content and len(content) > 50:
                # Extract first sentence or meaningful snippet
                sentences = content.split(". ")
                if sentences:
                    finding = sentences[0].strip()
                    if finding and len(finding) > 20:
                        findings.append(finding)
        
        # Add findings from scraped content
        for scraped in scraped_content[:3]:
            content = scraped.get("content", "")
            # Extract first paragraph
            paragraphs = content.split("\n\n")
            for para in paragraphs[:2]:
                if para and len(para) > 100:
                    finding = para[:300].strip()
                    if finding not in findings:
                        findings.append(finding)
        
        return findings[:10]  # Top 10 findings
    
    def _synthesize_findings(
        self,
        topic: str,
        key_findings: List[str],
        sources: List[Dict],
        research_type: str
    ) -> str:
        """Synthesize findings into a coherent summary."""
        # This is a structured synthesis - the LLM will enhance this
        synthesis_parts = []
        
        if research_type == "market":
            synthesis_parts.append(f"Market research on '{topic}' reveals several key insights:")
        elif research_type == "competitor":
            synthesis_parts.append(f"Competitive analysis of '{topic}' shows:")
        elif research_type == "technical":
            synthesis_parts.append(f"Technical analysis of '{topic}' indicates:")
        else:
            synthesis_parts.append(f"Research on '{topic}' provides the following insights:")
        
        for i, finding in enumerate(key_findings[:5], 1):
            synthesis_parts.append(f"\n{i}. {finding}")
        
        synthesis_parts.append(f"\n\nThis analysis is based on {len(sources)} sources.")
        
        return "".join(synthesis_parts)


# Singleton instance
_research_tool: Optional[DeepResearchTool] = None


def get_research_tool() -> DeepResearchTool:
    """Get singleton research tool instance."""
    global _research_tool
    if _research_tool is None:
        _research_tool = DeepResearchTool()
    return _research_tool


# ============================================================================
# Agent Tool Functions
# ============================================================================

async def deep_research(
    topic: str,
    research_type: str = "comprehensive",
    depth: str = "deep",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform comprehensive research on a topic using web search and scraping.
    
    This is the primary research tool. Use this whenever a user:
    - Presents an idea and wants feedback
    - Asks about market opportunities
    - Needs competitor analysis
    - Wants to understand a topic deeply
    
    The tool automatically:
    1. Searches 10+ web sources using Tavily
    2. Scrapes top 5 results for detailed content
    3. Extracts key findings
    4. Synthesizes a comprehensive summary
    5. Saves findings to Knowledge Vault
    
    Args:
        topic: What to research (e.g., "AI writing assistants market")
        research_type: "comprehensive", "market", "competitor", or "technical"
        depth: "quick" (fast), "standard", or "deep" (thorough)
        user_id: User ID for saving results
        
    Returns:
        Dictionary with sources, key findings, synthesis, and citations
    """
    tool = get_research_tool()
    return await tool.research(
        topic=topic,
        research_type=research_type,
        depth=depth,
        user_id=user_id,
        save_to_vault=True,
    )


async def quick_research(topic: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Perform quick research on a topic.
    
    Faster than deep_research, searches fewer sources but still provides
    useful insights. Good for quick fact-checking or initial exploration.
    
    Args:
        topic: What to research
        user_id: User ID for context
        
    Returns:
        Research results with fewer sources
    """
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
    """Perform market research on a topic.
    
    Specialized for market analysis: market size, trends, growth forecasts,
    industry analysis. Use when evaluating business ideas or markets.
    
    Args:
        topic: Market or industry to research
        user_id: User ID for saving results
        
    Returns:
        Market research findings
    """
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
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Perform competitor analysis.
    
    Researches competitors, alternatives, and competitive landscape.
    Optionally provide specific competitor names to analyze.
    
    Args:
        topic: Product/service/company to analyze
        competitors: Optional list of specific competitors
        user_id: User ID for saving results
        
    Returns:
        Competitive analysis findings
    """
    tool = get_research_tool()
    
    # Enhance topic with competitor names if provided
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


# ============================================================================
# Export for Agent Registration
# ============================================================================

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

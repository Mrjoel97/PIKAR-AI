"""MCP Connector - Main entry point for MCP tools.

This module provides the MCPConnector class which is the central interface
for agents to access external services through MCP tools.

The connector handles:
- Tool registration and access
- PII filtering on all queries
- Audit logging of all calls
- Rate limiting (TODO)
"""

from typing import Any, Callable, Dict, List, Optional

from app.mcp.config import get_mcp_config, MCPConfig
from app.mcp.security.pii_filter import PIIFilter, sanitize_query
from app.mcp.security.audit_logger import AuditLogger, log_mcp_call


class MCPConnector:
    """Central MCP connector for accessing external services.
    
    This class provides a unified interface for agents to use MCP tools.
    All queries are automatically sanitized for PII before being sent
    to external services.
    """
    
    def __init__(
        self,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """Initialize the MCP connector.
        
        Args:
            agent_name: Name of the agent using this connector.
            user_id: User ID for audit logging.
            session_id: Session ID for audit logging.
        """
        self.config = get_mcp_config()
        self.pii_filter = PIIFilter()
        self.audit_logger = AuditLogger()
        
        self.agent_name = agent_name
        self.user_id = user_id
        self.session_id = session_id
    
    def set_context(
        self,
        agent_name: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context_names: Optional[List[str]] = None,
    ) -> None:
        """Set context for the connector.
        
        Args:
            agent_name: Name of the agent.
            user_id: User ID for tracking.
            session_id: Session ID for tracking.
            context_names: Names to redact from queries (e.g., user's name).
        """
        if agent_name:
            self.agent_name = agent_name
        if user_id:
            self.user_id = user_id
        if session_id:
            self.session_id = session_id
        if context_names:
            self.pii_filter.set_context_names(context_names)
    
    async def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Perform a privacy-safe web search.
        
        Args:
            query: Search query (will be sanitized).
            max_results: Maximum number of results to return.
            
        Returns:
            Search results dictionary.
        """
        from app.mcp.tools.web_search import web_search_with_context
        
        safe_query = self.pii_filter.sanitize(query)
        return await web_search_with_context(
            query=safe_query,
            max_results=max_results,
            agent_name=self.agent_name,
            user_id=self.user_id,
            session_id=self.session_id,
        )
    
    async def web_scrape(self, url: str, extract_content: bool = True) -> Dict[str, Any]:
        """Scrape content from a URL.
        
        Args:
            url: URL to scrape.
            extract_content: Whether to extract and clean content.
            
        Returns:
            Scraped content dictionary.
        """
        from app.mcp.tools.web_scrape import web_scrape
        
        return await web_scrape(
            url=url,
            extract_content=extract_content,
            agent_name=self.agent_name,
            user_id=self.user_id,
            session_id=self.session_id,
        )
    
    async def generate_landing_page(
        self,
        title: str,
        description: str,
        style: str = "modern",
        include_form: bool = True,
    ) -> Dict[str, Any]:
        """Generate a landing page with HTML/React components.
        
        Args:
            title: Page title.
            description: Page description/purpose.
            style: Visual style (modern, minimal, bold).
            include_form: Whether to include a lead capture form.
            
        Returns:
            Generated landing page dictionary with HTML and React code.
        """
        from app.mcp.tools.landing_page import generate_landing_page
        
        return await generate_landing_page(
            title=title,
            description=description,
            style=style,
            include_form=include_form,
            agent_name=self.agent_name,
            user_id=self.user_id,
        )
    
    async def handle_form_submission(
        self,
        form_id: str,
        data: Dict[str, Any],
        send_email: bool = True,
        sync_crm: bool = True,
    ) -> Dict[str, Any]:
        """Handle a form submission.
        
        Args:
            form_id: ID of the form receiving the submission.
            data: Form data submitted.
            send_email: Whether to send email notification.
            sync_crm: Whether to sync with CRM.
            
        Returns:
            Submission result dictionary.
        """
        from app.mcp.tools.form_handler import handle_form_submission
        
        return await handle_form_submission(
            form_id=form_id,
            data=data,
            send_email=send_email,
            sync_crm=sync_crm,
            agent_name=self.agent_name,
            user_id=self.user_id,
        )


def get_mcp_tools(tool_names: Optional[List[str]] = None) -> List[Callable]:
    """Get MCP tools as callable functions for agent integration.
    
    Args:
        tool_names: List of tool names to include. If None, returns all tools.
                   Options: "web_search", "web_scrape", "landing_page", "form_handler"
    
    Returns:
        List of callable tool functions compatible with Google ADK.
    """
    from app.mcp.tools.web_search import web_search
    from app.mcp.tools.web_scrape import web_scrape
    from app.mcp.tools.landing_page import generate_landing_page, save_landing_page
    from app.mcp.tools.form_handler import handle_form_submission
    
    all_tools = {
        "web_search": web_search,
        "web_scrape": web_scrape,
        "landing_page": generate_landing_page,
        "save_landing_page": save_landing_page,
        "form_handler": handle_form_submission,
    }
    
    if tool_names is None:
        return list(all_tools.values())
    
    return [all_tools[name] for name in tool_names if name in all_tools]


from typing import Any, Dict, Optional
import os
import requests
from app.routers.approvals import create_approval_request, ApprovalRequestCreate

# Note: Since this tool runs inside the same process as FastAPI in some setups, we could call the function directly.
# However, usually tools might run in isolated environments. 
# For simplicity in this architecture, we will call the internal logic helper or use a direct helper call.

async def request_human_approval(action_type: str, action_description: str, payload: Dict[str, Any]) -> str:
    """
    Pauses execution and requests human approval via a generated Magic Link.
    
    Args:
        action_type: Short identifier like 'POST_TWEET' or 'SEND_EMAIL'.
        action_description: Human readable text for the user, e.g. "Post a tweet about the launch".
        payload: The exact data to be acted upon.
    
    Returns:
        A message containing the Magic Link to show to the user.
    """
    
    # We construct the request object reusing existing pydantic schema
    req = ApprovalRequestCreate(action_type=action_type, payload=payload)
    
    try:
        # In this monolith, we can call the router logic directly or mocked.
        # But to be clean, let's pretend we hit the API or just replicate the logic (safest is logic reuse).
        # We need to await it.
        result = await create_approval_request(req)
        
        link = result['link']
        return f"I have generated an approval request for '{action_description}'.\nPlease approve it here: {link}"
        
    except Exception as e:
        return f"Failed to generate approval link: {str(e)}"

# Register this tool in your agent definition

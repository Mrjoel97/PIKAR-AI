# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import logging
from dotenv import load_dotenv
load_dotenv('app/.env')
from typing import Optional, AsyncIterator, Annotated, List, Dict, Any, Union
from contextlib import asynccontextmanager
import google.auth

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BYPASS_IMPORT = os.environ.get("LOCAL_DEV_BYPASS") == "1"

if not BYPASS_IMPORT:
    try:
        from a2a.server.apps import A2AFastAPIApplication
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.types import AgentCapabilities, AgentCard
        from a2a.utils.constants import (
            AGENT_CARD_WELL_KNOWN_PATH,
            EXTENDED_AGENT_CARD_PATH,
        )
        A2A_AVAILABLE = True
    except Exception as e:
        logger.warning(f"A2A components not available: {e}")
        A2A_AVAILABLE = False
else:
    A2A_AVAILABLE = False

if not BYPASS_IMPORT:
    from app.persistence.supabase_task_store import SupabaseTaskStore
else:
    class SupabaseTaskStore:
        pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
if not BYPASS_IMPORT:
    try:
        from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
        from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
        A2A_COMPONENTS_AVAILABLE = True
    except Exception as e:
        logger.warning(f"A2A executor components not available: {e}")
        A2A_COMPONENTS_AVAILABLE = False

    try:
        from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        ADK_CORE_AVAILABLE = True
    except Exception as e:
        logger.warning(f"ADK core components not available: {e}")
        ADK_CORE_AVAILABLE = False
else:
    A2A_COMPONENTS_AVAILABLE = False
    ADK_CORE_AVAILABLE = False

try:
    from google.cloud import logging as google_cloud_logging
except ImportError:
    google_cloud_logging = None

if not BYPASS_IMPORT:
    from app.agent import app as adk_app
else:
    class MockAdkApp:
        name = "pikar-ai"
        root_agent = None
    adk_app = MockAdkApp()

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

# Import persistent session service (with fallback to InMemory for local dev)
if not BYPASS_IMPORT:
    try:
        from app.persistence.supabase_session_service import SupabaseSessionService
        session_service = SupabaseSessionService()
    except Exception as e:
        logger.warning(f"Failed to initialize SupabaseSessionService, falling back to InMemory: {e}")
        session_service = InMemorySessionService()
else:
    class MockSessionService:
        pass
    session_service = MockSessionService()

# setup_telemetry()
# _, project_id = google.auth.default()
# logging_client = google_cloud_logging.Client()
# logger = logging_client.logger(__name__)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")
if ADK_CORE_AVAILABLE:
    artifact_service = (
        GcsArtifactService(bucket_name=logs_bucket_name)
        if logs_bucket_name
        else InMemoryArtifactService()
    )
else:
    artifact_service = None

if ADK_CORE_AVAILABLE:
    runner = Runner(
        app=adk_app,
        artifact_service=artifact_service,
        session_service=session_service,  # Now uses Supabase-backed sessions
    )
else:
    runner = None

if A2A_AVAILABLE and A2A_COMPONENTS_AVAILABLE and ADK_CORE_AVAILABLE:
    request_handler = DefaultRequestHandler(
        agent_executor=A2aAgentExecutor(runner=runner), 
        task_store=SupabaseTaskStore() # PERSISTENCE UPGRADE
    )
    A2A_RPC_PATH = f"/a2a/{adk_app.name}"
else:
    request_handler = None
    A2A_RPC_PATH = None

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from app.middleware.rate_limiter import limiter
from datetime import datetime


async def build_dynamic_agent_card() -> Optional["AgentCard"]:
    """Builds the Agent Card dynamically from the root_agent."""
    if not A2A_AVAILABLE or not A2A_COMPONENTS_AVAILABLE or not ADK_CORE_AVAILABLE:
        return None
    agent_card_builder = AgentCardBuilder(
        agent=adk_app.root_agent,
        capabilities=AgentCapabilities(streaming=True),
        rpc_url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        agent_version=os.getenv("AGENT_VERSION", "0.1.0"),
    )
    agent_card = await agent_card_builder.build()
    return agent_card


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    if A2A_AVAILABLE and A2A_COMPONENTS_AVAILABLE and ADK_CORE_AVAILABLE:
        try:
            agent_card = await build_dynamic_agent_card()
            a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
            a2a_app.add_routes_to_app(
                app_instance,
                agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
                rpc_url=A2A_RPC_PATH,
                extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
            )
            logger.info("A2A routes initialized successfully")
        except Exception as e:
            logger.warning(f"A2A initialization failed (non-fatal): {e}. App will continue without A2A features.")
    yield


app = FastAPI(
    title="pikar-ai",
    description="API for interacting with the Agent pikar-ai",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# #region agent log - Request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        logger.info(f"[DEBUG] Incoming request: {request.method} {request.url.path} from Origin: {request.headers.get('origin', 'N/A')}")
        response = await call_next(request)
        logger.info(f"[DEBUG] Response: {response.status_code} for {request.method} {request.url.path}")
        return response

app.add_middleware(RequestLoggingMiddleware)
# #endregion

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register scheduled endpoints router for Cloud Scheduler
from app.services.scheduled_endpoints import router as scheduled_router
from app.routers.files import router as files_router
from app.routers.approvals import router as approvals_router
from app.routers.org import router as org_router
from app.routers.briefing import router as briefing_router
from app.routers.departments import router as departments_router
from app.routers.pages import router as pages_router
from app.routers.onboarding import router as onboarding_router
from app.routers.workflows import router as workflows_router

app.include_router(scheduled_router)
app.include_router(files_router, tags=["Files"])
app.include_router(approvals_router, tags=["Approvals"])
app.include_router(org_router, tags=["Organization"])
app.include_router(briefing_router, tags=["Briefing"])
app.include_router(departments_router, tags=["Departments"])
app.include_router(pages_router, tags=["Pages"])
app.include_router(onboarding_router)
app.include_router(workflows_router, tags=["Workflows"])



@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


@app.get("/health/connections", tags=["Health"])
async def get_connection_pool_health():
    """Monitor Supabase connection pool stats and cache health."""
    from datetime import datetime
    try:
        from app.services.supabase import get_client_stats, get_service_client
        from app.rag.knowledge_vault import get_rag_client_stats, get_supabase_client
        
        service_stats = get_client_stats()
        rag_stats = get_rag_client_stats()
        
        # Verify Service Client Connectivity
        try:
            service_client = get_service_client()
            if not service_client:
                raise ValueError("Service client failed to initialize")
            # Lightweight connectivity check
            service_client.table("skills").select("count", count="exact").limit(0).execute()
        except Exception as e:
            raise ValueError(f"Service client connectivity check failed: {e}")
            
        # Verify RAG Client Connectivity
        try:
            rag_client = get_supabase_client()
            if not rag_client:
                raise ValueError("RAG client failed to initialize")
            # Lightweight connectivity check
            rag_client.table("agent_knowledge").select("count", count="exact").limit(0).execute()
        except Exception as e:
            raise ValueError(f"RAG client connectivity check failed: {e}")
        
        # Build base response
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "pools": {
                "service_client": service_stats,
                "rag_client": rag_stats
            },
            "efficiency_note": "Creation counts should remain stable (1) after initialization."
        }
        
        # Add Cache Health
        from app.services.cache import get_cache_service
        cache = get_cache_service()
        cache_stats = await cache.get_stats()
        cache_healthy = await cache.is_healthy()
        
        response["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
            "stats": cache_stats,
            "transport": "async_redis"
        }
        
        return response
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/health/cache", tags=["Health"])
async def get_cache_health():
    """Monitor Redis cache health and performance."""
    from app.services.cache import get_cache_service
    cache = get_cache_service()
    
    stats = await cache.get_stats()
    is_healthy = await cache.is_healthy()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/admin/cache/invalidate", tags=["Admin"])
async def invalidate_cache(user_id: Optional[str] = None):
    """Invalidate cache for a specific user or all users."""
    from app.services.cache import get_cache_service
    cache = get_cache_service()
    
    if user_id:
        await cache.invalidate_user_all(user_id)
        return {"status": "success", "message": f"Cache invalidated for user {user_id}"}
    else:
        # Invalidate all caches (use with caution)
        await cache.flush_all()
        return {"status": "success", "message": "All caches invalidated"}

from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from google.genai import types as genai_types

# SSE Request Models
class TextPart(BaseModel):
    text: str

class NewMessage(BaseModel):
    parts: List[TextPart]

class ChatRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    new_message: NewMessage

@app.post("/a2a/app/run_sse")
async def run_sse(request: ChatRequest):
    """Custom SSE endpoint for agent chat."""
    if not runner:
        logger.error("ADK Runner not initialized")
        return {"error": "Runner not initialized"}

    logger.info(f"Starting SSE chat for session {request.session_id}")
    
    # Extract text from message parts
    user_text = " ".join([p.text for p in request.new_message.parts])
    
    # Create ADK Content object for the new message
    adk_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_text)]
    )
    
    # Use default user_id if not provided
    effective_user_id = request.user_id or "anonymous"
    
    # Ensure session exists before running agent
    try:
        existing_session = await session_service.get_session(
            app_name=adk_app.name,
            user_id=effective_user_id,
            session_id=request.session_id
        )
        if not existing_session:
            logger.info(f"Creating new session {request.session_id} for user {effective_user_id}")
            await session_service.create_session(
                app_name=adk_app.name,
                user_id=effective_user_id,
                session_id=request.session_id
            )
    except Exception as e:
        logger.warning(f"Session check/creation failed: {e}")
        # Continue anyway - the runner might handle this
    
    async def event_generator():
        try:
            logger.info(f"Calling runner.run_async for session {request.session_id} user {effective_user_id}")
            # Run the agent asynchronously
            try:
                # ADK Runner requires new_message as a Content object
                response_stream = runner.run_async(
                    session_id=request.session_id,
                    new_message=adk_message,
                    user_id=effective_user_id
                )
            except Exception as e:
                 logger.error(f"Failed to start runner: {e}", exc_info=True)
                 yield f"data: {{\"error\": \"Runner failed to start: {str(e)}\"}}\n\n"
                 return

            logger.info("Runner started, iterating stream...")
            async for event in response_stream:
                logger.info(f"Received event type: {type(event)}")
                # Serialize event to JSON
                # Using model_dump_json() if available, else standard json dump
                if hasattr(event, "model_dump_json"):
                    data = event.model_dump_json()
                elif hasattr(event, "to_json"):
                    data = event.to_json()
                else:
                    # Fallback serialization
                    data = json.dumps(event, default=lambda o: str(o))
                
                yield f"data: {data}\n\n"
            
            logger.info("Stream finished normally")
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}", exc_info=True)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")



# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

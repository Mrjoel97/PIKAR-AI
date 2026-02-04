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
from dotenv import load_dotenv
load_dotenv('app/.env')
from typing import Optional, AsyncIterator, Annotated, List, Dict, Any, Union
from contextlib import asynccontextmanager
print("Importing google.auth...")
import google.auth
BYPASS_IMPORT = os.environ.get("LOCAL_DEV_BYPASS") == "1"

if not BYPASS_IMPORT:
    try:
        print("Importing a2a components...")
        from a2a.server.apps import A2AFastAPIApplication
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.types import AgentCapabilities, AgentCard
        from a2a.utils.constants import (
            AGENT_CARD_WELL_KNOWN_PATH,
            EXTENDED_AGENT_CARD_PATH,
        )
        A2A_AVAILABLE = True
    except Exception as e:
        print(f"Warning: A2A components not available or timed out: {e}")
        A2A_AVAILABLE = False
else:
    print("Bypassing a2a imports...")
    A2A_AVAILABLE = False

if not BYPASS_IMPORT:
    from app.persistence.supabase_task_store import SupabaseTaskStore
else:
    class SupabaseTaskStore:
        pass
print("Importing fastapi...")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
if not BYPASS_IMPORT:
    try:
        print("Importing a2a.agent_executor...")
        from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
        from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
        A2A_COMPONENTS_AVAILABLE = True
    except Exception as e:
        print(f"Warning: A2A components not available: {e}")
        A2A_COMPONENTS_AVAILABLE = False

    try:
        print("Importing google.adk core...")
        from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        ADK_CORE_AVAILABLE = True
    except Exception as e:
        print(f"Warning: ADK core components not available: {e}")
        ADK_CORE_AVAILABLE = False
else:
    print("Bypassing ADK imports...")
    A2A_COMPONENTS_AVAILABLE = False
    ADK_CORE_AVAILABLE = False

try:
    print("Importing google.cloud.logging...")
    from google.cloud import logging as google_cloud_logging
except ImportError:
    google_cloud_logging = None

if not BYPASS_IMPORT:
    print("Importing app.agent...")
    from app.agent import app as adk_app
else:
    print("Bypassing app.agent import...")
    class MockAdkApp:
        name = "pikar-ai"
        root_agent = None
    adk_app = MockAdkApp()
print("Importing app.app_utils.telemetry...")
from app.app_utils.telemetry import setup_telemetry
print("Importing app.app_utils.typing...")
from app.app_utils.typing import Feedback
print("All imports in fast_api_app.py done.")

# Import persistent session service (with fallback to InMemory for local dev)
if not BYPASS_IMPORT:
    try:
        from app.persistence.supabase_session_service import SupabaseSessionService
        session_service = SupabaseSessionService()
    except Exception as e:
        import logging
        logging.warning(f"Failed to initialize SupabaseSessionService, falling back to InMemory: {e}")
        session_service = InMemorySessionService()
else:
    class MockSessionService:
        pass
    session_service = MockSessionService()

# setup_telemetry()
# _, project_id = google.auth.default()
# logging_client = google_cloud_logging.Client()
# logger = logging_client.logger(__name__)
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app.add_middleware(SlowAPIMiddleware, limiter=limiter)
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
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
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

app.include_router(scheduled_router)
app.include_router(files_router, tags=["Files"])
app.include_router(approvals_router, tags=["Approvals"])
app.include_router(org_router, tags=["Organization"])
app.include_router(briefing_router, tags=["Briefing"])
app.include_router(departments_router, tags=["Departments"])
app.include_router(pages_router, tags=["Pages"])
app.include_router(onboarding_router)



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
    """Monitor Supabase connection pool status and efficiency."""
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
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "pools": {
                "service_client": service_stats,
                "rag_client": rag_stats
            },
            "efficiency_note": "Creation counts should remain stable (1) after initialization."
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

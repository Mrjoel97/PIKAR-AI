import os
import sys

# Force API key mode to see if it fixes ADK import
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
# Also force invalid creds to fail fast if ADC is attempted
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "dummy_creds.json"

# Mock EVERYTHING related to GCP/OTEL to prevent hang
import sys
from unittest.mock import MagicMock
sys.modules["google.cloud"] = MagicMock()
sys.modules["google.cloud.aiplatform"] = MagicMock()
sys.modules["google.cloud.aiplatform_v1"] = MagicMock()
sys.modules["google.auth"] = MagicMock()
sys.modules["google.auth.credentials"] = MagicMock()
sys.modules["google.auth.transport"] = MagicMock()
sys.modules["google.auth.transport.requests"] = MagicMock()
sys.modules["google.oauth2"] = MagicMock()
sys.modules["google.oauth2.service_account"] = MagicMock()
sys.modules["vertexai"] = MagicMock()
sys.modules["google.api_core"] = MagicMock()
sys.modules["opentelemetry"] = MagicMock()
sys.modules["opentelemetry.trace"] = MagicMock()

# Ensure google module has attributes
import google
google.auth = sys.modules["google.auth"]
google.cloud = sys.modules["google.cloud"]
google.oauth2 = sys.modules["google.oauth2"]

print("Testing LlmAgent dependencies with MOCKS...")
try:
    print("Importing google.adk.events.event...")
    from google.adk.events import event
    print("SUCCESS")

    print("Importing google.adk.models.llm_request...")
    from google.adk.models import llm_request
    print("SUCCESS")

    print("Importing google.adk.tools.base_tool...")
    from google.adk.tools import base_tool
    print("SUCCESS")

    print("Importing google.adk.telemetry.tracing...")
    from google.adk.telemetry import tracing
    print("SUCCESS")

    print("Importing google.adk.agents.base_agent...")
    from google.adk.agents import base_agent
    print("SUCCESS: BaseAgent")

    print("Importing google.adk.flows.llm_flows.auto_flow...")
    from google.adk.flows.llm_flows import auto_flow
    print("SUCCESS")

    print("Importing google.adk.agents.llm_agent...")
    from google.adk.agents import llm_agent
    print("SUCCESS: LlmAgent")

except Exception as e:
    print(f"Error: {e}")

print("Done.")

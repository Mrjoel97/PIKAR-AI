import sys
import os
import pytest
from fastapi.testclient import TestClient

from app.fast_api_app import app
from a2a.types import Message, Role, Part, TextPart, MessageSendParams, SendStreamingMessageRequest
import uuid
import json

client = TestClient(app)

class TestA2AProtocol:
    """End-to-end integration tests for A2A protocol."""
    
    def test_agent_card_retrieval(self):
        """Verify the agent publishes a valid Agent Card."""
        # Note: The path might be dynamic, but based on fast_api_app.py it starts with /a2a
        # We'll try to discover it or use the default we found.
        # fast_api_app.py: A2A_RPC_PATH = f"/a2a/{adk_app.name}"
        # If app.name is "pikar_ai_agent" (we need to confirm this from app/agent.py)
        
        # We can also check the routes in the app to find the correct path
        routes = [route.path for route in app.routes]
        print(f"Available routes: {routes}")
        
        # Assuming the agent name is pikar_ai_agent or similar. 
        # But a safer way is to query the well-known path if mapped? 
        # fast_api_app.py wraps it in lifespan, so routes exist after startup.
        
        with TestClient(app) as local_client:
            # We need to find the card URL. 
            # Strategy: List routes and find one ending in agent-card.json
            card_url = next((r.path for r in app.routes if r.path.endswith("agent-card.json")), None)
            assert card_url is not None, "Could not find agent-card.json route"
            
            response = local_client.get(card_url)
            assert response.status_code == 200
            card = response.json()
            
            assert "name" in card
            assert "description" in card
            assert "capabilities" in card
            assert "protocolVersion" in card

    def test_send_message_and_receive_response(self):
        """Verify the agent can receive a message and return a response via A2A."""
        with TestClient(app) as local_client:
            # 1. Get RPC URL from routes
            # Look for the main message:send or similar endpoint, or just the base A2A path
            # A2A adds a POST route for the app. The logic in A2AFastAPIApplication adds routes.
            # Usually strict A2A uses a streaming endpoint or message:send.
            
            # Let's inspect the A2A_RPC_PATH from the card first
            card_url = next((r.path for r in app.routes if r.path.endswith("agent-card.json")), None)
            card = local_client.get(card_url).json()
            # In local test, the card might give an absolute URL with http://0.0.0.0:8000
            # We need the relative path for TestClient
            rpc_url_full = card.get("url") # This is usually the RPC URL
            # Parse relative path
            from urllib.parse import urlparse
            rpc_path = urlparse(rpc_url_full).path
            
            # The A2A endpoint for sending messages is typically [RPC_URL] (POST) for streaming
            # or [RPC_URL]/message:send for REST. 
            # The python SDK/notebook uses SendStreamingMessageRequest to [RPC_URL]
            
            # 2. Construct Message
            message_id = str(uuid.uuid4())
            msg = Message(
                message_id=f"msg-user-{message_id}",
                role=Role.user,
                parts=[Part(root=TextPart(text="Hello! Who are you?"))]
            )
            
            request_payload = SendStreamingMessageRequest(
                id=f"req-{message_id}",
                params=MessageSendParams(message=msg)
            ).model_dump(mode="json", exclude_none=True)
            
            # 3. Send Request
            response = local_client.post(
                rpc_path,
                json=request_payload,
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200
            
            # 4. Process Streaming Response
            # TestClient stream response is a bit different, but for standard execution 
            # we should get NDJSON (Newline Delimited JSON).
            
            lines = response.text.strip().split('\n')
            assert len(lines) > 0
            
            received_response_text = ""
            task_completed = False
            
            for line in lines:
                if not line.startswith("data: "):
                    continue
                
                event_data = json.loads(line[6:]) # Skip "data: "
                
                # We expect events like:
                # {"task": {"id": "...", "status": {"state": "TASK_STATE_IN_PROGRESS"}}}
                # or {"task": {..., "artifacts": [...]}}
                
                if "task" in event_data:
                    status = event_data["task"].get("status", {}).get("state")
                    if status == "TASK_STATE_COMPLETED":
                        task_completed = True
                        # Extract answer
                        artifacts = event_data["task"].get("artifacts", [])
                        for artifact in artifacts:
                            for part in artifact.get("parts", []):
                                if "text" in part:
                                    received_response_text += part["text"]
            
            assert task_completed, "Task did not reach COMPLETED state"
            assert len(received_response_text) > 0, "Agent did not return any text response"
            print(f"Agent response: {received_response_text}")


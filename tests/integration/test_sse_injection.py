import sys
import os
import json
import unittest

sys.path.append(os.getcwd())

# Mock environment variables BEFORE importing fast_api_app to satisfy its startup logic if needed
os.environ["LOCAL_DEV_BYPASS"] = "1" 

# Import from the extracted module
from app.sse_utils import extract_widget_from_event
_extract_widget_from_event = extract_widget_from_event

class TestSSEInjection(unittest.TestCase):
    def test_failure_injection(self):
        # Simulate tool output from create_video_with_veo (failure)
        tool_result = {
            "success": False,
            "error": "Video generation is temporarily unavailable.",
            "user_message": "User friendly error message.",
            "prompt": "test"
        }
        
        # Simulate ADK event structure
        event = {
            "content": {
                "parts": [
                    {
                        "functionResponse": {
                            "name": "create_video_with_veo",
                            "response": tool_result
                        }
                    }
                ]
            }
        }
        event_json = json.dumps(event)
        
        # Run extraction
        processed_json = _extract_widget_from_event(event_json)
        processed = json.loads(processed_json)
        
        # Verify text injection
        parts = processed["content"]["parts"]
        print(f"FAILED PARTS: {parts}")
        self.assertTrue(any(p.get("text") == "User friendly error message." for p in parts))
        print("Failure injection test PASSED")

    def test_success_injection(self):
        # Simulate tool output (success with widget)
        tool_result = {
            "type": "video",
            "title": "Generated video",
            "data": {"videoUrl": "http://foo.com"}
        }
        
        event = {
            "content": {
                "parts": [
                    {
                        "functionResponse": {
                            "name": "create_video_with_veo",
                            "response": tool_result
                        }
                    }
                ]
            }
        }
        event_json = json.dumps(event)
        
        processed_json = _extract_widget_from_event(event_json)
        processed = json.loads(processed_json)
        
        # Verify widget key
        self.assertIn("widget", processed)
        self.assertEqual(processed["widget"]["type"], "video")
        
        # Verify synthetic text
        parts = processed["content"]["parts"]
        # Default message for video
        self.assertTrue(any("Here's your video" in p.get("text", "") for p in parts))
        print("Success injection test PASSED")

if __name__ == "__main__":
    unittest.main()

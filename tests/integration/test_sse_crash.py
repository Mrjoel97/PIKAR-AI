import sys
import os
import json
import unittest

sys.path.append(os.getcwd())
os.environ["LOCAL_DEV_BYPASS"] = "1" 

# Import from the extracted module
from app.sse_utils import extract_widget_from_event
_extract_widget_from_event = extract_widget_from_event

class TestSSECrash(unittest.TestCase):
    def test_crash_injection(self):
        # Simulate ADK crash output (error at top level of functionResponse)
        event = {
            "content": {
                "parts": [
                    {
                        "functionResponse": {
                            "name": "create_video_with_veo",
                            "error": "Unexpected Import Error: No module named google"
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
        print(f"PARTS: {parts}")
        
        # We expect the error to be injected as text
        has_text = any("Unexpected Import Error" in p.get("text", "") for p in parts)
        if not has_text:
            print("FAILURE: No text injected for crash!")
        
        self.assertTrue(has_text)

if __name__ == "__main__":
    unittest.main()


import asyncio
import logging
import os
import sys
import importlib.util

# Configure logging to see the output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure env var is set for the test
os.environ["REMOTION_RENDER_ENABLED"] = "1"
os.environ["REMOTION_RENDER_TIMEOUT"] = "300" # 5 mins for initial install
os.environ["HOME"] = "/tmp" # Workaround for missing home dir in current container

def load_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

async def test_remotion():
    print("Testing Remotion Render...")
    try:
        # Load service directly to avoid app.__init__ and mcp conflict
        service_path = os.path.join(os.getcwd(), "app/services/remotion_render_service.py")
        remotion_render_service = load_module_from_path("remotion_render_service", service_path)
        
        # Test short video
        prompt = "A futuristic city with flying cars"
        duration = 3 # seconds
        user_id = "debug-user"
        
        image_url = "https://images.unsplash.com/photo-1579546929518-9e396f3cc809?ixlib=rb-4.0.3&w=1080&q=80"
        
        print("Calling render_scenes_to_mp4 with image...")
        mp4_bytes, asset_id = await asyncio.to_thread(
            remotion_render_service.render_scenes_to_mp4,
            prompt, duration, user_id, image_url
        )
        
        if mp4_bytes:
            print(f"Success! Generated {len(mp4_bytes)} bytes. Asset ID: {asset_id}")
        else:
            print("Failed: No output returned.")
            
    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_remotion())

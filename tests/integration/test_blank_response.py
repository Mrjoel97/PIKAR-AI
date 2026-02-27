import asyncio
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Add app to path
sys.path.append(os.getcwd())

async def test_blank_response():
    print("Testing create_video_with_veo...")
    
    # We mock get_canva_tool to avoid instantiating the real one which might need env vars we don't have
    # But wait, we want to test CANVA_MEDIA logic.
    
    # Let's mock the DEPENDENCIES of CanvaMCPTool.
    # vertex_video_service.generate_video
    # remotion_render_service.render_scenes_to_mp4
    # supabase client
    
    try:
        from app.mcp.tools.canva_media import create_video_with_veo
    except ImportError as e:
        print(f"ImportError: {e}")
        return

    # Scenario 1: Veo 404, Remotion Fails
    print("\n---/ Scenario 1: Both Fail /---")
    with patch("app.services.vertex_video_service.generate_video") as mock_veo:
        mock_veo.return_value = {"success": False, "error": "Veo 404"}
        
        with patch("app.services.remotion_render_service.render_scenes_to_mp4") as mock_remotion:
            # Mock Remotion failure (returns None tuple as per my analysis)
            mock_remotion.return_value = (None, None)
            
            result = await create_video_with_veo("test prompt")
            print(f"Result: {result}")
            
            if not result:
                print("!! FAILURE: Result is empty/None")
            elif not result.get("success") and result.get("user_message"):
                 print("SUCCESS: Result contains user_message")
            else:
                 print(f"UNKNOWN: {result}")

    # Scenario 2: Veo Success
    print("\n---/ Scenario 2: Veo Success /---")
    with patch("app.services.vertex_video_service.generate_video") as mock_veo:
         mock_veo.return_value = {
             "success": True, 
             "video_url": "http://veo.url/vid.mp4",
             "video_bytes": None
         }
         
         # Mock Supabase in CanvaTool
         with patch("app.mcp.tools.canva_media.CanvaMCPTool.supabase", new_callable=MagicMock) as mock_supabase:
             # If supabase is present, it tries to upload.
             mock_supabase.table.return_value.insert.return_value.execute.return_value = None
             
             with patch("app.rag.knowledge_vault.ingest_document_content", new_callable=AsyncMock):
                 result = await create_video_with_veo("test prompt")
                 print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_blank_response())

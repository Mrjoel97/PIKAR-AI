
import asyncio
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.append(os.getcwd())

from app.services.director_service import DirectorService
from app.services.request_context import set_current_user_id

async def verify_director():
    prompt = "A cinematic trailer for a futuristic cyberpunk city. High speed chase. Neon lights."
    user_id = "test-user-verification"
    
    logger.info(f"Starting verification for user {user_id} with prompt: {prompt}")
    
    try:
        director = DirectorService()
        video_url = await director.create_pro_video(prompt, user_id)
        
        if video_url:
            logger.info(f"SUCCESS: Pro Video created at {video_url}")
        else:
            logger.error("FAILURE: Director returned None")
            
    except Exception as e:
        logger.error(f"EXCEPTION during verification: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_director())

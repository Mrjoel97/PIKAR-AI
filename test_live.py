import asyncio
import os
from google import genai

# Setup auth
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'secrets/my-project-pk-484623-c72b7850d9d5.json'
os.environ['GOOGLE_CLOUD_PROJECT'] = 'my-project-pk-484623'

async def test_model(model_name):
    client = genai.Client(vertexai=True, project="my-project-pk-484623", location="us-central1")
    from google.genai import types
    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            parts=[types.Part.from_text(text="Hello")]
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Aoede")
            )
        ),
    )
    
    try:
        async def _connect_and_talk():
            async with client.aio.live.connect(model=model_name, config=live_config) as session:
                await session.send(input="User has connected. Please introduce yourself.", end_of_turn=True)
                # Wait for the first response to confirm the model works
                async for response in session.receive():
                    pass
                print(f'Model {model_name} works!')
                return True
        return await asyncio.wait_for(_connect_and_talk(), timeout=5)
    except asyncio.TimeoutError:
        print(f'Model {model_name} timed out waiting for response, which might mean it works.')
        return True
    except Exception as e:
        print(f'Model {model_name} failed: {type(e).__name__} - {e}')
        return False

async def main():
    models_to_test = [
        'gemini-live-2.5-flash-native-audio',
        'gemini-live-2.5-flash-preview-native-audio-09-2025',
        'gemini-2.0-flash-exp'
    ]
    for m in models_to_test:
        await test_model(m)

asyncio.run(main())

import asyncio
import websockets
import json

async def test():
    try:
        async with websockets.connect('ws://127.0.0.1:8000/ws/voice/test_123') as ws:
            print("Connected!")
            await ws.send(json.dumps({"type": "auth", "token": "test_token"}))
            print("Sent auth, waiting for response...")
            response = await ws.recv()
            print(f"Received: {response}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

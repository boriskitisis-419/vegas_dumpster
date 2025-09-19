import asyncio
import websockets
from handlers import twilio_handler

async def main():
    print("[Server] Starting...")
    async with websockets.serve(twilio_handler, "0.0.0.0", 5000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

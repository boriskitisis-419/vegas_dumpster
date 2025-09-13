import asyncio
import base64
import json
import websockets
import os
from datetime import datetime
from dumpster_functions import FUNCTION_MAP
from config import CONFIG
import os

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
load_dotenv()

DEEPGRAM_WS_URL = "wss://agent.deepgram.com/v1/agent/converse"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
elevenlabs = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

SILENCE_TIMEOUT = 20
FINAL_TIMEOUT = 20

async def stream_ulab_audio_from_bytes(audio_stream, session, chunk_size=3200, delay=0.02):
    audio_stream.seek(0)  # start from beginning
    audio_bytes = audio_stream.read()

    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i + chunk_size]

        media_msg = {
            "event": "media",
            "streamSid": getattr(session.twilio_ws, "streamsid", None),
            "media": {"payload": base64.b64encode(chunk).decode("ascii")},
        }

        try:
            await session.twilio_ws.send(json.dumps(media_msg))
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"[stream_ulaw_audio] Error sending chunk: {e}")
            break

async def stream_agent_text(text, session, chunk_size=3200, delay=0.02):
    # === Step 1: Generate 16kHz PCM WAV from ElevenLabs ===
    response = elevenlabs.text_to_speech.stream(
        voice_id=f"{ELEVENLABS_VOICE_ID}",
        output_format="ulaw_8000",
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.8,
            similarity_boost=1.0,
            style=0.1,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )
    audio_bytes = b"".join(response)  # raw µ-law bytes

    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        media_msg = {
            "event": "media",
            "streamSid": getattr(session.twilio_ws, "streamsid", None),
            "media": {"payload": base64.b64encode(chunk).decode("ascii")},
        }
        await session.twilio_ws.send(json.dumps(media_msg))
    
class CallSession:
    def __init__(self, twilio_ws, sts_ws):
        self.twilio_ws = twilio_ws
        self.sts_ws = sts_ws
        self.finish_call_sent = False
        self.silence_task = None
        self.final_task = None        

    async def nudge(self):
        print("[Silence Watchdog] User inactive. Sending nudge audio.")
        await stream_ulaw_audio("deepgram_tts/check_activity.ulaw", self)
        await asyncio.sleep(10.0)
        self.final_task = asyncio.create_task(self.final_hangup())

    async def final_hangup(self):
        print("[Final Hangup] Playing final audio and closing call.")
        await stream_ulaw_audio("deepgram_tts/finish_call.ulaw", self)
        await asyncio.sleep(6.0)
        await self.twilio_ws.close()
        print("[Final Hangup] Twilio socket closed, call ended.")

    async def start_silence_timer(self):
        if self.silence_task:
            self.silence_task.cancel()
        self.silence_task = asyncio.create_task(self._silence_watchdog())
        print("[Silence Timer] Started/Reset.")

    async def _silence_watchdog(self):
        await asyncio.sleep(SILENCE_TIMEOUT)
        await self.nudge()

# ------------------- Function Calls -------------------
def execute_function_call(func_name, arguments):
    if func_name in FUNCTION_MAP:
        result = FUNCTION_MAP[func_name](**arguments)
        print(f"[Function call] {func_name} result: {result}")
        return result
    print(f"[Function call] Unknown function: {func_name}")
    return {"error": f"Unknown function: {func_name}"}

def create_function_call_response(func_id, func_name, result):
    return {
        "type": "FunctionCallResponse",
        "id": func_id,
        "name": func_name,
        "content": json.dumps(result),
    }

async def handle_function_call_request(decoded, session: CallSession):
    for function_call in decoded.get("functions", []):
        func_name = function_call["name"]
        func_id = function_call["id"]
        arguments = json.loads(function_call["arguments"])
        print(f"[Function call request] {func_name}, arguments: {arguments}")

        result = execute_function_call(func_name, arguments)
        response = create_function_call_response(func_id, func_name, result)

        if func_name == "finish_call" and arguments.get("client_wants_to_finish", False):
            session.finish_call_sent = True
            print(f"[Function call response] Sent finish_call")
            print("aaa")
        try:
            await session.sts_ws.send(json.dumps(response))
        except Exception as e:
            print(f"[Function call finish_call] Error sending: {e}")

# ------------------- Pre-recorded .ulaw streaming -------------------
async def stream_ulaw_audio(file_path: str, session, chunk_size: int = 32000, delay: float = 0.02):
    try:
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        print(f"[stream_ulaw_audio] Failed to read {file_path}: {e}")
        return

    print(f"[Agent Audio] Streaming {file_path}, size={len(audio_bytes)} bytes")
    for i in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[i:i+chunk_size]
        media_msg = {
            "event": "media",
            "streamSid": getattr(session.twilio_ws, "streamsid", None),
            "media": {"payload": base64.b64encode(chunk).decode("ascii")},
        }
        try:
            await session.twilio_ws.send(json.dumps(media_msg))
            await asyncio.sleep(delay)
        except Exception as e:
            print(f"[stream_ulaw_audio] Error sending chunk: {e}")
            break
    print(f"[Agent Audio] Finished streaming {file_path}")

# ------------------- STS / Twilio handlers -------------------
async def handle_text_message(decoded, session: CallSession):
    msg_type = decoded.get("type")
    msg_role = decoded.get("role")
    msg_content = decoded.get("content")

    if msg_type == "ConversationText":
        if msg_role == "assistant":
            print(f"Bot: {msg_content}")
            await stream_agent_text(msg_content, session)
        else:
            print(f"Chris: {msg_content}")

    if msg_type == "FunctionCallRequest":
        await handle_function_call_request(decoded, session)

async def sts_sender(sts_ws, audio_queue):
    while True:
        chunk = await audio_queue.get()
        try:
            await sts_ws.send(chunk)
        except Exception as e:
            print(f"[sts_sender] Error sending chunk: {e}")

async def sts_receiver(session: CallSession):
    try:
        async for message in session.sts_ws:
            if isinstance(message, str):
                try:
                    decoded = json.loads(message)
                except Exception as e:
                    print(f"[STS JSON parse error] {e}")
                    continue
                mtype = decoded.get("type")

                if mtype == "UserStartedSpeaking":
                    print("[Barge-in] User started speaking.")
                    clear_message = {
                        "event": "clear",
                        "streamSid": getattr(session.twilio_ws, "streamsid", None),
                    }
                    try:
                        await session.twilio_ws.send(json.dumps(clear_message))
                    except: pass
                    if session.silence_task:
                        session.silence_task.cancel()
                        session.silence_task = None

                elif mtype == "AgentAudioDone":
                    if session.finish_call_sent:
                        await asyncio.sleep(3)
                        await session.twilio_ws.close()
                        await session.sts_ws.close()
                        return
                    await session.start_silence_timer()

                else:
                    await handle_text_message(decoded, session)

    except Exception as e:
        print(f"[sts_receiver] Exception: {e}")

async def twilio_receiver(twilio_ws, audio_queue):
    try:
        async for message in twilio_ws:
            try:
                data = json.loads(message)
                event = data.get("event")
                if event == "start":
                    twilio_ws.streamsid = data["start"]["streamSid"]
                    print(f"[Twilio Receiver] Stream started, streamSid={twilio_ws.streamsid}")
                elif event == "media":
                    media = data["media"]
                    chunk = base64.b64decode(media["payload"])
                    if media["track"] == "inbound":
                        audio_queue.put_nowait(chunk)
                elif event == "stop":
                    print("[Twilio Receiver] Stream stopped.")
                    break
            except Exception as e:
                print(f"[Twilio receiver error] {e}")
                break
    except Exception as e:
        print(f"[twilio_receiver] Exception: {e}")

async def twilio_handler(twilio_ws):
    audio_queue = asyncio.Queue()
    try:
        async with websockets.connect(
            DEEPGRAM_WS_URL,
            extra_headers={"Authorization": f"Token {DEEPGRAM_API_KEY}"}
        ) as sts_ws:
            await sts_ws.send(json.dumps(CONFIG))
            print("[Twilio Handler] Sent STS config.")

            session = CallSession(twilio_ws, sts_ws)

            await asyncio.gather(
                sts_sender(sts_ws, audio_queue),
                sts_receiver(session),
                twilio_receiver(twilio_ws, audio_queue),
                return_exceptions=True,
            )
    except Exception as e:
        print(f"[Twilio Handler] Exception: {e}")
        try:
            await twilio_ws.close()
        except: pass

# ------------------- Main -------------------
async def main():
    print("[Server] Starting...")
    async with websockets.serve(twilio_handler, "0.0.0.0", 5000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

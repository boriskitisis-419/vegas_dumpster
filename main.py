import asyncio
import base64
import json
import websockets
import os
from datetime import datetime
from dumpster_functions import FUNCTION_MAP
from config import CONFIG
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
import requests
from requests.auth import HTTPBasicAuth
load_dotenv()

DEEPGRAM_WS_URL = "wss://agent.deepgram.com/v1/agent/converse"
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
elevenlabs = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

SILENCE_TIMEOUT = 35
FINAL_TIMEOUT = 10

import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

def download_twilio_recording(recording_sid: str, file_format: str = "wav", dual_channel: bool = True) -> str:
    # Get credentials from environment variables
    
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio credentials are missing. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in your environment.")
    
    # Construct URL
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.{file_format}"
    if dual_channel:
        url += "?RequestedChannels=2"
        
    pst_time = datetime.now(ZoneInfo("America/Los_Angeles"))

    file_name = pst_time.strftime("%m_%d_%H_%M")
    folder_path = "recording/" + pst_time.strftime("%m_%d")

    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    # Download recording
    response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    
    if response.status_code == 200:
        filename = os.path.join(folder_path, f"{file_name}.{file_format}")  # e.g., "09_14/recording.wav"
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Recording downloaded successfully: {filename}")
        return filename
    else:
        raise Exception(f"Failed to download recording. Status code: {response.status_code}\n{response.text}")

def delete_twilio_recording(recording_sid: str):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.json"

    response = requests.delete(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))

    if response.status_code == 204:
        print(f"Recording {recording_sid} deleted successfully.")
    else:
        print(f"Failed to delete recording {recording_sid}: {response.status_code} {response.text}")

async def stream_agent_text(text, session):
    if not hasattr(session, "bot_speaking_count"):
        session.bot_speaking_count = 0

    session.bot_speaking_count += 1
    session.bot_speaking = True

    response = elevenlabs.text_to_speech.stream(
        voice_id=f"{ELEVENLABS_VOICE_ID}",
        output_format="ulaw_8000",
        text=text,
        model_id="eleven_turbo_v2",
        voice_settings=VoiceSettings(
            stability=1,
            similarity_boost=1,
            style=0.7,
            use_speaker_boost=True,
            speed=0.9,
        ),
    )

    audio_bytes = b""
    for chunk in response:
        audio_bytes += chunk

        media_msg = {
            "event": "media",
            "streamSid": getattr(session.twilio_ws, "streamsid", None),
            "media": {"payload": base64.b64encode(chunk).decode("ascii")},
        }
        await session.twilio_ws.send(json.dumps(media_msg))

    duration_sec = len(audio_bytes) / 8000.0

    asyncio.create_task(_mark_bot_done_after(duration_sec, session, text))


async def _mark_bot_done_after(duration, session, text):
    await asyncio.sleep(duration)

    if hasattr(session, "bot_speaking_count") and session.bot_speaking_count > 0:
        session.bot_speaking_count -= 1

    session.bot_speaking = session.bot_speaking_count > 0

class CallSession:
    def __init__(self, twilio_ws, sts_ws):
        self.twilio_ws = twilio_ws
        self.sts_ws = sts_ws
        self.finish_call_sent = False
        self.silence_task = None
        self.final_task = None        
        self.call_sid = None
        self.recording_sid = None
        self.bot_speaking = None
        self.bot_speaking_count = 0
        self.interupt_word = ""
        self.ignore = False

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
        await self.sts_ws.close()
        print("[Final Hangup] Twilio socket closed, call ended.")
        if self.recording_sid:
            print("2. recording_sid is here", self.recording_sid)
            await asyncio.sleep(6.0)
            download_twilio_recording(self.recording_sid)
            delete_twilio_recording(self.recording_sid)

    async def start_silence_timer(self):
        if self.silence_task:
            self.silence_task.cancel()
        self.silence_task = asyncio.create_task(self._silence_watchdog())
        print("[Silence Timer] Started/Reset.")

    async def _silence_watchdog(self):
        await asyncio.sleep(SILENCE_TIMEOUT)
        await self.nudge()

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

async def stream_ulaw_audio(file_path: str, session, chunk_size: int = 64000):
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
        except Exception as e:
            print(f"[stream_ulaw_audio] Error sending chunk: {e}")
            break
    print(f"[Agent Audio] Finished streaming {file_path}")

async def handle_text_message(decoded, session: CallSession):
    msg_type = decoded.get("type")
    msg_role = decoded.get("role")
    msg_content = decoded.get("content")

    if msg_type == "ConversationText":
        if msg_role == "assistant":
            if session.ignore == False:
                print(f"Bot: {msg_content}")
                await stream_agent_text(msg_content, session)
            else:
                print("[Special Case]: Ignored to say, ", msg_content)
        else:
            if session.bot_speaking:
                session.interupt_word = msg_content
                print("     [LOG] Bot was interrupted while speaking!")
                print("     interupt word: ", session.interupt_word)
                MIN_WORDS = 2
                words = session.interupt_word.split()
                if len(words) < MIN_WORDS:
                    session.ignore = True
                    print("     [Ignored] Too few words:", session.interupt_word)
                    print("     $$$$$$$$$$$$$$$$$$$$$[LOG] Trivial user sound, ignoring interruption.")
                else:
                    clear_message = {
                        "event": "clear",
                        "streamSid": getattr(session.twilio_ws, "streamsid", None),
                    }
                    try:
                        await session.twilio_ws.send(json.dumps(clear_message))
                    except: pass

            print(f"Chris: {msg_content}")
            print("##################################\n")

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
                    session.ignore = False
                    print("\n##################################")
                    print("[Barge-in] User started speaking.")
                    if session.silence_task:
                        session.silence_task.cancel()
                        session.silence_task = None

                elif mtype == "AgentAudioDone":
                    if session.finish_call_sent:                        
                        await asyncio.sleep(3)
                        await session.twilio_ws.close()
                        await session.sts_ws.close()      

                        if session.recording_sid:                  
                            await asyncio.sleep(3)
                            print("Finish call sent", session.recording_sid)
                            download_twilio_recording(session.recording_sid)
                            delete_twilio_recording(session.recording_sid)
                        return
                    await session.start_silence_timer()

                else:
                    await handle_text_message(decoded, session)

    except Exception as e:
        print(f"[sts_receiver] Exception: {e}")

async def twilio_receiver(twilio_ws, audio_queue, session: CallSession):
    try:
        async for message in twilio_ws:
            try:
                data = json.loads(message)
                event = data.get("event")
                if event == "start":
                    print(data["start"])
                    twilio_ws.streamsid = data["start"]["streamSid"]
                    session.call_sid = data["start"]["callSid"]
                    
                    # Start Twilio recording
                    if session.call_sid:
                        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{session.call_sid}/Recordings.json"
                        response = requests.post(url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
                        print(response)
                        if response.status_code in [200, 201]:
                            recording_data = response.json()  # parse JSON
                            recording_sid = recording_data.get("sid")  # this is your Recording SID
                            if recording_sid:
                                print(f"[Recording] Started successfully, SID: {recording_sid}")
                                session.recording_sid = recording_sid  # store in session for later download
                            print("[Recording] Call recording started successfully.")
                        else:
                            print(f"[Recording] Failed to start recording: {response.status_code} {response.text}")

                    print(f"[Twilio Receiver] Stream started, streamSid={twilio_ws.streamsid}, callSid={session.call_sid}")

                elif event == "media":
                    media = data["media"]
                    chunk = base64.b64decode(media["payload"])
                    if media["track"] == "inbound":
                        audio_queue.put_nowait(chunk)

                elif event == "stop":
                    session.silence_task.cancel()
                    print("[Twilio Receiver] Stream stopped.")
                    # Download recordings after the call ends
                    if session.recording_sid:
                        await session.twilio_ws.close()
                        await session.sts_ws.close()
                        await asyncio.sleep(6.0)
                        print("3. recording_sid is here", session.recording_sid)
                        download_twilio_recording(session.recording_sid)
                        delete_twilio_recording(session.recording_sid)
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
                twilio_receiver(twilio_ws, audio_queue, session),
                return_exceptions=True,
            )
    except Exception as e:
        print(f"[Twilio Handler] Exception: {e}")
        try:
            await session.twilio_ws.close()
        except: pass

async def main():
    print("[Server] Starting...")
    async with websockets.serve(twilio_handler, "0.0.0.0", 5000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

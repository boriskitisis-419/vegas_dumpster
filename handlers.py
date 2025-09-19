import asyncio
import json
import base64
import requests
import websockets
from requests.auth import HTTPBasicAuth

from config import CONFIG, DEEPGRAM_WS_URL, DEEPGRAM_API_KEY, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
from sessions import CallSession
from elevenlabs_utils import stream_agent_text
from function_calls import execute_function_call, create_function_call_response
from twilio_utils import download_twilio_recording, delete_twilio_recording


# ========== STS HANDLERS ==========
async def sts_sender(sts_ws, audio_queue):
    """Send audio chunks to Deepgram STS."""
    while True:
        chunk = await audio_queue.get()
        try:
            await sts_ws.send(chunk)
        except Exception as e:
            print(f"[sts_sender] Error sending chunk: {e}")


async def sts_receiver(session: CallSession):
    """Receive events/messages from STS."""
    try:
        async for message in session.sts_ws:
            if not isinstance(message, str):
                continue
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


# ========== FUNCTION & TEXT HANDLING ==========
async def handle_text_message(decoded, session: CallSession):
    msg_type = decoded.get("type")
    msg_role = decoded.get("role")
    msg_content = decoded.get("content")

    if msg_type == "ConversationText":
        if msg_role == "assistant":
            if not session.ignore:
                print(f"Bot: {msg_content}")
                await stream_agent_text(msg_content, session)
            else:
                print("[Ignored Assistant]:", msg_content)
        else:
            if session.bot_speaking:
                session.interupt_word = msg_content
                print("[LOG] Bot was interrupted:", session.interupt_word)

                if len(session.interupt_word.split()) < 2:
                    session.ignore = True
                    print("[Ignored] Too few words:", session.interupt_word)
                else:
                    clear_message = {
                        "event": "clear",
                        "streamSid": getattr(session.twilio_ws, "streamsid", None),
                    }
                    try:
                        await session.twilio_ws.send(json.dumps(clear_message))
                    except:
                        pass

            print(f"User: {msg_content}\n{'#'*34}\n")

    if msg_type == "FunctionCallRequest":
        await handle_function_call_request(decoded, session)


async def handle_function_call_request(decoded, session: CallSession):
    for function_call in decoded.get("functions", []):
        func_name = function_call["name"]
        func_id = function_call["id"]
        arguments = json.loads(function_call["arguments"])

        print(f"[FunctionCallRequest] {func_name}, args={arguments}")
        result = execute_function_call(func_name, arguments)
        response = create_function_call_response(func_id, func_name, result)

        if func_name == "finish_call" and arguments.get("client_wants_to_finish", False):
            session.finish_call_sent = True
            print("[FunctionCallResponse] finish_call set")

        try:
            await session.sts_ws.send(json.dumps(response))
        except Exception as e:
            print(f"[FunctionCallResponse] Error sending: {e}")


# ========== TWILIO HANDLERS ==========
async def twilio_receiver(twilio_ws, audio_queue, session: CallSession):
    """Receive audio/events from Twilio websocket."""
    try:
        async for message in twilio_ws:
            try:
                data = json.loads(message)
                event = data.get("event")

                if event == "start":
                    print(f"[Twilio Receiver] Stream started: {data['start']}")
                    twilio_ws.streamsid = data["start"]["streamSid"]
                    session.call_sid = data["start"]["callSid"]

                    # Start Twilio recording
                    if session.call_sid:
                        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Calls/{session.call_sid}/Recordings.json"
                        response = requests.post(url, auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
                        if response.status_code in [200, 201]:
                            recording_data = response.json()
                            session.recording_sid = recording_data.get("sid")
                            print(f"[Recording] Started, SID: {session.recording_sid}")
                        else:
                            print(f"[Recording] Failed: {response.status_code} {response.text}")

                elif event == "media":
                    media = data["media"]
                    chunk = base64.b64decode(media["payload"])
                    if media.get("track") == "inbound":
                        audio_queue.put_nowait(chunk)

                elif event == "stop":
                    if session.silence_task:
                        session.silence_task.cancel()
                    print("[Twilio Receiver] Stream stopped.")
                    await session.twilio_ws.close()
                    await session.sts_ws.close()
                    break

            except Exception as e:
                print(f"[Twilio Receiver Error] {e}")
                break
    except Exception as e:
        print(f"[twilio_receiver] Exception: {e}")


async def twilio_handler(twilio_ws):
    """Main entrypoint per Twilio websocket connection."""
    audio_queue = asyncio.Queue()
    session = None

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
        if session and session.twilio_ws:
            try:
                await session.twilio_ws.close()
            except:
                pass

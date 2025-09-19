import asyncio
import base64
import json
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)

async def stream_agent_text(text, session):
    if not hasattr(session, "bot_speaking_count"):
        session.bot_speaking_count = 0

    session.bot_speaking_count += 1
    session.bot_speaking = True

    response = elevenlabs.text_to_speech.stream(
        voice_id=ELEVENLABS_VOICE_ID,
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
    asyncio.create_task(_mark_bot_done_after(duration_sec, session))

async def _mark_bot_done_after(duration, session):
    await asyncio.sleep(duration)
    if hasattr(session, "bot_speaking_count") and session.bot_speaking_count > 0:
        session.bot_speaking_count -= 1
    session.bot_speaking = session.bot_speaking_count > 0

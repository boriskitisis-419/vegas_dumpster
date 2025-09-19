import base64
import json

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

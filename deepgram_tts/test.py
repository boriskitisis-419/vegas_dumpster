import os
import uuid
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")
elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def text_to_speech_file(text: str) -> str:
    # Call ElevenLabs TTS API
    response = elevenlabs.text_to_speech.convert(
        voice_id=f"{ELEVENLABS_VOICE_ID}",  # Adam pre-made voice
        output_format="ulaw_8000",
        text=text,
        model_id="eleven_turbo_v2_5",  # turbo model for low latency
        voice_settings=VoiceSettings(
            stability=0.8,
            similarity_boost=1.0,
            style=0.1,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # Generate unique file name
    save_file_path = f"{uuid.uuid4()}.ulaw"

    # Save response chunks into the file
    with open(save_file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print(f"{save_file_path}: A new ulaw file was saved successfully!")
    return save_file_path

if __name__ == "__main__":
    # Example usage
    check_activity = "Hello! Are you still there?"
    finish_call = "Seems like you are so busy! Thank you for your time. Have a great day."
    output_file = text_to_speech_file(check_activity)
    print(f"Saved audio file: {output_file}")

import asyncio
from audio_streaming import stream_ulaw_audio
from twilio_utils import download_twilio_recording, delete_twilio_recording
from config import SILENCE_TIMEOUT

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

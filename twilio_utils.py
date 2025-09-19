import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN

def download_twilio_recording(recording_sid: str, file_format: str = "wav", dual_channel: bool = True) -> str:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise ValueError("Twilio credentials are missing.")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.{file_format}"
    if dual_channel:
        url += "?RequestedChannels=2"

    pst_time = datetime.now(ZoneInfo("America/Los_Angeles"))
    file_name = pst_time.strftime("%m_%d_%H_%M")
    folder_path = "recording/" + pst_time.strftime("%m_%d")
    os.makedirs(folder_path, exist_ok=True)

    response = requests.get(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    if response.status_code == 200:
        filename = os.path.join(folder_path, f"{file_name}.{file_format}")
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Recording downloaded successfully: {filename}")
        return filename
    else:
        raise Exception(f"Failed to download recording: {response.status_code} {response.text}")

def delete_twilio_recording(recording_sid: str):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.json"
    response = requests.delete(url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    if response.status_code == 204:
        print(f"Recording {recording_sid} deleted successfully.")
    else:
        print(f"Failed to delete recording {recording_sid}: {response.status_code} {response.text}")

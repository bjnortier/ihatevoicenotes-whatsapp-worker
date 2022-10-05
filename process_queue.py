import json
import os
import requests
from whisper import load_model, load_audio
from redis import from_url
import time

BEARER = os.environ.get("BEARER")
REDIS_URL = os.environ.get("REDIS_URL")
QUEUE_KEY = os.environ.get("QUEUE_KEY")
print("BEARER", BEARER)
print("REDIS_URL", REDIS_URL)
print("QUEUE_KEY", QUEUE_KEY)

redis = from_url(REDIS_URL)


def init_whisper():
    return load_model("small")


def get(url):
    headers = {"Authorization": f"Bearer {BEARER}"}
    return requests.get(url, headers=headers)


def get_media_url(id):
    url = f"https://graph.facebook.com/v14.0/{id}"
    response = get(url)
    if response.status_code == 200:
        return response.json()["url"]
    else:
        raise Exception(response.content)


def get_media(url):
    response = get(url)
    return response.content


def send_text(number, text):
    url = "https://graph.facebook.com/v14.0/101254459434414/messages"
    headers = {"Authorization": f"Bearer {BEARER}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": number, "text": {"body": text}}
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    if response.status_code != 200:
        print(response.content)
    else:
        print("text sent")


def process_message(message):
    number = message["from"]
    if message["type"] == "audio":
        send_text(number, "🤖s at work...")

        audio_id = message["audio"]["id"]
        file_name = f"{audio_id}.ogg"
        try:
            media_url = get_media_url(audio_id)
            media = get_media(media_url)

            with open(file_name, "wb") as file:
                file.write(media)
            result = model.transcribe(file_name)
            send_text(number, result["text"])
        finally:
            if os.path.exists(file_name):
                os.remove(file_name)


if __name__ == "__main__":
    print(f"Working in: {os.getcwd()}")
    model = init_whisper()
    print("Whisper initialised.")
    while True:
        try:
            (_, encoded) = redis.blpop([QUEUE_KEY])
            message = json.loads(encoded)
            print(message)
            count = 0
            for entry in message["entry"]:
                for change in entry["changes"]:
                    messages = change["value"].get("messages")
                    if messages:
                        for message in messages:
                            process_message(message)
                            count += 1
            print(f"{count} messages processed")
        except Exception as e:
            print(e)
            # To avoid overwhelming errors in the while loop
            time.sleep(1)
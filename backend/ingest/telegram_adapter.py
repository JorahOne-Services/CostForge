import json
import os
import urllib.request

BASE_URL = os.environ.get("COSTFORGE_ENDPOINT", "http://127.0.0.1:17890/ingest")


def emit(message_text: str, chat_type: str = "private", length: int = 0):
    payload = {
        "source": "telegram/bot_api",
        "model": "telegram/bot_api",
        "input_tokens": length,
        "output_tokens": 0,
        "requests": 1,
        "meta": {"chat_type": chat_type, "preview": (message_text or "")[:64]},
    }
    _post(payload)


def _post(payload):
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(BASE_URL, data=data, headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

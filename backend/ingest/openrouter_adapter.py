import json
import os
import urllib.request

BASE_URL = os.environ.get("COSTFORGE_ENDPOINT", "http://127.0.0.1:17890/ingest")


def emit(model: str, input_tokens: int = 0, output_tokens: int = 0, requests: int = 1, meta: dict | None = None):
    payload = {
        "source": f"openrouter/{model or 'pricing'}",
        "model": model or "openrouter/pricing",
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "requests": int(requests or 1),
        "meta": meta or {},
    }
    _post(payload)


def _post(payload):
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            BASE_URL, data=data, headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass

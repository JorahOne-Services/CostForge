from datetime import datetime


def adapt(event: dict) -> dict:
    data = {
        "source": "hermes",
        "model": event.get("model", "unknown"),
        "input_tokens": event.get("input_tokens", 0),
        "output_tokens": event.get("output_tokens", 0),
        "requests": event.get("requests", 1),
        "ts": event.get("ts") or datetime.now().isoformat(),
        "meta": {
            "provider": event.get("provider"),
            "endpoint": event.get("endpoint"),
        },
    }
    return data

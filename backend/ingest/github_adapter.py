import json
import os
import urllib.request

BASE_URL = os.environ.get("COSTFORGE_ENDPOINT", "http://127.0.0.1:17890/ingest")

# Map known GitHub task types to rough relative cost weight.
TASK_COST = {
    "issues_list": 1,
    "issue_create": 2,
    "repo_list": 1,
    "workflow_run": 3,
}
TASK_MODEL = os.environ.get("COSTFORGE_GITHUB_DEFAULT_MODEL", "github/api")


def emit(task: str, *, repo: str = "", requests: int = 1, meta: dict | None = None):
    payload = {
        "source": "github/api",
        "model": TASK_MODEL,
        "input_tokens": 0,
        "output_tokens": 0,
        "requests": int(requests or 1),
        "meta": {
            "task": task,
            "repo": repo,
            **(meta or {}),
        },
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

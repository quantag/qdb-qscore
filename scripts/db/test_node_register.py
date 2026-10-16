import requests
import sys
import json

from config import BASE_URL


def register_node(endpoint, provider_id=None, gpu=0, qpu=0, status=0, caps=None):
    url = f"{BASE_URL}/nodes/register"

    payload = {
        "endpoint": endpoint,
        "gpu": int(gpu),
        "qpu": int(qpu),
        "status": int(status),
        "caps": caps,
    }

    # provider_id is optional: only include when provided
    if provider_id:
        payload["provider_id"] = provider_id

    resp = requests.post(url, json=payload)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Response:", resp.text)


def _parse_caps(arg):
    if arg is None:
        return None
    try:
        return json.loads(arg)
    except Exception:
        return arg


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_node_register.py <endpoint> [gpu] [qpu] [status] [caps_json]")
        print("  python test_node_register.py <provider_id> <endpoint> [gpu] [qpu] [status] [caps_json]")
        sys.exit(1)

    # Decide mode by checking whether argv[1] looks like a UUID.
    # If it contains '-' and has length 36, treat as provider_id; otherwise treat as endpoint.
    a1 = sys.argv[1]
    a2 = sys.argv[2] if len(sys.argv) > 2 else None

    provider_id = None
    endpoint = None
    idx = 2  # next arg index after endpoint

    if a2 and len(a1) == 36 and "-" in a1 and (a2.startswith("http://") or a2.startswith("https://")):
        provider_id = a1
        endpoint = a2
        idx = 3
    else:
        endpoint = a1
        idx = 2

    gpu = sys.argv[idx] if len(sys.argv) > idx else 0
    qpu = sys.argv[idx + 1] if len(sys.argv) > (idx + 1) else 0
    status = sys.argv[idx + 2] if len(sys.argv) > (idx + 2) else 0
    caps_arg = sys.argv[idx + 3] if len(sys.argv) > (idx + 3) else None
    caps = _parse_caps(caps_arg)

    register_node(endpoint, provider_id=provider_id, gpu=gpu, qpu=qpu, status=status, caps=caps)

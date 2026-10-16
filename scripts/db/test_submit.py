#!/usr/bin/env python3
import sys
import json
import base64
import requests

API_URL = "https://quantum.quantag-it.com/api5/qvm/submit"

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_submit.py <qasm_file> <config.json>")
        sys.exit(1)

    qasm_file = sys.argv[1]
    config_file = sys.argv[2]

    # read source file
    with open(qasm_file, "r", encoding="utf-8") as f:
        qasm_code = f.read()
    src_b64 = base64.b64encode(qasm_code.encode("utf-8")).decode("ascii")

    # read config (send it as-is under "config")
    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    payload = {
        "src": src_b64,
        "config": cfg
    }

    # Prefer header for gateway auth if available
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    if isinstance(cfg, dict) and cfg.get("apikey"):
        headers["X-API-Key"] = str(cfg["apikey"])

    print("Submitting job to:", API_URL)
    resp = requests.post(API_URL, json=payload, headers=headers)
    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

if __name__ == "__main__":
    main()

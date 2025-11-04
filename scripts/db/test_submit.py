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
    with open(qasm_file, "r") as f:
        qasm_code = f.read()
    src_b64 = base64.b64encode(qasm_code.encode("utf-8")).decode("ascii")

    # read config
    with open(config_file, "r") as f:
        cfg = json.load(f)

    api_key = cfg["apikey"]
    backend = cfg.get("backend", "ibm")
    options = cfg.get("options", {})
    mode = cfg.get("mode", "sampler")
    shots = cfg.get("shots", 1024)
    src_type = cfg.get("src_type", "qasm")

    payload = {
        "apikey": api_key,
        "src": src_b64,
        "src_type": src_type,
        "execution": {
            "mode": mode,
            "shots": shots
        },
        "backend": backend,
        "options": options
    }

    # send request
    print("Submitting job to:", API_URL)
    resp = requests.post(API_URL, json=payload)
    print("Status:", resp.status_code)
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)

if __name__ == "__main__":
    main()


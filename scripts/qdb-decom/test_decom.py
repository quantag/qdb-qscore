#!/usr/bin/env python3
import sys
import base64
import requests


API_URL = "https://cloud.quantag-it.com/api3/dec"


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} SCRIPT.py")
        sys.exit(1)

    script_path = sys.argv[1]

    # Read the script file
    try:
        with open(script_path, "rb") as f:
            src_bytes = f.read()
    except OSError as e:
        print(f"Failed to read {script_path}: {e}")
        sys.exit(1)

    # Base64 encode the source
    src_b64 = base64.b64encode(src_bytes).decode("ascii")

    payload = {
        "src": src_b64,
        "env": "some"
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"HTTP error: {e}")
        sys.exit(1)

    try:
        data = resp.json()
    except ValueError:
        print("Response is not valid JSON:")
        print(resp.text)
        sys.exit(1)

    status = data.get("status")
    if status == 0:
        res_b64 = data.get("res", "")
        try:
            res = base64.b64decode(res_b64.encode("ascii")).decode("utf-8", errors="replace")
        except Exception as e:
            print(f"Failed to decode result: {e}")
            print("Raw res field:", res_b64)
            sys.exit(1)

        print("Status: 0 (OK)")
        print("Result from server:")
        print(res)
    else:
        print(f"Status: {status}")
        print("Error from server:", data.get("err"))
        sys.exit(1)


if __name__ == "__main__":
    main()

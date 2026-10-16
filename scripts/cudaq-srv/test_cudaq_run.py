import sys
import os
import requests
import base64
import json

URL = "https://cloud.quantag-it.com/api1/run"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.qasm> [shots]")
        sys.exit(1)

    qasm_file = sys.argv[1]
    shots = int(sys.argv[2]) if len(sys.argv) > 2 else 1000

    if not os.path.exists(qasm_file):
        print(f"Error: QASM file not found: {qasm_file}")
        sys.exit(1)

    with open(qasm_file, "r", encoding="utf-8") as f:
        qasm_text = f.read()

    # Encode inputs
    qasm_b64 = base64.b64encode(qasm_text.encode("utf-8")).decode("ascii")
   # shots_b64 = base64.b64encode(str(shots).encode("utf-8")).decode("ascii")

    payload = {
        "qasm_b64": qasm_b64,
        "shots": shots
    }
    print(payload)

    try:
        resp = requests.post(URL, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            print("Success")
            print("Histogram:", data.get("histogram"))
            print("CReg size:", data.get("creg_size"))
        else:
            print("Error", resp.status_code)
            print(resp.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    main()

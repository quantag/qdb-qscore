#!/usr/bin/env python3
"""
Test client for Quantag MBQC microservice.
Usage:
    python test_translate.py path/to/circuit.qasm [output.json]

If no output file is given, it writes to <input>.json.
"""

import sys
import base64
import json
import requests
from pathlib import Path

API_URL = "https://cloud.quantag-it.com/api2/translate"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_translate.py <input.qasm> [output.json]")
        sys.exit(1)

    qasm_path = Path(sys.argv[1])
    if not qasm_path.exists():
        print(f"Error: file not found: {qasm_path}")
        sys.exit(1)

    output_path = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else qasm_path.with_suffix(".json")
    )

    # Read and encode file
    qasm_text = qasm_path.read_text()
    qasm_b64 = base64.b64encode(qasm_text.encode()).decode()

    # Prepare payload
    payload = {
        "src": qasm_b64,
        "output": "all"
    }

    print(f"[*] Sending {qasm_path.name} to {API_URL} ...")

    try:
        response = requests.post(API_URL, json=payload, timeout=60)
    except requests.exceptions.RequestException as e:
        print(f"[!] HTTP error: {e}")
        sys.exit(2)

    if response.status_code != 200:
        print(f"[!] Server returned {response.status_code}")
        print(response.text)
        sys.exit(3)

    result = response.json()
    output_path.write_text(json.dumps(result, indent=2))
    print(f"Saved response to {output_path.resolve()}")

if __name__ == "__main__":
    main()

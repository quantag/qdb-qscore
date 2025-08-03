import sys
import base64
import json
import requests

if len(sys.argv) < 3:
    print("Usage: python test_tokens.py <qasm_file> <model>")
    sys.exit(1)

qasm_file = sys.argv[1]
model = sys.argv[2]
url = "https://cryspprod3.quantag-it.com:444/api12/tokens"

# Read and encode the QASM file
with open(qasm_file, "r", encoding="ascii") as f:
    qasm_code = f.read()

qasm_b64 = base64.b64encode(qasm_code.encode("utf-8")).decode("ascii")

# Prepare JSON payload
payload = {
    "model": model,
    "text_b64": qasm_b64
}

# Send POST request
try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    print("Token count:", response.json()["tokens"])
except requests.exceptions.RequestException as e:
    print("Request failed:", e)
    if e.response is not None:
        print("Response Text:", e.response.text)

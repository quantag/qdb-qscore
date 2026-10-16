import requests
import base64
import sys
import json

if len(sys.argv) != 3:
    print("Usage: python test_submit.py program.qasm setup.yaml")
    sys.exit(1)

qasm_file = sys.argv[1]
yaml_file = sys.argv[2]

# Endpoint
URL = "https://cryspprod2.quantag-it.com:4043/api2/run"

# Read files
with open(qasm_file, "r") as f:
    qasm_code = f.read()

with open(yaml_file, "r") as f:
    yaml_code = f.read()

# Encode to base64
encoded_qasm = base64.b64encode(qasm_code.encode()).decode()
encoded_yaml = base64.b64encode(yaml_code.encode()).decode()

# Build payload
payload = {
    "qasm": encoded_qasm,
    "setup": encoded_yaml
}

# Send request
try:
    response = requests.post(URL, json=payload)  # verify=False for self-signed cert
    print("Status code:", response.status_code)
    print("Raw response:", response.text)

    if response.ok:
        data = response.json()
        if data.get("status") == 0:
            decoded = base64.b64decode(data["res"]).decode()
            print("Decoded result:", decoded)
        else:
            print("Error:", data.get("err"))
except Exception as e:
    print("Request failed:", e)

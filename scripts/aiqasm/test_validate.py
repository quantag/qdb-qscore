import sys
import base64
import requests
import json

if len(sys.argv) < 2:
    print("Usage: python test_validate.py <file.qasm>")
    sys.exit(1)

qasm_path = sys.argv[1]
with open(qasm_path, "r", encoding="utf-8") as f:
    qasm_code = f.read()

qasm_b64 = base64.b64encode(qasm_code.encode("utf-8")).decode("utf-8")

url = "https://cryspprod3.quantag-it.com:444/api12/validate"
payload = {"qasm_b64": qasm_b64}

try:
    response = requests.post(url, json=payload)
    response.raise_for_status()
    result = response.json()
    print(json.dumps(result, indent=2))
except requests.RequestException as e:
    print("Request failed:", e)
    if e.response is not None:
        print("Response Text:", e.response.text)

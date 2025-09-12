import requests
import base64
import json

# Endpoint
URL = "https://cryspprod2.quantag-it.com:4043/api2/run"

# Example OpenQASM program
qasm_code = """OPENQASM 3;
include "stdgates.inc";
qubit q[2];
h q[0];
cx q[0], q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];
"""

# Encode to base64
encoded_src = base64.b64encode(qasm_code.encode()).decode()

# Send request
payload = {"src": encoded_src}
response = requests.post(URL, json=payload, verify=False)  # verify=False if self-signed cert

print("Status code:", response.status_code)
print("Response JSON:", response.json())

# If you want to decode result:
if response.ok and "res" in response.json():
    decoded_result = base64.b64decode(response.json()["res"]).decode()
    print("Decoded result:", decoded_result)

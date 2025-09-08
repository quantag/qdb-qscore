import requests
import base64
import json

URL = "https://cloud.quantag-it.com/api1/run"

# Minimal Bell circuit in OpenQASM 2.0
bell_qasm = """OPENQASM 2.0;
include "qelib1.inc";

qreg q[2];
creg c[2];
h q[0];
cx q[0], q[1];
measure q -> c;
"""

# Encode inputs
qasm_b64 = base64.b64encode(bell_qasm.encode("utf-8")).decode("ascii")
shots_b64 = base64.b64encode(b"1000").decode("ascii")

payload = {
    "qasm_b64": qasm_b64,
    "shots_b64": shots_b64
}

try:
    resp = requests.post(URL, json=payload, timeout=60)
    if resp.status_code == 200:
        data = resp.json()
        if "result_b64" in data:
            result_json = base64.b64decode(data["result_b64"]).decode("utf-8")
            result = json.loads(result_json)
            print("Success")
            print("Histogram:", result.get("histogram"))
            print("CReg size:", result.get("creg_size"))
        else:
            print("Unexpected response:", data)
    else:
        print("Error", resp.status_code)
        print(resp.text)
except Exception as e:
    print("Exception:", e)

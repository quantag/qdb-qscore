import requests

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

payload = {"qasm": bell_qasm}

try:
    resp = requests.post(URL, json=payload, timeout=60)
    if resp.status_code == 200:
        print("Success")
        print("Response:", resp.json())
    else:
        print("Error", resp.status_code)
        print(resp.text)
except Exception as e:
    print("Exception:", e)

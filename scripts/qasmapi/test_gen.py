import sys
import base64
import requests
import os

if len(sys.argv) < 2:
    print("Usage: python test_gen.py <filename>")
    sys.exit(1)

filename = sys.argv[1]
basename = os.path.basename(filename)
qasm_output = basename + ".qasm"

# Read binary file and encode as base64
with open(filename, "rb") as f:
    binary_data = f.read()

b64_data = base64.b64encode(binary_data).decode("ascii")

# Prepare JSON payload
payload = {
    "data": b64_data
}

# URL to your Apache-proxied microservice
url = "https://cryspprod3.quantag-it.com:444/api11/gen_init_qasm"

# Send POST request
response = requests.post(url, json=payload)

# Handle response
if response.ok:
    result = response.json()
    qasm = base64.b64decode(result["qasm_base64"]).decode("utf-8")

    with open(qasm_output, "w") as f:
        f.write(qasm)

    print("Saved OpenQASM to:", qasm_output)
    print("Qubits:", result["num_qubits"])
    print("Norm:", result["norm"])
    print("Used length:", result["used_length"])
else:
    print("Error:", response.status_code)
    print(response.text)

import requests, base64

url2 = "https://qasm2qir-845732993158.europe-west1.run.app/qasm2qir"
url = "https://api.quantag-it.com/qasm2qir"

qasm_code = "OPENQASM 3; qubit[1] q; h q[0];"
payload = {"qasm": base64.b64encode(qasm_code.encode()).decode()}

resp = requests.post(url, json=payload)
data = resp.json()

if data.get("status") == "0":
    qir = base64.b64decode(data["qir"]).decode()
    print("QIR:\n", qir)
else:
    print("Error:", data.get("error"))

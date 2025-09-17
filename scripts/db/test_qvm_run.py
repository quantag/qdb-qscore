import requests
import sys
import base64

from config import BASE_URL

def main():
    if len(sys.argv) < 3:
        print("Usage: python test_qvm_run.py <api_key> <qasm_file> [shots=1000]")
        sys.exit(1)

    api_key = sys.argv[1]
    qasm_file = sys.argv[2]
    shots = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

    # Read QASM file and base64 encode
    with open(qasm_file, "r", encoding="utf-8") as f:
        qasm = f.read()
    qasm_b64 = base64.b64encode(qasm.encode("utf-8")).decode("utf-8")

    url = f"{BASE_URL}/qvm/run"
    payload = {
        "apikey": api_key,
        "qasm": qasm_b64,
        "shots": shots,
        "backend": "cudaq"
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        print("Status code:", response.status_code)
        try:
            data = response.json()
            print("Response:", data)
        except Exception:
            print("Non-JSON response:", response.text)
    except Exception as e:
        print("Error calling API:", str(e))

if __name__ == "__main__":
    main()

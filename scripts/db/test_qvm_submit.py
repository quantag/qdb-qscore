import sys
import base64
import requests

from config import BASE_URL

def main():
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <API_KEY> <QASM_FILE> [shots]")
        sys.exit(1)

    api_key = sys.argv[1]
    qasm_file = sys.argv[2]
    shots = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

    # read file and base64 encode
    with open(qasm_file, "r") as f:
        qasm_text = f.read()
    qasm_b64 = base64.b64encode(qasm_text.encode()).decode()

    payload = {
        "apikey": api_key,
        "qasm": qasm_b64,
        "shots": shots
    }

    url = f"{BASE_URL}/qvm/submit"
    print(f"POST {url}")
    resp = requests.post(url, json=payload)
    print("Status code:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Non-JSON response:", resp.text)

if __name__ == "__main__":
    main()

import sys
import base64
import requests
import json

ENDPOINT = "https://cryspprod3.quantag-it.com:444/api12/join"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_join.py chunk1.qasm chunk2.qasm ...")
        sys.exit(1)

    chunk_files = sys.argv[1:]
    chunks_b64 = []

    for fname in chunk_files:
        try:
            with open(fname, "r", encoding="utf-8") as f:
                content = f.read()
                b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
                chunks_b64.append(b64)
        except Exception as e:
            print(f"Failed to read or encode {fname}: {e}")
            sys.exit(1)

    payload = {
        "chunks_b64": chunks_b64
    }

    try:
        response = requests.post(ENDPOINT, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        if e.response is not None:
            print("Response JSON:", e.response.json())
        sys.exit(1)

    result = response.json()
    joined_qasm = base64.b64decode(result["joined_qasm_b64"]).decode("utf-8")

    with open("joined_output.qasm", "w", encoding="utf-8") as f:
        f.write(joined_qasm)

    print("Successfully joined QASM chunks into 'joined_output.qasm'")
    print(f"Total lines: {result.get('lines', '?')}")

if __name__ == "__main__":
    main()

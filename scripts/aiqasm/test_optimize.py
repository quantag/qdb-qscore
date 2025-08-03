import base64
import requests
import sys
import os

# === Endpoint Configuration ===
BASE_URL = "https://cryspprod3.quantag-it.com:444/api12/optimize"

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_qasm_file>")
        sys.exit(1)

    qasm_path = sys.argv[1]
    if not os.path.isfile(qasm_path):
        print(f"Error: File not found: {qasm_path}")
        sys.exit(1)

    with open(qasm_path, "r", encoding="utf-8") as f:
        qasm_code = f.read()

    qasm_b64 = base64.b64encode(qasm_code.encode("utf-8")).decode("utf-8")
    payload = {"qasm": qasm_b64}

    try:
        response = requests.post(
            BASE_URL,
            json=payload,
            timeout=15
         #   verify=False  # NOTE: For self-signed certs. Use verify=True in production
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Request failed:", e)
        if e.response is not None:
            try:
                print("Server response:")
                print(e.response.json())
            except Exception:
                print("Raw response:")
                print(e.response.text)
        sys.exit(1)
        

    try:
        result = response.json()
        optimized_b64 = result["qasm"]
        optimized_qasm = base64.b64decode(optimized_b64.encode("utf-8")).decode("utf-8")

#        print("=== Optimized QASM ===")
#        print(optimized_qasm)
        print(result)

        output_path = qasm_path + ".out"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(optimized_qasm)
        print(f"\nSaved to: {output_path}")

    except Exception as e:
        print("Failed to decode response:", e)
        print("Raw response:", response.text)
        sys.exit(1)

if __name__ == "__main__":
    main()

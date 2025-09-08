import sys
import os
import requests
import base64
import json

# Gateway endpoint
URL = "https://qcloud-gateway-asivl5za.ew.gateway.dev/compile"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input.qasm> [type]")
        print("  type = python (default) or cpp")
        sys.exit(1)

    qasm_file = sys.argv[1]
    target_type = sys.argv[2] if len(sys.argv) > 2 else "python"
    target_type = target_type.lower()

    if not os.path.exists(qasm_file):
        print(f"Error: QASM file not found: {qasm_file}")
        sys.exit(1)

    with open(qasm_file, "r", encoding="utf-8") as f:
        qasm_text = f.read()

    # Encode QASM in base64
    qasm_b64 = base64.b64encode(qasm_text.encode("utf-8")).decode("ascii")

    payload = {
        "qasm_b64": qasm_b64,
        "type": target_type
    }

    try:
        resp = requests.post(URL, json=payload, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            if target_type == "cpp" and "kernel_cpp_b64" in data:
                kernel_src = base64.b64decode(data["kernel_cpp_b64"]).decode("utf-8")
                print("Success (C++ mode)")
                print("Generated CUDA-Q C++ kernel code:\n")
                print(kernel_src)
            elif target_type == "python" and "kernel_py_b64" in data:
                kernel_src = base64.b64decode(data["kernel_py_b64"]).decode("utf-8")
                print("Success (Python mode)")
                print("Generated CUDA-Q Python kernel code:\n")
                print(kernel_src)
            else:
                print("Unexpected response:", data)
        else:
            print("Error", resp.status_code)
            print(resp.text)
    except Exception as e:
        print("Exception:", e)

if __name__ == "__main__":
    main()

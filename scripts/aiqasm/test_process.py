import sys
import base64
import requests
import os

API_URL = "https://cryspprod3.quantag-it.com:444/api12/process"

if len(sys.argv) < 2:
    print("Usage: python test_process.py <input.qasm> [model]")
    sys.exit(1)

input_file = sys.argv[1]
model = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o"

with open(input_file, "rb") as f:
    qasm_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "qasm_b64": qasm_b64,
    "model": model
}

try:
    response = requests.post(API_URL, json=payload)
    response.raise_for_status()

    result = response.json()
    print("Response JSON:", result)
    optimized_b64 = result.get("optimized_qasm_b64")

    if optimized_b64:
        output_file = os.path.splitext(input_file)[0] + ".opt.qasm"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(base64.b64decode(optimized_b64).decode("utf-8"))
        print(f"Optimized QASM saved to: {output_file}")
    else:
        print("No optimized QASM returned.")

except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
    if e.response is not None:
        try:
            print("Response JSON:", e.response.json())
        except Exception:
            print("Response Text:", e.response.text)

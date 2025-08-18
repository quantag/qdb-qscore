import base64
import sys
import requests
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_optimize.py <input.qasm>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"File not found: {input_path}")
        sys.exit(1)

    # Step 1: Encode input QASM file to base64
    with open(input_path, "rb") as f:
        qasm_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Step 2: Send POST request to /optimize
    url = "https://cryspprod3.quantag-it.com:444/api16/optimize"
    try:
        response = requests.post(url, json={"qasm": qasm_b64}, verify=False)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Request failed:", e)
        sys.exit(1)

    # Step 3: Handle JSON response
    result = response.json()
    if "qasm" not in result:
        print("Error:", result.get("error", "Unknown error"))
        sys.exit(1)

    # Step 4: Decode optimized QASM and save
    output_path = input_path.with_suffix(".opt.qasm")
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(result["qasm"]))

    print(f"Optimized QASM saved to: {output_path}")

if __name__ == "__main__":
    main()

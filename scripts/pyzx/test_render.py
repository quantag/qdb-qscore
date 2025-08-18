import base64
import json
import sys
import requests
from pathlib import Path

def main():
    if len(sys.argv) != 2:
        print("Usage: python test_render.py <file.qasm>")
        sys.exit(1)

    qasm_path = Path(sys.argv[1])
    if not qasm_path.exists():
        print(f"File not found: {qasm_path}")
        sys.exit(1)

    # Read and encode QASM file
    with open(qasm_path, "rb") as f:
        qasm_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Send to your endpoint
    url = "https://cryspprod3.quantag-it.com:444/api16/render"
    try:
        response = requests.post(url, json={"qasm": qasm_b64}, verify=True)  # Set verify=True if using valid cert
        response.raise_for_status()
    except requests.RequestException as e:
        print("Request failed:", e)
        sys.exit(1)

    # Handle response
    data = response.json()
    if "image" not in data:
        print("No image returned:", data)
        sys.exit(1)

    # Decode and save PNG
    png_data = base64.b64decode(data["image"])
    output_path = qasm_path.with_suffix(".png")
    with open(output_path, "wb") as f:
        f.write(png_data)

    print(f"Saved: {output_path}")

if __name__ == "__main__":
    main()

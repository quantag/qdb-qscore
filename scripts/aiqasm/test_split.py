import sys
import os
import base64
import requests

API_URL = "https://cryspprod3.quantag-it.com:444/api12/split"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_split.py <input_file.qasm> [model] [size]")
        sys.exit(1)

    file_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) >= 3 else None
    size = int(sys.argv[3]) if len(sys.argv) >= 4 else None

    with open(file_path, "r", encoding="utf-8") as f:
        qasm_text = f.read()

    qasm_b64 = base64.b64encode(qasm_text.encode("utf-8")).decode("ascii")

    payload = {"qasm": qasm_b64}
    if model:
        payload["model"] = model
    if size:
        payload["size"] = size

    try:
        response = requests.post(API_URL, json=payload)
        response.raise_for_status()
        result = response.json()

        print(f"Chunk count: {result['chunk_count']}")

        base_name = os.path.splitext(file_path)[0]
        for i, chunk_b64 in enumerate(result["chunks"]):
            chunk_qasm = base64.b64decode(chunk_b64).decode("utf-8")
            output_path = f"{base_name}.part{i}"
            with open(output_path, "w", encoding="utf-8") as out_file:
                out_file.write(chunk_qasm)
            print(f"Wrote: {output_path}")

    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        if e.response is not None:
            try:
                print("Response JSON:", e.response.json())
            except Exception:
                print("Response content:", e.response.text)

if __name__ == "__main__":
    main()

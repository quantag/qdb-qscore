import sys
import base64
import json
import requests

API_BASE = "https://cryspprod3.quantag-it.com:444/api18"

def encode_file(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")

def decode_to_file(data_b64, out_path):
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(data_b64))

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <input-file>")
        sys.exit(1)

    in_path = sys.argv[1]
    if in_path.endswith(".qasm"):
        # Compile
        qasm_b64 = encode_file(in_path)
        resp = requests.post(
            API_BASE + "/compile",
            json={"qasm_b64": qasm_b64}
        )
        if resp.status_code != 200:
            print("Error:", resp.status_code, resp.text)
            sys.exit(1)
        data = resp.json()
        out_path = in_path + ".out.qbin"
        decode_to_file(data["qbin_b64"], out_path)
        print("Compiled OK ->", out_path)

    elif in_path.endswith(".qbin"):
        # Decompile
        qbin_b64 = encode_file(in_path)
        resp = requests.post(
            API_BASE + "/decompile",
            json={"qbin_b64": qbin_b64}
        )
        if resp.status_code != 200:
            print("Error:", resp.status_code, resp.text)
            sys.exit(1)
        data = resp.json()
        out_path = in_path + ".out.qasm"
        decode_to_file(data["qasm_b64"], out_path)
        print("Decompiled OK ->", out_path)

    else:
        print("Input must end with .qasm or .qbin")
        sys.exit(1)

if __name__ == "__main__":
    main()

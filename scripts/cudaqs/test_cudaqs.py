import sys
import base64
import requests

API_BASE = "https://cryspprod3.quantag-it.com:444/api19"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_cudaq.py <source.py> [kernel_name]")
        sys.exit(1)

    source_file = sys.argv[1]
    kernel_name = sys.argv[2] if len(sys.argv) > 2 else "bell"

    with open(source_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    src_b64 = base64.b64encode(source_code.encode("utf-8")).decode("utf-8")

    payload = {
        "source_b64": src_b64,
        "lang": "python",
        "kernel": kernel_name,
        "target": "qpp-cpu",   # could also be "qpp-cpu", "density-matrix-cpu", etc.
        "shots": 1000,
        "state": False
    }

    url = f"{API_BASE}/cudaq/run"
    print(f"POST {url} {payload}")
    resp = requests.post(url, json=payload)  # verify=False if using self-signed cert

    if resp.ok:
        print("Response:", resp.json())
    else:
        print("Error:", resp.status_code, resp.text)


if __name__ == "__main__":
    main()

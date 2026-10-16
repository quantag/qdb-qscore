import requests
import json
import sys
from pathlib import Path
import base64

BASE_URL = "https://cryspprod3.quantag-it.com:444/api20"

def solve_with_csv_file(csv_path: str):
    # Read and base64 encode file content
    csv_bytes = Path(csv_path).read_bytes()
    csv_b64 = base64.b64encode(csv_bytes).decode("utf-8")

    payload = {
        "csv": csv_b64,   # same field name, now base64 encoded
        "backend": "dwave"
    }
    print("Payload keys:", list(payload.keys()))
    # Call API
    resp = requests.post(f"{BASE_URL}/solve", json=payload) 
    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        print("Request failed:", e)
        print("Response text:", resp.text)
        sys.exit(1)

    # Pretty print response
    print("Status:", resp.status_code)
    print("Response:", json.dumps(resp.json(), indent=2))


def test_health():
    resp = requests.get(f"{BASE_URL}/health", verify=False)
    print("Health check:", resp.json())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_qaoa.py <portfolio.csv> [health]")
        sys.exit(1)

    if sys.argv[1] == "health":
        test_health()
    else:
        solve_with_csv_file(sys.argv[1])


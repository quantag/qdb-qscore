import requests
import sys

BASE_URL = "https://quantum.quantag-it.com/api5"

def delete_all_apikeys(user_id):
    url = f"{BASE_URL}/apikeys/delete_all"
    payload = {"user_id": user_id}
    resp = requests.post(url, json=payload)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Raw response:", resp.text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_delete_all_apikeys.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    delete_all_apikeys(user_id)

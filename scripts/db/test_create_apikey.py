import requests
import sys

from config import BASE_URL

def create_apikey(user_id):
    url = f"{BASE_URL}/apikeys"
    payload = {"user_id": user_id}
    resp = requests.post(url, json=payload)
    print("Status:", resp.status_code)
    print("Response:", resp.json())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_create_apikey.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    create_apikey(user_id)

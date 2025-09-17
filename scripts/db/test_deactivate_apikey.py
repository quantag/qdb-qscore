import requests
import sys

from config import BASE_URL

def deactivate_apikey(key_uid):
    url = f"{BASE_URL}/apikeys/{key_uid}/deactivate"
    resp = requests.post(url)
    print("Status:", resp.status_code)
    print("Response:", resp.json())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_deactivate_apikey.py <key_uid>")
        sys.exit(1)

    key_uid = sys.argv[1]
    deactivate_apikey(key_uid)

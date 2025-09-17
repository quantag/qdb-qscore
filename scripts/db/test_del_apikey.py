import requests
import sys

from config import BASE_URL

def delete_apikey(key_uid):
    url = f"{BASE_URL}/apikeys/{key_uid}"
    resp = requests.delete(url)
    print("Status:", resp.status_code)
    print("Response:", resp.json())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_delete_apikey.py <key_uid>")
        sys.exit(1)

    key_uid = sys.argv[1]
    delete_apikey(key_uid)

import requests
import sys

from config import BASE_URL

def list_apikeys(user_id):
    url = f"{BASE_URL}/apikeys/{user_id}"
    resp = requests.get(url)
    print("Status:", resp.status_code)
    print("Response:", resp.json())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_list_apikeys.py <user_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    list_apikeys(user_id)

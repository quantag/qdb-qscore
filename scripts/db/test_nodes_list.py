import requests
import sys

from config import BASE_URL

def list_nodes():
    url = f"{BASE_URL}/nodes"
    resp = requests.get(url)
    print("Status:", resp.status_code)
    try:
        print("Response:", resp.json())
    except Exception:
        print("Response:", resp.text)

if __name__ == "__main__":
    list_nodes()

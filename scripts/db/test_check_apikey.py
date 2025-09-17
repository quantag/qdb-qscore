import requests
import sys

BASE_URL = "https://quantum.quantag-it.com/api5"

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_check_apikey.py <api_key>")
        sys.exit(1)

    server_url = BASE_URL
    api_key = sys.argv[1]

    url = f"{server_url}/check_apikey"
    payload = {"apikey": api_key}

    try:
        response = requests.post(url, json=payload, timeout=10)
        print("Status code:", response.status_code)
        print("Response:", response.json())
    except Exception as e:
        print("Error calling API:", str(e))

if __name__ == "__main__":
    main()

import requests
import json

URL = "https://cloud.quantag-it.com/start/prepare"

payload = {
    "email": "test.user@gmail.com"
}

headers = {
    "Content-Type": "application/json"
}

print(f"Sending request to {URL} ...")
resp = requests.post(URL, data=json.dumps(payload), headers=headers, verify=True)

print("Status:", resp.status_code)
try:
    print("Response JSON:", resp.json())
except Exception:
    print("Raw response:", resp.text)

import requests
import json
import sys

URL = "https://cloud.quantag-it.com/start/get"

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <email>")
    sys.exit(1)

email = sys.argv[1]

payload = {"email": email}
headers = {"Content-Type": "application/json"}

print(f"Sending request to {URL} with email={email} ...")
resp = requests.post(URL, data=json.dumps(payload), headers=headers, verify=True)

print("Status:", resp.status_code)
try:
    print("Response JSON:", json.dumps(resp.json(), indent=2))
except Exception:
    print("Raw response:", resp.text)

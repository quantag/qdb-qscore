import requests
import json
import sys

URL = "https://cloud.quantag-it.com/start/del"

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <email> [workplace_name]")
    sys.exit(1)

email = sys.argv[1]
name = sys.argv[2] if len(sys.argv) > 2 else None

payload = {"email": email}
if name:
    payload["name"] = name

headers = {"Content-Type": "application/json"}

print(f"Sending request to {URL} with email={email}, name={name or 'ALL (delete user root)'} ...")
resp = requests.post(URL, data=json.dumps(payload), headers=headers, verify=True)

print("Status:", resp.status_code)
try:
    print("Response JSON:", resp.json())
except Exception:
    print("Raw response:", resp.text)

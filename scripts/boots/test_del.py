import requests
import json
import sys

URL = "https://cloud.quantag-it.com/start/del"

# Take email from command line argument, or use default
if len(sys.argv) > 1:
    email = sys.argv[1]
else:
    email = "test.user@gmail.com"

payload = {"email": email}
headers = {"Content-Type": "application/json"}

print(f"Sending request to {URL} with email={email} ...")
resp = requests.post(URL, data=json.dumps(payload), headers=headers, verify=True)

print("Status:", resp.status_code)
try:
    print("Response JSON:", resp.json())
except Exception:
    print("Raw response:", resp.text)

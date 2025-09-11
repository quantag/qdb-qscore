import requests
import base64
import json
from pathlib import Path

BASE = "https://cryspprod3.quantag-it.com:444/api2"


def test_submitFiles():
    session_id = "sess123"
    # prepare a fake file
    data_bytes = b"print('hello world')\n"
    encoded = base64.b64encode(data_bytes).decode("ascii")
    payload = {
        "sessionId": session_id,
        "files": [
            {"path": "src/test.py", "source": encoded}
        ]
    }
    r = requests.post(f"{BASE}/public/submitFiles", json=payload, verify=False)
    print("submitFiles:", r.status_code, r.text)

def test_submitFile():
    data_bytes = b"console.log('Hello');"
    encoded = base64.b64encode(data_bytes).decode("ascii")
    payload = {
        "sessionId": "sess123",
        "path": "hello.js",
        "source": encoded
    }
    r = requests.post(f"{BASE}/public/submitFile", json=payload, verify=False)
    print("submitFile:", r.status_code, r.text)

def test_prepareData():
    payload = {
        "userId": "user1",
        "sessionId": "sess_copy"
    }
    r = requests.post(f"{BASE}/public/prepareData", json=payload, verify=False)
    print("prepareData:", r.status_code, r.text)

def test_getImage():
    payload = {"sessionId": "sess123"}
    r = requests.post(f"{BASE}/public/getImage", json=payload, verify=False)
    print("getImage:", r.status_code)
    try:
        resp = r.json()
        if resp.get("code") == 0:
            data = base64.b64decode(resp["data"])
            Path("downloaded.png").write_bytes(data)
            print("Image saved to downloaded.png")
    except Exception as e:
        print("Error decoding getImage response:", e)

def test_getFile():
    payload = {"file": "hello.js"}
    r = requests.post(f"{BASE}/public/getFile", json=payload, verify=False)
    print("getFile:", r.status_code)
    try:
        resp = r.json()
        if resp.get("code") == 0:
            data = base64.b64decode(resp["data"])
            Path("downloaded_file.js").write_bytes(data)
            print("File saved to downloaded_file.js")
    except Exception as e:
        print("Error decoding getFile response:", e)

if __name__ == "__main__":
    test_submitFiles()
    test_submitFile()
    test_prepareData()
    test_getImage()
    test_getFile()

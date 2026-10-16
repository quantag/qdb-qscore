import sys
import time
import requests

from config import BASE_URL

def main():
    if len(sys.argv) < 3:
        print(f"Usage: python {sys.argv[0]} <API_KEY> <JOB_UID> [--wait]")
        sys.exit(1)

    api_key = sys.argv[1]
    job_uid = sys.argv[2]
    wait_mode = "--wait" in sys.argv

    headers = {"X-API-Key": api_key}
    url = f"{BASE_URL}/qvm/job/{job_uid}"

    if wait_mode:
        print(f"Polling {url} until DONE...")
        while True:
            resp = requests.get(url, headers=headers)
            print("Status code:", resp.status_code)
            try:
                data = resp.json()
            except Exception:
                print("Non-JSON:", resp.text)
                break

            print("Response:", data)
            if data.get("status") in ("DONE", "ERROR"):
                break
            time.sleep(2)
    else:
        resp = requests.get(url, headers=headers)
        print("Status code:", resp.status_code)
        try:
            print("Response:", resp.json())
        except Exception:
            print("Non-JSON response:", resp.text)

if __name__ == "__main__":
    main()

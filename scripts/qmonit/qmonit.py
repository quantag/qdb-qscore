import json
import requests
import sys
import os

DEFAULT_CONFIG = "services.json"

def check_services(config_file: str):
    try:
        with open(config_file, "r") as f:
            services = json.load(f)
    except Exception as e:
        print(f"Error loading config file {config_file}: {e}")
        sys.exit(1)

    results = []
    any_fail = False

    for service in services:
        name = service.get("name")
        base_url = service.get("url")
        health_url = f"{base_url}/health"

        print(f"Checking {name} at {health_url} ...")

        try:
            resp = requests.get(health_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and data.get("status") == 0:
                    results.append((name, "OK"))
                else:
                    results.append((name, f"FAIL (status={data.get('status')})"))
                    any_fail = True
            else:
                results.append((name, f"FAIL (HTTP {resp.status_code})"))
                any_fail = True
        except Exception as e:
            results.append((name, f"ERROR ({e})"))
            any_fail = True

    print("\nHealth Check Results:")
    for name, status in results:
        print(f"- {name}: {status}")

    if any_fail:
        sys.exit(1)

if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG
    if not os.path.exists(config_file):
        print(f"Config file {config_file} not found.")
        sys.exit(1)
    check_services(config_file)


# app_config.py

import os
import json

MODEL_LIMITS_PATH = "model_limits.json"

if os.path.exists(MODEL_LIMITS_PATH):
    with open(MODEL_LIMITS_PATH, "r") as f:
        model_limits = json.load(f)
else:
    model_limits = {
        "gpt-3.5-turbo": 16385,
        "gpt-4": 8192,
        "gpt-4-0613": 8192,
        "gpt-4-1106-preview": 128000,
        "gpt-4o": 128000
    }

# === Load API key from config.json ===
CONFIG_PATH = "config.json"
if not os.path.exists(CONFIG_PATH):
    print("ERROR: config.json not found. Please create it before starting the server.")
    sys.exit(1)

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)
    api_key = config.get("openai_api_key")
    model_name = config.get("openai_model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.2)
    max_tokens = config.get("max_tokens", 2000)
    system_prompt = config.get("system_prompt", "You are a helpful assistant that optimizes OpenQASM.")


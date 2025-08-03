# app_config.py

import os
import json

MODEL_LIMITS_PATH = "model_limits.json"

if os.path.exists(MODEL_LIMITS_PATH):
    with open(MODEL_LIMITS_PATH, "r") as f:
        MODEL_LIMITS = json.load(f)
else:
    MODEL_LIMITS = {
        "gpt-3.5-turbo": 16385,
        "gpt-4": 8192,
        "gpt-4-0613": 8192,
        "gpt-4-1106-preview": 128000,
        "gpt-4o": 128000
    }


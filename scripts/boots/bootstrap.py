#!/usr/bin/env python3
import os, hashlib, shutil
from pathlib import Path
from flask import Flask, request, jsonify
import logging
from datetime import datetime
from flask_cors import CORS

SAMPLE_DIR = "/var/codeserver/sample"
BASE_WORK_DIR = os.environ.get("BASE_WORK_DIR", "/var/codeserver/users")
DEFAULT_SUBDIR = "workplace"

# logging setup
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_file = os.path.join(log_dir, f"bootstrap-{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(log_file, mode="w"), logging.StreamHandler()],
)
log = logging.getLogger("bootstrap")

app = Flask(__name__)
CORS(app)

def email_to_user_id(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:32]


def safe_join(base: Path, *parts: str) -> Path:
    p = (base.joinpath(*parts)).resolve()
    if not str(p).startswith(str(base.resolve())):
        raise ValueError("path traversal detected")
    return p

@app.route("/prepare", methods=["POST"])
def prepare():
    data = request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"status": 2, "error": "email is required"}), 400

    # Use provided name or default
    folder_name = data.get("name", DEFAULT_SUBDIR)

    try:
        user_id = email_to_user_id(email)
        user_root = safe_join(Path(BASE_WORK_DIR), user_id)
        workspace = user_root / folder_name

        if workspace.exists():
            log.info("Workspace for %s already exists: %s", email, workspace)
            return jsonify({
                "status": 1,
                "email": email,
                "user_id": user_id,
                "path": str(workspace.resolve())
            })

        # Create folder
        workspace.mkdir(parents=True, exist_ok=False)

        # Copy sample if available
        if Path(SAMPLE_DIR).exists():
            log.info("Copying sample content to %s", workspace)
            try:
                shutil.copytree(SAMPLE_DIR, workspace, dirs_exist_ok=True)
            except Exception as e:
                log.error("Failed to copy sample content: %s", e)

        log.info("Prepared workspace for %s at %s", email, workspace)

        return jsonify({
            "status": 0,
            "email": email,
            "user_id": user_id,
            "path": str(workspace.resolve())
        })
    except Exception as e:
        log.error("Unexpected error in /prepare: %s", e, exc_info=True)
        return jsonify({"status": 2, "error": "internal server error"}), 500

@app.route("/del", methods=["POST"])
def delete_workspace():
    data = request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"status": 2, "error": "email is required"}), 400

    try:
        user_id = email_to_user_id(email)
        user_root = safe_join(Path(BASE_WORK_DIR), user_id)
        workspace = user_root / DEFAULT_SUBDIR

        if not workspace.exists():
            log.info("Workspace for %s not found at %s", email, workspace)
            return jsonify({"status": 1, "email": email, "user_id": user_id})

        try:
            shutil.rmtree(user_root)  # remove whole user root, not just workplace
            log.info("Deleted workspace for %s at %s", email, user_root)
            return jsonify({"status": 0, "email": email, "user_id": user_id})
        except Exception as e:
            log.error("Failed to delete workspace %s: %s", user_root, e, exc_info=True)
            return jsonify({"status": 2, "email": email, "user_id": user_id}), 500

    except Exception as e:
        log.error("Unexpected error in /del: %s", e, exc_info=True)
        return jsonify({"status": 2, "error": "internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("BOOTSTRAP_PORT", "5001"))
    app.run(host="127.0.0.1", port=port)

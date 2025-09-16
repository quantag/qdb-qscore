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

@app.route("/get", methods=["POST"])
def get_workspaces():
    data = request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"status": 2, "error": "email is required"}), 400

    try:
        user_id = email_to_user_id(email)
        user_root = safe_join(Path(BASE_WORK_DIR), user_id)

        if not user_root.exists():
            log.info("User root not found for %s: %s", email, user_root)
            return jsonify({
                "status": 1,
                "email": email,
                "user_id": user_id,
                "workspaces": []
            })

        workspaces = []
        for entry in user_root.iterdir():
            if entry.is_dir():
                workspaces.append(str(entry.resolve()))

        log.info("Listing workspaces for %s: %s", email, workspaces)

        return jsonify({
            "status": 0,
            "email": email,
            "user_id": user_id,
            "workspaces": workspaces
        })

    except Exception as e:
        log.error("Unexpected error in /get: %s", e, exc_info=True)
        return jsonify({"status": 2, "error": "internal server error"}), 500

@app.route("/del", methods=["POST"])
def delete_workspace():
    data = request.get_json(force=True)
    email = data.get("email")
    if not email:
        return jsonify({"status": 2, "error": "email is required"}), 400

    # Optional "name" field
    folder_name = data.get("name")

    try:
        user_id = email_to_user_id(email)
        user_root = safe_join(Path(BASE_WORK_DIR), user_id)

        # Decide path to delete
        target_path = user_root / folder_name if folder_name else user_root

        if not target_path.exists():
            log.info("Target for deletion not found: %s", target_path)
            return jsonify({
                "status": 1,
                "email": email,
                "user_id": user_id,
                "path": str(target_path)
            })

        try:
            shutil.rmtree(target_path)
            log.info("Deleted %s for %s at %s", 
                     "workspace" if folder_name else "user root", 
                     email, target_path)
            return jsonify({
                "status": 0,
                "email": email,
                "user_id": user_id,
                "path": str(target_path)
            })
        except Exception as e:
            log.error("Failed to delete %s: %s", target_path, e, exc_info=True)
            return jsonify({
                "status": 2,
                "email": email,
                "user_id": user_id,
                "path": str(target_path)
            }), 500

    except Exception as e:
        log.error("Unexpected error in /del: %s", e, exc_info=True)
        return jsonify({"status": 2, "error": "internal server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("BOOTSTRAP_PORT", "5001"))
    app.run(host="127.0.0.1", port=port)

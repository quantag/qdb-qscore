# app.py
# Flask service replicating:
#   POST /public/submitFiles
#   POST /public/submitFile
#   POST /public/prepareData
#   POST /public/getImage
#   POST /public/getFile

import base64
import json
import logging
import os
from pathlib import Path
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest
from flask_cors import CORS
from datetime import datetime

# -----------------------------------------------------------------------------
# Configuration (equivalent to Application.mainFolder and Application.imageFolder)
# -----------------------------------------------------------------------------
MAIN_FOLDER = os.environ.get("MAIN_FOLDER", "./data/")
IMAGE_FOLDER = os.environ.get("IMAGE_FOLDER", "./images/")

# Ensure folders exist
Path(MAIN_FOLDER).mkdir(parents=True, exist_ok=True)
Path(IMAGE_FOLDER).mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
log_dir = "./logs"
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
log_file = os.path.join(log_dir, f"server-{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("controller")
log.info("Server starting, logging to %s", log_file)

# -----------------------------------------------------------------------------
# Load properties file (application.properties)
# -----------------------------------------------------------------------------
def load_properties(filename="dap-files.properties"):
    props = {}
    if not os.path.exists(filename):
        return props
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                props[key.strip()] = value.strip()
    return props

properties = load_properties()

MAIN_FOLDER = properties.get("mainFolder", "./data/")
IMAGE_FOLDER = properties.get("imageFolder", "./images/")

Path(MAIN_FOLDER).mkdir(parents=True, exist_ok=True)
Path(IMAGE_FOLDER).mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Helpers (equivalent to Utils.* and request helpers)
# -----------------------------------------------------------------------------
def safe_join(base: Path, *parts: str) -> Path:
    """
    Join and normalize parts under base, preventing path traversal.
    """
    candidate = base.joinpath(*parts).resolve()
    base_resolved = base.resolve()
    if not str(candidate).startswith(str(base_resolved)):
        raise ValueError("Path traversal detected")
    return candidate

def clear_folder(folder: Path) -> None:
    if not folder.exists():
        return
    for p in folder.rglob("*"):
        try:
            if p.is_file() or p.is_symlink():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                # remove dirs bottom-up
                try:
                    p.rmdir()
                except OSError:
                    pass
        except Exception as e:
            log.warning("Failed to remove %s: %s", p, e)
    # finally try removing empty subdirs
    for p in sorted(folder.rglob("*"), reverse=True):
        if p.is_dir():
            try:
                p.rmdir()
            except OSError:
                pass

def save_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

def load_file(path: Path) -> bytes:
    with open(path, "rb") as f:
        return f.read()

def get_relative_path(input_path: str) -> str:
    """
    Emulate requestData.getRelativePath(...) + backslash -> slash normalization.
    Removes drive letters and leading slashes, collapses .., and returns a posix-like path.
    """
    # Drop Windows drive (e.g., C:\) and leading slashes
    p = Path(input_path)
    parts = []
    for part in p.parts:
        if part in ("/", "\\"):
            continue
        # Skip drive letters like "C:\"
        if len(part) == 2 and part[1] == ":":
            continue
        if part in (".",):
            continue
        if part in ("..",):
            # collapse traversal
            if parts:
                parts.pop()
            continue
        parts.append(part)
    # Join with POSIX separator
    return "/".join(parts)

def b64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)

def bytes_to_b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")

# -----------------------------------------------------------------------------
# Flask app
# -----------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": 0}), 200

@app.post("/public/submitFiles")
def submit_files():
    try:
        req = request.get_json(force=True, silent=False)
        session_id = req.get("sessionId")
        files = req.get("files", [])
        opts = req.get("opts", {})

        if not session_id or not isinstance(files, list):
            raise BadRequest("Missing sessionId or files")

        log.info("VSCode Mode: %s", opts.get("mode"))
        log.info("QUANTAG_BASE_URL: %s", opts.get("baseUrl"))

        session_base = safe_join(Path(MAIN_FOLDER), session_id)
        session_base.mkdir(parents=True, exist_ok=True)
        # Clear session folder before writing, as in original
        clear_folder(session_base)

        stored_paths = []
        for f in files:
            raw_path = f.get("path")
            b64src = f.get("source")
            if not raw_path or not b64src:
                raise BadRequest("Missing file.path or file.source")

            rel = get_relative_path(raw_path).replace("\\", "/")
            target = safe_join(session_base, rel)
            save_file(target, b64_to_bytes(b64src))
            # log folder and file
            log.info("Uploaded file: %s", target)
            log.info("Parent folder: %s", target.parent)

            # Return relative paths as in the Java code
            stored_paths.append(str(Path(session_id) / rel).replace("\\", "/"))

        session_folder_abs = str(session_base.resolve())
        return jsonify({"code": 0, "count": len(stored_paths), "sessionFolder": session_folder_abs}), 200

    except BadRequest as e:
        log.warning("submitFiles BAD_REQUEST: %s", e)
        return jsonify({"code": 1, "message": "BAD_REQUEST"}), 400
    except ValueError as e:
        log.warning("submitFiles path traversal blocked: %s", e)
        return jsonify({"code": 1, "message": "BAD_REQUEST"}), 400
    except Exception as e:
        log.exception("submitFiles error")
        # The Java version fell back to 400 on bad input; keeping it simple
        return jsonify({"code": 1, "message": "ERROR"}), 400

@app.post("/public/submitFile")
def submit_file():
    """
    Request JSON:
    {
      "sessionId": "ignored by original single-file endpoint",
      "path": "any/thing/name.ext",
      "source": "<base64>"
    }

    Behavior:
      - Uses only the base file name (drops directories).
      - Writes into MAIN_FOLDER root (no subfolder).
      - Returns 200 on success, 409 on write error, 400 on missing fields.
      - Response body always looks like success payload in the original controller.

    Response JSON (mirrors Java's "SubmitFileResponse(OK, 1)"):
      {"code": 0, "count": 1}
    """
    try:
        req = request.get_json(force=True, silent=False)
        raw_path = req.get("path")
        b64src = req.get("source")

        if not raw_path or not b64src:
            return jsonify({"code": 1, "message": "BAD_REQUEST"}), 400

        # Emulate FilenameUtils.getName(...) behavior: strip directories
        file_name = Path(raw_path).name
        target = safe_join(Path(MAIN_FOLDER), file_name)

        try:
            save_file(target, b64_to_bytes(b64src))
            # Note: original code sets 200 on success, 409 on write error
            return jsonify({"code": 0, "count": 1}), 200
        except Exception:
            log.exception("submitFile write error")
            return jsonify({"code": 0, "count": 1}), 409

    except BadRequest:
        return jsonify({"code": 1, "message": "BAD_REQUEST"}), 400

@app.post("/public/prepareData")
def prepare_data():
    """
    Request JSON:
    {
      "userId": "user123",
      "sessionId": "sess456"
    }

    Behavior:
      - Mirrors MAIN_FOLDER/userId into MAIN_FOLDER/sessionId.
      - Overwrites existing files.

    Response on success:
      {"code": 0}

    On error:
      500 with {"code": 1, "message": "Cannot prepare data."}
    """
    try:
        req = request.get_json(force=True, silent=False)
        user_id = req.get("userId")
        session_id = req.get("sessionId")
        if not user_id or not session_id:
            return jsonify({"code": 1, "message": "BAD_REQUEST"}), 400

        main_path = Path(MAIN_FOLDER).resolve()
        source_path = safe_join(main_path, user_id)
        target_path = safe_join(main_path, session_id)

        # Walk source and copy to target (overwrite)
        if not source_path.exists():
            # If source does not exist, mirror nothing but still return success
            target_path.mkdir(parents=True, exist_ok=True)
            return jsonify({"code": 0}), 200

        for p in source_path.rglob("*"):
            rel = p.relative_to(source_path)
            dst = safe_join(target_path, str(rel))
            if p.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                # Copy file
                with open(p, "rb") as rf, open(dst, "wb") as wf:
                    wf.write(rf.read())

        return jsonify({"code": 0}), 200

    except Exception as e:
        log.exception("prepareData error")
        # Original throws RuntimeException("Cannot prepare data.")
        return jsonify({"code": 1, "message": "Cannot prepare data."}), 500

@app.post("/public/getImage")
def get_image():
    """
    Request JSON:
    {
      "sessionId": "sess456"
    }

    Behavior:
      - Loads IMAGE_FOLDER/<sessionId>.png
      - Returns base64 data

    Response on success:
      {"code": 0, "data": "<base64>"}

    On error:
      {"code": 1}
    """
    try:
        req = request.get_json(force=True, silent=False)
        session_id = req.get("sessionId")
        if not session_id:
            return jsonify({"code": 1}), 400

        path = safe_join(Path(IMAGE_FOLDER), f"{session_id}.png")
        data = load_file(path)
        return jsonify({"code": 0, "data": bytes_to_b64(data)}), 200
    except Exception:
        log.warning("getImage failed", exc_info=True)
        return jsonify({"code": 1}), 200

@app.post("/public/getFile")
def get_file():
    """
    Request JSON:
    {
      "file": "name.ext"
    }

    Behavior:
      - Loads IMAGE_FOLDER/<file>
      - Returns base64 data

    Response on success:
      {"code": 0, "data": "<base64>"}

    On error:
      {"code": 1}
    """
    try:
        req = request.get_json(force=True, silent=False)
        file_name = req.get("file")
        if not file_name:
            return jsonify({"code": 1}), 400

        # Only allow plain file name here (avoid nested paths)
        base_name = Path(file_name).name
        path = safe_join(Path(IMAGE_FOLDER), base_name)
        data = load_file(path)
        return jsonify({"code": 0, "data": bytes_to_b64(data)}), 200
    except Exception:
        log.warning("getFile failed", exc_info=True)
        return jsonify({"code": 1}), 200

properties = load_properties()

MAIN_FOLDER = properties.get("mainFolder", "./data/")
IMAGE_FOLDER = properties.get("imageFolder", "./images/")

Path(MAIN_FOLDER).mkdir(parents=True, exist_ok=True)
Path(IMAGE_FOLDER).mkdir(parents=True, exist_ok=True)
# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example: FLASK_RUN_HOST=0.0.0.0 FLASK_RUN_PORT=8080 python app.py
    app.run(host="0.0.0.0", port=8150)
    CORS(app)

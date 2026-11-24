# app.py
# Flask service replicating:
#   POST /public/submitFiles
#   POST /public/submitFile
#   POST /public/prepareData
#   POST /public/getImage
#   POST /public/getFile

import base64
import binascii
import json
import logging
import os
import re
import shutil
import threading
import time
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
CORS(app)

# -----------------------------------------------------------------------------
# Upload limits and cleanup of old upload sessions (dap-files.properties)
# -----------------------------------------------------------------------------
MAX_FILES = int(properties.get("maxFiles", "200"))
MAX_TOTAL_BYTES = int(properties.get("maxTotalBytes", str(10 * 1024 * 1024)))
SESSION_TTL_SECONDS = float(properties.get("sessionTtlHours", "24")) * 3600
CLEANUP_INTERVAL_SECONDS = 600
# Only folders created by submitFiles carry this marker; user folders (prepareData)
# and the image folder are never removed by the cleanup.
SESSION_MARKER = ".qs-upload-session"
SESSION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")

# Base64 makes the body about 4/3 of the decoded size, plus JSON and paths
app.config["MAX_CONTENT_LENGTH"] = MAX_TOTAL_BYTES * 4 // 3 + 1024 * 1024

_last_cleanup = 0.0
_cleanup_lock = threading.Lock()


def upload_error(status, message, path=None):
    body = {"code": 1, "message": message}
    if path is not None:
        body["path"] = path
    log.warning("submitFiles rejected (%d): %s%s", status, message, f" [{path}]" if path else "")
    return jsonify(body), status


def format_mb(n):
    return f"{n / (1024 * 1024):.1f} MB"


def cleanup_old_sessions(keep=None):
    """Remove upload session folders not used for SESSION_TTL_SECONDS (at most every 10 min)."""
    global _last_cleanup
    now = time.time()
    with _cleanup_lock:
        if now - _last_cleanup < CLEANUP_INTERVAL_SECONDS:
            return 0
        _last_cleanup = now
    removed = 0
    main = Path(MAIN_FOLDER)
    if not main.is_dir():
        return 0
    for folder in main.iterdir():
        try:
            marker = folder / SESSION_MARKER
            if not folder.is_dir() or folder.is_symlink() or not marker.is_file():
                continue
            if keep is not None and folder.resolve() == keep.resolve():
                continue
            if now - marker.stat().st_mtime > SESSION_TTL_SECONDS:
                shutil.rmtree(folder)
                removed += 1
        except Exception as e:
            log.warning("Cleanup of %s failed: %s", folder, e)
    if removed:
        log.info("Removed %d upload session folder(s) older than %.0f h", removed, SESSION_TTL_SECONDS / 3600)
    return removed


@app.errorhandler(413)
def request_too_large(_e):
    return upload_error(413, f"Request too large: the files exceed the limit of {format_mb(MAX_TOTAL_BYTES)}")

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": 0}), 200

@app.post("/public/submitFiles")
def submit_files():
    """
    Request JSON: {"sessionId": "...", "files": [{"path": "rel/path.py", "source": "<base64>"}], "root": ..., "opts": {...}}
    All files are checked before anything is written. An empty file ("source": "") is valid.
    Limits: MAX_FILES files and MAX_TOTAL_BYTES decoded bytes per request.
    Errors: {"code": 1, "message": "...", "path": "<file, if one file is the cause>"} with 400 or 413.
    """
    try:
        req = request.get_json(force=True, silent=False)
    except BadRequest:
        return upload_error(400, "Request body is not valid JSON")
    if not isinstance(req, dict):
        return upload_error(400, "Request body must be a JSON object")

    session_id = req.get("sessionId")
    files = req.get("files", [])
    opts = req.get("opts") or {}
    if not isinstance(session_id, str) or not session_id.strip():
        return upload_error(400, "Missing sessionId")
    if not isinstance(files, list):
        return upload_error(400, "'files' must be a list")
    if len(files) > MAX_FILES:
        return upload_error(413, f"Too many files: {len(files)} (limit {MAX_FILES})")

    log.info("VSCode Mode: %s", opts.get("mode") if isinstance(opts, dict) else None)
    log.info("QUANTAG_BASE_URL: %s", opts.get("baseUrl") if isinstance(opts, dict) else None)

    # The session folder is cleared below, so it must be a plain child folder of
    # MAIN_FOLDER: never MAIN_FOLDER itself ("", ".") or the image folder.
    if not SESSION_ID_RE.fullmatch(session_id) or session_id in (".", ".."):
        return upload_error(400, "Invalid sessionId")
    try:
        session_base = safe_join(Path(MAIN_FOLDER), session_id)
    except ValueError:
        return upload_error(400, "Invalid sessionId")
    if session_base.parent != Path(MAIN_FOLDER).resolve() or session_base == Path(IMAGE_FOLDER).resolve():
        return upload_error(400, "Invalid sessionId")

    # 1. Check every file before writing anything
    prepared = []
    total = 0
    for index, f in enumerate(files):
        if not isinstance(f, dict):
            return upload_error(400, f"File entry {index} must be an object")
        raw_path = f.get("path")
        b64src = f.get("source")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return upload_error(400, f"File entry {index} has no path")
        if b64src is None:
            return upload_error(400, "File has no 'source' field", raw_path)
        if not isinstance(b64src, str):
            return upload_error(400, "'source' must be a base64 string", raw_path)
        try:
            data = base64.b64decode(b64src, validate=True)
        except (binascii.Error, ValueError):
            return upload_error(400, "'source' is not valid base64", raw_path)
        rel = get_relative_path(raw_path).replace("\\", "/")
        if not rel:
            return upload_error(400, "Invalid file path", raw_path)
        try:
            target = safe_join(session_base, rel)
        except ValueError:
            return upload_error(400, "File path points outside the session folder", raw_path)
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            return upload_error(413, f"Files too large: more than {format_mb(MAX_TOTAL_BYTES)} in total "
                                     f"(limit {format_mb(MAX_TOTAL_BYTES)})", raw_path)
        prepared.append((rel, target, data))

    # 2. Write the session folder
    try:
        cleanup_old_sessions(keep=session_base)
    except Exception:
        log.exception("Cleanup of old sessions failed")

    try:
        session_base.mkdir(parents=True, exist_ok=True)
        # Clear session folder before writing, as in original
        clear_folder(session_base)
        (session_base / SESSION_MARKER).write_text(datetime.now().isoformat())

        stored_paths = []
        for rel, target, data in prepared:
            save_file(target, data)
            log.info("Uploaded file: %s (%d bytes)", target, len(data))
            stored_paths.append(str(Path(session_id) / rel).replace("\\", "/"))
    except Exception as e:
        log.exception("submitFiles write error")
        return upload_error(500, f"Cannot store the files: {e}")

    session_folder_abs = str(session_base.resolve())
    log.info("Session %s: %d file(s), %d bytes", session_id, len(stored_paths), total)
    return jsonify({"code": 0, "count": len(stored_paths), "sessionFolder": session_folder_abs}), 200

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
        log.info(f"getImage incoming JSON: {req}")
        session_id = req.get("sessionId")
        if not session_id:
            log.exception(f"get_image failed. no session_id")
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

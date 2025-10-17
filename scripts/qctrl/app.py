"""
Q-CTRL Fire Opal Flask microservice (with file logging + QASM archiving)

- Logs go to LOG_DIR (default: /logs), rotating app.log and error.log
- Each incoming OpenQASM is saved as LOG_DIR/qasm_YYYYmmdd-HHMMSS_<id>.qasm
"""

import base64
import json
import logging
import os
import time
import traceback
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict

from flask import Flask, request, jsonify

# Fire Opal / Q-CTRL and IBM Runtime
import fireopal as fo

# ----------------- Logging setup -----------------
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))  # default to /logs as requested
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _build_logger() -> logging.Logger:
    logger = logging.getLogger("qctrl_service")
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )

    # Rotating file for all logs
    app_handler = RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(fmt)
    logger.addHandler(app_handler)

    # Rotating file for errors
    err_handler = RotatingFileHandler(
        LOG_DIR / "error.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    err_handler.setLevel(logging.WARNING)
    err_handler.setFormatter(fmt)
    logger.addHandler(err_handler)

    # Also log to stderr (useful under systemd/gunicorn)
    stderr = logging.StreamHandler()
    stderr.setLevel(logging.INFO)
    stderr.setFormatter(fmt)
    logger.addHandler(stderr)

    return logger

logger = _build_logger()

app = Flask(__name__)


class BadRequest(Exception):
    pass


def _decode_qasm_from_base64(src_b64: str) -> str:
    try:
        raw = base64.b64decode(src_b64, validate=True)
        return raw.decode("utf-8")
    except Exception as exc:
        raise BadRequest(f"Invalid base64 in 'src': {exc}")


def _require_config(cfg: Dict[str, Any], key: str) -> Any:
    if key not in cfg or not cfg[key]:
        raise BadRequest(f"Missing required config field: {key}")
    return cfg[key]


def _auth_qctrl_and_ibm(cfg: Dict[str, Any]):
    # Q-CTRL auth
    api_key = _require_config(cfg, "qctrl_api_key")
    fo.authenticate_qctrl_account(api_key=api_key)

    # IBM credentials via Fire Opal helper
    token = _require_config(cfg, "ibm_token")
    instance = cfg.get("ibm_instance", "one")
    creds = fo.credentials.make_credentials_for_ibm_cloud(token=token, instance=instance)
    return creds


def _select_backend(creds: Any, requested_backend: str | None) -> str:
    if requested_backend:
        return requested_backend
    supported = fo.show_supported_devices(credentials=creds).get("supported_devices", [])
    if not supported:
        raise RuntimeError("No supported devices returned by Fire Opal for provided IBM credentials.")
    return supported[0]


def _execute_fire_opal(qasm: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    creds = _auth_qctrl_and_ibm(cfg)
    backend_name = _select_backend(creds, cfg.get("backend_name"))
    shot_count = int(cfg.get("shot_count", 1024))

    job = fo.execute(
        circuits=[qasm],
        shot_count=shot_count,
        credentials=creds,
        backend_name=backend_name,
    )

    job_id = None
    for attr in ("id", "job_id", "jobId", "uid"):
        if hasattr(job, attr):
            try:
                job_id = getattr(job, attr)
                break
            except Exception:
                pass

    wait = bool(cfg.get("wait", True))
    out: Dict[str, Any] = {
        "job_id": job_id,
        "backend_name": backend_name,
        "shot_count": shot_count,
        "waited": wait,
    }

    if not wait:
        out["status"] = 0
        out["message"] = "submitted"
        return out

    result = job.result()
    out["raw_result"] = result

    counts = {}
    if isinstance(result, dict):
        results_list = result.get("results")
        if isinstance(results_list, list) and results_list:
            first = results_list[0]
            if isinstance(first, dict):
                counts = first
    total_shots = sum(v for v in counts.values()) if counts else 0
    probs = {k: v / float(total_shots) for k, v in counts.items()} if total_shots > 0 else {}
    out["counts"] = counts
    out["probabilities"] = probs
    out["status"] = 0

    return out


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0, "message": "ok"})


@app.route("/run", methods=["POST"])
def run():
    t0 = time.time()
    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")
        payload = request.get_json(force=True)

        # Minimal request logging (never log secrets)
        size = len(request.data) if request.data else 0
        top_keys = list(payload.keys()) if isinstance(payload, dict) else []
        logger.info(
            "REQ POST /run ct=%s size=%s keys=%s ip=%s",
            request.headers.get("Content-Type"),
            size,
            top_keys,
            request.remote_addr,
        )

        src_b64 = payload.get("src")
        cfg = payload.get("config", {})
        if not src_b64:
            raise BadRequest("Missing required field 'src' (base64-encoded OpenQASM)")
        if not isinstance(cfg, dict):
            raise BadRequest("Field 'config' must be an object")

        # Decode QASM
        qasm = _decode_qasm_from_base64(src_b64)

        # Save QASM to file
        qasm_filename = None
        try:
            ts = time.strftime("%Y%m%d-%H%M%S")
            short_id = uuid.uuid4().hex[:8]
            qasm_filename = f"qasm_{ts}_{short_id}.qasm"
            (LOG_DIR / qasm_filename).write_text(qasm, encoding="utf-8")
            logger.info("Saved incoming QASM to %s", LOG_DIR / qasm_filename)
        except Exception as save_exc:
            logger.warning("Failed to save incoming QASM: %s", save_exc)

        # Execute with Fire Opal
        result = _execute_fire_opal(qasm, cfg)

        # Include stored filename (if any) for traceability
        if qasm_filename:
            result["qasm_file"] = str(LOG_DIR / qasm_filename)

        dt_ms = (time.time() - t0) * 1000.0
        logger.info("RES /run status=200 took=%.1fms", dt_ms)
        return jsonify(result)

    except BadRequest as br:
        dt_ms = (time.time() - t0) * 1000.0
        logger.warning("BadRequest /run: %s (%.1fms)", br, dt_ms)
        return jsonify({"status": 1, "error": str(br)}), 400
    except Exception as exc:
        dt_ms = (time.time() - t0) * 1000.0
        logger.exception("Unhandled error in /run (%.1fms)", dt_ms)
        return jsonify({
            "status": 2,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }), 500


if __name__ == "__main__":
    # For local dev; in prod use gunicorn
    app.run(host="127.0.0.1", port=5201, debug=True)

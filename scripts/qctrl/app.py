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


def _safe_repr(obj, maxlen=800):
    try:
        s = repr(obj)
        if len(s) > maxlen:
            s = s[:maxlen] + "...(truncated)"
        return s
    except Exception:
        return f"<unrepr {type(obj).__name__}>"

def _best_effort_to_dict(obj):
    try:
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        # last resort: show selected attrs
        out = {}
        for k in ("id", "job_id", "jobId", "uid", "status", "state", "backend", "name"):
            try:
                if hasattr(obj, k):
                    out[k] = getattr(obj, k)
            except Exception:
                pass
        return out or {"type": type(obj).__name__}
    except Exception:
        return {"type": type(obj).__name__}


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

# Memoized flag to avoid re-authenticating on every request
_QCTRL_AUTHED = False

def _ensure_qctrl_auth_from_request():
    """
    Authenticate to Q-CTRL using qctrl_api_key passed as a query parameter.
    Called by /status and /result handlers.
    """
    global _QCTRL_AUTHED
    if _QCTRL_AUTHED:
        return
    api_key = request.args.get("qctrl_api_key")
    if not api_key:
        raise BadRequest("Missing required query parameter: qctrl_api_key")
    fo.authenticate_qctrl_account(api_key=api_key)
    _QCTRL_AUTHED = True

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

from datetime import datetime, timezone, timedelta

def _extract_action_id_from_job(job) -> str | None:
    # Try common attribute names without guessing blindly in logs
    for attr in ("action_id", "model_id", "id", "job_id", "uid"):
        try:
            if hasattr(job, attr):
                val = getattr(job, attr)
                if val:
                    return str(val)
        except Exception:
            pass
    # Try to_dict() if available
    try:
        if hasattr(job, "to_dict"):
            d = job.to_dict()
            for k in ("action_id", "model_id", "id", "job_id", "uid"):
                if k in d and d[k]:
                    return str(d[k])
    except Exception:
        pass
    return None

def _find_recent_action_id(function_name: str = "execute") -> str | None:
    # Fallback: ask Fire Opal for very recent actions and take the newest 'execute'
    try:
        meta_list = fo.get_action_metadata(limit=3)  # small, fast
        # Each element is a dataclass with .name and .model_id per docs
        # Prefer the most recent matching 'execute'
        for m in meta_list:
            try:
                if getattr(m, "name", None) == function_name and getattr(m, "model_id", None):
                    return str(m.model_id)
            except Exception:
                continue
    except Exception:
        pass
    return None

def _execute_fire_opal(qasm: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    creds = _auth_qctrl_and_ibm(cfg)
    backend_name = _select_backend(creds, cfg.get("backend_name"))
    shot_count = int(cfg.get("shot_count", 1024))

    submitted_at = datetime.now(timezone.utc)
    job = fo.execute(
        circuits=[qasm],
        shot_count=shot_count,
        credentials=creds,
        backend_name=backend_name,
    )

    # 1) Try to grab Action ID straight from the job object
    action_id = _extract_action_id_from_job(job)

    # 2) If missing, do a quick metadata peek for the newest 'execute'
    if not action_id:
        try:
            status_payload = job.status()  # quick; also proves the job exists
            logger.info("OPAL_STATUS keys=%s sample=%r",
                        list(status_payload.keys()) if isinstance(status_payload, dict) else None,
                        status_payload)
        except Exception:
            pass
        action_id = _find_recent_action_id("execute")

    wait = bool(cfg.get("wait", True))
    out: Dict[str, Any] = {
        "action_id": action_id,          
        "backend_name": backend_name,
        "shot_count": shot_count,
        "waited": wait,
    }

    logger.info("SUBMIT_SUMMARY backend=%s shots=%s waited=%s action_id=%s",
                backend_name, shot_count, wait, action_id)

    if not wait:
        out["status"] = 0
        out["message"] = "submitted"
        return out

    # Wait path (unchanged)
    result = job.result()
    out["raw_result"] = result
    counts = {}
    if isinstance(result, dict):
        results_list = result.get("results")
        if isinstance(results_list, list) and results_list:
            first = results_list[0]
            if isinstance(first, dict):
                counts = first
        # Optional: surface provider job ids when present
        if "provider_job_ids" in result:
            out["provider_job_ids"] = result["provider_job_ids"]

    total_shots = sum(v for v in counts.values()) if counts else 0
    probs = {k: v / float(total_shots) for k, v in counts.items()} if total_shots > 0 else {}
    out["counts"] = counts
    out["probabilities"] = probs
    out["status"] = 0
    return out

def _parse_counts_and_probs(result: Dict[str, Any]) -> tuple[Dict[str, int], Dict[str, float]]:
    counts: Dict[str, int] = {}
    if isinstance(result, dict):
        results_list = result.get("results")
        if isinstance(results_list, list) and results_list:
            first = results_list[0]
            if isinstance(first, dict):
                counts = first
    total_shots = sum(v for v in counts.values()) if counts else 0
    probs = {k: v / float(total_shots) for k, v in counts.items()} if total_shots > 0 else {}
    return counts, probs


def _get_action_status_best_effort(action_id: str) -> Dict[str, Any]:
    """
    Best-effort status lookup without blocking for results.
    Tries Fire Opal metadata, falls back to UNKNOWN if not available.
    """
    try:
        meta_list = fo.get_action_metadata()  # returns recent actions; SDK-dependent
        # Try objects (attrs) and dicts
        for m in meta_list:
            model_id = getattr(m, "model_id", None)
            if not model_id and isinstance(m, dict):
                model_id = m.get("model_id")
            if str(model_id) == str(action_id):
                name = getattr(m, "name", None) or (m.get("name") if isinstance(m, dict) else None)
                state = (
                    getattr(m, "state", None)
                    or getattr(m, "status", None)
                    or (m.get("state") if isinstance(m, dict) else None)
                    or (m.get("status") if isinstance(m, dict) else None)
                )
                return {"action_id": action_id, "name": name, "state": state or "UNKNOWN"}
    except Exception as e:
        logger.warning("STATUS_LOOKUP_FAILED action_id=%s err=%s", action_id, e)
    return {"action_id": action_id, "state": "UNKNOWN"}


def _execute_fire_opal2(qasm: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    creds = _auth_qctrl_and_ibm(cfg)
    backend_name = _select_backend(creds, cfg.get("backend_name"))
    shot_count = int(cfg.get("shot_count", 1024))

    job = fo.execute(
        circuits=[qasm],
        shot_count=shot_count,
        credentials=creds,
        backend_name=backend_name,
    )

    try:
        logger.info(
            "OPAL_SUBMIT backend=%s shots=%s job_obj=%s",
            backend_name, shot_count, _safe_repr(job)
        )
        logger.info("OPAL_SUBMIT_DICT %s", _best_effort_to_dict(job))
    except Exception:
        pass

    status_payload = None
    try:
        status_payload = job.status()
        logger.info("OPAL_STATUS type=%s keys=%s sample=%r",
                    type(status_payload).__name__,
                    list(status_payload.keys()) if isinstance(status_payload, dict) else None,
                    status_payload if isinstance(status_payload, dict) else status_payload)
    except Exception as e:
        logger.warning("OPAL_STATUS_FAILED %s", e)

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

@app.route("/status/<action_id>", methods=["GET"])
def status_action(action_id: str):
    t0 = time.time()
    try:
        _ensure_qctrl_auth_from_request()

        # Best-effort status using Fire Opal metadata
        info = _get_action_status_best_effort(action_id)  # your helper

        dt_ms = (time.time() - t0) * 1000.0
        logger.info(
            "RES /status/%s status=200 took=%.1fms state=%s",
            action_id, dt_ms, info.get("state")
        )
        return jsonify({"status": 0, **info})
    except BadRequest as br:
        dt_ms = (time.time() - t0) * 1000.0
        logger.warning("BadRequest /status/%s: %s (%.1fms)", action_id, br, dt_ms)
        return jsonify({"status": 1, "error": str(br)}), 400
    except Exception as exc:
        dt_ms = (time.time() - t0) * 1000.0
        logger.exception("Unhandled error in /status/%s (%.1fms)", action_id, dt_ms)
        return jsonify({"status": 2, "error": str(exc)}), 500


@app.route("/status2/<action_id>", methods=["GET"])
def status_action2(action_id: str):
    t0 = time.time()
    try:
        info = _get_action_status_best_effort(action_id)
        dt_ms = (time.time() - t0) * 1000.0
        logger.info("RES /status/%s status=200 took=%.1fms state=%s", action_id, dt_ms, info.get("state"))
        return jsonify({"status": 0, **info})
    except Exception as exc:
        dt_ms = (time.time() - t0) * 1000.0
        logger.exception("Unhandled error in /status/%s (%.1fms)", action_id, dt_ms)
        return jsonify({"status": 2, "error": str(exc)}), 500

@app.route("/result/<action_id>", methods=["GET"])
def result_action(action_id: str):
    t0 = time.time()
    try:
        # authenticate from the query param ?qctrl_api_key=... (as discussed earlier)
        _ensure_qctrl_auth_from_request()

        # 1) Check state once (non-blocking)
        info = _get_action_status_best_effort(action_id)  # returns {'action_id', 'state', ...}
        state = str(info.get("state") or "UNKNOWN").upper()

        # 2) If not terminal -> return pending immediately (never wait)
        if state not in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            dt_ms = (time.time() - t0) * 1000.0
            logger.info("RES /result/%s pending state=%s took=%.1fms", action_id, state, dt_ms)
            return jsonify({
                "status": 0,
                "action_id": action_id,
                "state": state,
                "pending": True
            })

        # 3) Terminal state -> fetch final result (fast path)
        result = fo.get_result(action_id)

        # Same counts/probabilities parsing logic you use in /run when wait=True
        counts = {}
        if isinstance(result, dict):
            results_list = result.get("results")
            if isinstance(results_list, list) and results_list:
                first = results_list[0]
                if isinstance(first, dict):
                    counts = first
        total_shots = sum(v for v in counts.values()) if counts else 0
        probabilities = {k: v / float(total_shots) for k, v in counts.items()} if total_shots > 0 else {}

        out = {
            "status": 0,
            "action_id": action_id,
            "state": state,
            "raw_result": result,
            "counts": counts,
            "probabilities": probabilities,
        }
        if isinstance(result, dict) and "provider_job_ids" in result:
            out["provider_job_ids"] = result["provider_job_ids"]

        dt_ms = (time.time() - t0) * 1000.0
        logger.info("RES /result/%s done state=%s took=%.1fms", action_id, state, dt_ms)
        return jsonify(out)

    except BadRequest as br:
        dt_ms = (time.time() - t0) * 1000.0
        logger.warning("BadRequest /result/%s: %s (%.1fms)", action_id, br, dt_ms)
        return jsonify({"status": 1, "error": str(br)}), 400
    except Exception as exc:
        dt_ms = (time.time() - t0) * 1000.0
        logger.exception("Unhandled error in /result/%s (%.1fms)", action_id, dt_ms)
        return jsonify({"status": 2, "error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0, "message": "ok"})


# --- Add near your other helpers ---
def _require_query_or_cfg(cfg: Dict[str, Any], key: str) -> Any:
    # Reuse your existing _require_config for body, but allow query fallback
    val = cfg.get(key)
    if not val:
        # try from query string (?qctrl_api_key=...)
        val = request.args.get(key)
    if not val:
        raise BadRequest(f"Missing required field: {key}")
    return val

def _coerce_int(val, default: int) -> int:
    try:
        return int(val)
    except Exception:
        return default


# --- New endpoint: list jobs/actions from Q-CTRL ---
@app.route("/jobs", methods=["POST"])
def list_jobs():
    t0 = time.time()
    try:
        if not request.is_json:
            raise BadRequest("Content-Type must be application/json")

        payload = request.get_json(force=True) or {}
        cfg = payload.get("config", {})
        if not isinstance(cfg, dict):
            raise BadRequest("Field 'config' must be an object")

        # Minimal request logging (never log secrets)
        size = len(request.data) if request.data else 0
        top_keys = list(payload.keys()) if isinstance(payload, dict) else []
        logger.info(
            "REQ POST /jobs ct=%s size=%s keys=%s ip=%s",
            request.headers.get("Content-Type"),
            size,
            top_keys,
            request.remote_addr,
        )

        # Authenticate to Q-CTRL (like in /run, but only Q-CTRL key is required here)
        api_key = _require_query_or_cfg(cfg, "qctrl_api_key")
        fo.authenticate_qctrl_account(api_key=api_key)  # your code pattern uses Fire Opal auth in /run:contentReference[oaicite:3]{index=3}

        # Optional client-side filters
        # (We fetch a small recent window and filter here to keep the call fast/predictable)
        limit = _coerce_int(payload.get("limit", 50), 50)  # default 50
        name_filter = payload.get("name")         # e.g., "execute"
        state_filter = payload.get("state")       # e.g., "SUCCEEDED" / "STARTED" / "FAILED"

        # Pull recent actions from Q-CTRL Fire Opal
        # NOTE: If the SDK supports server-side limit/filter args, you can pass them here.
        meta_list = fo.get_action_metadata()  # returns recent actions

        jobs = []
        count_scanned = 0
        for m in meta_list:
            # Extract robustly (supports dataclass-like objects or dicts)
            def get(v, *keys):
                if isinstance(v, dict):
                    for k in keys:
                        if k in v and v[k] is not None:
                            return v[k]
                    return None
                # object-like
                for k in keys:
                    try:
                        if hasattr(v, k):
                            val = getattr(v, k)
                            if val is not None:
                                return val
                    except Exception:
                        pass
                return None

            model_id = get(m, "model_id", "id", "action_id")
            name = get(m, "name")
            state = get(m, "state", "status", "action_status")
            created_at = get(m, "created_at", "creation_time", "timestamp")
            # Optional additional fields if present
            backend = get(m, "backend", "device", "device_name")

            # Apply optional filters
            if name_filter and str(name) != str(name_filter):
                continue
            if state_filter and str(state).upper() != str(state_filter).upper():
                continue

            jobs.append({
                "action_id": str(model_id) if model_id is not None else None,
                "name": name,
                "state": state,
                "created_at": created_at,
                "backend": backend,
            })
            count_scanned += 1
            if len(jobs) >= limit:
                break

        dt_ms = (time.time() - t0) * 1000.0
        logger.info("RES /jobs status=200 took=%.1fms scanned=%s returned=%s", dt_ms, count_scanned, len(jobs))
        return jsonify({"status": 0, "count": len(jobs), "jobs": jobs})

    except BadRequest as br:
        dt_ms = (time.time() - t0) * 1000.0
        logger.warning("BadRequest /jobs: %s (%.1fms)", br, dt_ms)
        return jsonify({"status": 1, "error": str(br)}), 400
    except Exception as exc:
        dt_ms = (time.time() - t0) * 1000.0
        logger.exception("Unhandled error in /jobs (%.1fms)", dt_ms)
        return jsonify({
            "status": 2,
            "error": str(exc),
            "trace": traceback.format_exc(),
        }), 500


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

from flask import Flask, jsonify
from flask import request
import psycopg2
import json
import logging
import base64
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit import transpile
from qiskit.qasm3 import loads as qasm3_loads
from datetime import datetime
import os
from datetime import datetime
from flask_cors import CORS
import uuid
import secrets
import requests
import threading
import psutil
import traceback
from laboneq.simple import Session, DeviceSetup
from laboneq.openqasm3.openqasm3_importer import exp_from_qasm


VERSION = "1.0.0"

# Configure logging
# Generate filename with timestamp
log_filename = datetime.now().strftime("logs/server_%Y%m%d_%H%M%S.log")

# Configure logging to file + console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logging.info(f"Logging started, writing to {log_filename}")


app = Flask(__name__)
CORS(app)


# Load config
with open("config.json") as f:
    config = json.load(f)

db_config = {
    "host": config["host"],
    "port": config["port"],
    "database": config["database"],
    "user": config["user"],
    "password": config["password"]
}

def create_job_record(user_id, qasm_b64, backend_type, instance="sim", status_str="QUEUED", mode=None, shots=None):
    """Insert a new job row and return its internal uid (uuid)."""
    job_uid = str(uuid.uuid4())
    # decode only for storing readable input
    try:
        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
    except Exception:
        qasm_str = "<invalid base64 QASM>"

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (uid, user_id, input, instance, qpu, status_str, mode, shots)
            VALUES (%s,   %s,      %s,    %s,      %s,  %s,        %s,   %s);
            """,
            (job_uid, user_id, qasm_str, instance, backend_type, status_str, mode,
             int(shots) if shots is not None else None)
        )

        conn.commit()
        return job_uid
    except Exception as e:
        logging.error(f"create_job_record error: {e}")
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


def update_job_status(job_uid, status_str, results_obj=None, error_msg=None):
    """Update job status/results; set end_time when terminal."""
    terminal = status_str in ("DONE", "ERROR")
    results_json = None
    if results_obj is not None:
        results_json = json.dumps(results_obj)
    elif error_msg is not None:
        results_json = json.dumps({"error": error_msg})

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        if terminal:
            cursor.execute(
                """
                UPDATE jobs
                SET status_str = %s,
                    results = %s,
                    end_time = %s
                WHERE uid = %s;
                """,
                (status_str, results_json, datetime.utcnow(), job_uid)
            )
        else:
            cursor.execute(
                "UPDATE jobs SET status_str = %s WHERE uid = %s;",
                (status_str, job_uid)
            )
        conn.commit()
    except Exception as e:
        logging.error(f"update_job_status error: {e}")
        raise
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

def _qvm_execute_job_async(job_uid, qasm_b64, shots, backend_type):
    """Background worker: forward to Node B, update DB with result or error."""
    try:
        update_job_status(job_uid, "RUNNING")

        node_b_url = "https://cloud.quantag-it.com/api1/run"
        payload = {"qasm_b64": qasm_b64, "shots": int(shots)}

        logging.info(f"[{job_uid}] forwarding to Node B: {node_b_url}")
        resp = requests.post(node_b_url, json=payload, timeout=600)
        resp.raise_for_status()
        node_b_result = resp.json()

        logging.info(f"[{job_uid}] Node B result received")
        update_job_status(job_uid, "DONE", results_obj=node_b_result)

    except Exception as e:
        logging.error(f"[{job_uid}] async execution failed: {e}")
        try:
            update_job_status(job_uid, "ERROR", error_msg=str(e))
        except Exception as e2:
            logging.error(f"[{job_uid}] failed to write ERROR status: {e2}")


def _submit_zi_job_core(job_uid: str, qasm_b64: str, options: dict):
    """
    Execute a Zurich Instruments (LabOne Q) job.
    Requires options["setup_b64"] containing base64-encoded YAML setup.
    """
    logging.info(f"Options keys: {list(options.keys())}")

    try:
        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        setup_b64 = options.get("setup_b64")
        if not setup_b64:
            return 400, {"error": "Missing 'setup_b64' in options"}

        yaml_str = base64.b64decode(setup_b64).decode("utf-8")

        # --- Save temporary files for debugging ---
        os.makedirs("scripts", exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        qasm_path = f"scripts/script_{ts}.qasm"
        yaml_path = f"scripts/setup_{ts}.yaml"
        with open(qasm_path, "w") as f: f.write(qasm_str)
        with open(yaml_path, "w") as f: f.write(yaml_str)

        # --- Load device setup and prepare experiment ---
        device_setup = DeviceSetup.from_yaml(yaml_path)
        qubits = device_setup.qubits
        qubit_map = {f"_qubit{i}": q for i, q in enumerate(qubits)}

        exp = exp_from_qasm(qasm_str, qubits=qubit_map)

        # --- Run (emulation mode by default) ---
        session = Session(device_setup=device_setup)
        session.connect(do_emulation=True)
        compiled = session.compile(exp)
        results = session.run(compiled)

        results_json = {
            "acquired_results": str(results.acquired_results),
            "timestamp": datetime.utcnow().isoformat(),
            "success": True
        }

        update_job_status(job_uid, "DONE", results_obj=results_json)
        logging.info(f"[{job_uid}] ZI job completed successfully")
        return 200, {"message": "ZI job completed", "results": results_json}

    except Exception as e:
        logging.error(f"[{job_uid}] ZI job failed: {e}")
        logging.error(traceback.format_exc())
        update_job_status(job_uid, "ERROR", error_msg=str(e))
        return 500, {"error": str(e)}


def get_users():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users;")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route('/health', methods=['GET'])
def health():
    # Disk space in GB
    disk_usage = psutil.disk_usage('/')
    free_gb = round(disk_usage.free / (1024**3), 2)

    # CPU load (1-minute average)
    cpu_load = psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else psutil.cpu_percent(interval=0.1)

    return jsonify({
        "status": 0,
        "version": VERSION,
        "disk_free_gb": free_gb,
        "cpu_load": cpu_load
    }), 200


@app.route("/users/<user_id>/jobs", methods=["GET"])
def user_jobs(user_id):
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE user_id = %s;", (user_id,))
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        jobs = [dict(zip(columns, row)) for row in rows]
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def _submit_qctrl_job_core(job_uid: str, src_b64: str, options: dict):
    """
    Forward the job to the Q-CTRL microservice (async) and persist provider fields.
    """
    try:
        # mark running while we submit
        update_job_status(job_uid, "RUNNING")

        service_url = (
            (options or {}).get("service_url")
            or os.getenv("QCTRL_SERVICE_URL")
            or "https://cloud.quantag-it.com/api21/run"
        )

        # Force async submit (never wait here)
        cfg = dict(options or {})
        cfg["wait"] = False

        payload = {"src": src_b64, "config": cfg}

        logging.info(f"[{job_uid}] forwarding to Q-CTRL service: {service_url}")
        resp = requests.post(service_url, json=payload, timeout=120)
        text_preview = (resp.text or "")[:500]
        logging.info(f"[{job_uid}] Q-CTRL resp.status={resp.status_code} body[0:500]={text_preview}")

        try:
            resp_json = resp.json()
        except Exception:
            resp_json = {"raw": text_preview}

        if resp.status_code >= 400:
            update_job_status(job_uid, "ERROR",
                              error_msg=f"Q-CTRL error: {resp.status_code} {text_preview}")
            return resp.status_code, {"error": "Q-CTRL service error", "details": resp_json}

        action_id = resp_json.get("action_id") or resp_json.get("job_id")
        backend_name = resp_json.get("backend_name")
        # Initial provider status (what we know right after submit)
        provider_status = "STARTED"

        # Persist provider fields (and keep job queued)
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE jobs
               SET provider_job_id = %s,
                   provider_job_status = %s,
                   qpu = COALESCE(%s, qpu),
                   status_str = %s
             WHERE uid = %s;
            """,
            (str(action_id) if action_id else None, provider_status,
             backend_name, "QUEUED", job_uid)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Optionally stash submit response for traceability (non-terminal)
        update_job_status(job_uid, "QUEUED", results_obj={"submit_response": resp_json})

        return 202, {
            "message": "Q-CTRL job submitted",
            "action_id": action_id,
            "backend": backend_name
        }

    except Exception as e:
        logging.exception(f"[{job_uid}] Q-CTRL submit failed")
        try:
            update_job_status(job_uid, "ERROR", error_msg=str(e))
        except Exception:
            pass
        return 500, {"error": str(e)}



@app.route("/qvm/job/<job_uid>", methods=["GET"])
def qvm_job_status(job_uid):
    # Validate API key and ownership
    api_key = request.headers.get("X-API-Key") or request.args.get("apikey")
    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"error": "Invalid or missing API key"}), 403

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT uid, user_id, status_str, results, submitted_at, end_time, qpu, instance FROM jobs WHERE uid = %s;",
            (job_uid,)
        )
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Job not found"}), 404

        uid, owner_id, status_str, results, submitted_at, end_time, qpu, instance = row
        if owner_id != user_id:
            return jsonify({"error": "Forbidden"}), 403

        payload = {
            "job_uid": uid,
            "status": status_str,
            "backend": qpu,
            "instance": instance,
            "submitted_at": submitted_at.isoformat() if submitted_at else None,
            "end_time": end_time.isoformat() if end_time else None,
        }

        # results column may be TEXT/JSON; return as dict if present
        if results:
            try:
                payload["results"] = json.loads(results) if isinstance(results, str) else results
            except Exception:
                payload["results"] = results  # raw

        return jsonify(payload), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/apikeys/delete_all", methods=["POST"])
def delete_all_apikeys():
    """Delete all API keys for a given user_id"""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM apikeys WHERE user_id = %s RETURNING uid;", (user_id,))
        rows = cursor.fetchall()
        conn.commit()

        if not rows:
            return jsonify({"message": "No API keys found for this user", "deleted": 0}), 200

        deleted_keys = [row[0] for row in rows]
        return jsonify({
            "message": f"Deleted {len(deleted_keys)} API keys",
            "deleted": len(deleted_keys),
            "uids": deleted_keys
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- Node registry (containers self-register) ---

def _require_node_register_token():
    expected = os.getenv("NODE_REGISTER_TOKEN", "")
    if not expected:
        # Fail closed if you forgot to configure it
        return False, (jsonify({"error": "NODE_REGISTER_TOKEN is not configured on server"}), 500)

    got = request.headers.get("X-Node-Token") or request.args.get("token") or ""
    if got != expected:
        return False, (jsonify({"error": "Forbidden"}), 403)

    return True, None


@app.route("/nodes/register", methods=["POST"])
def nodes_register():
    data = request.get_json(silent=True) or {}

    endpoint = data.get("endpoint")
    if not endpoint:
        return jsonify({"error": "Missing endpoint"}), 400

    provider_id = data.get("provider_id")  # optional
    status = int(data.get("status", 0))
    gpu = int(data.get("gpu", 0))
    qpu = int(data.get("qpu", 0))
    caps = data.get("caps")

    if isinstance(caps, dict):
        caps = json.dumps(caps)

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        if provider_id:
            cursor.execute(
                """
                INSERT INTO nodes (provider_id, endpoint, status, caps, gpu, qpu)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING uid, provider_id, endpoint, status, caps, gpu, qpu;
                """,
                (provider_id, endpoint, status, caps, gpu, qpu),
            )
        else:
            cursor.execute(
                """
                INSERT INTO nodes (endpoint, status, caps, gpu, qpu)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING uid, provider_id, endpoint, status, caps, gpu, qpu;
                """,
                (endpoint, status, caps, gpu, qpu),
            )

        row = cursor.fetchone()
        conn.commit()

        cols = [d[0] for d in cursor.description]
        return jsonify(dict(zip(cols, row))), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()



@app.route("/nodes", methods=["GET"])
def nodes_list():
#    ok, resp = _require_node_register_token()
#    if not ok:
#        return resp

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT uid, provider_id, endpoint, status, caps, gpu, qpu FROM nodes ORDER BY endpoint ASC;"
        )
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        return jsonify([dict(zip(cols, r)) for r in rows]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def validate_api_key(api_key):
    """Return user_id if API key is valid, else None"""
    if not api_key:
        return None

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id FROM apikeys WHERE api_key = %s AND active = TRUE;",
            (api_key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception as e:
        logging.error(f"API key validation error: {e}")
        return None
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/check_apikey", methods=["POST"])
def check_apikey():
    data = request.get_json()
    api_key = data.get("apikey")

    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"valid": False, "error": "Invalid or missing API key"}), 403

    return jsonify({"valid": True, "user_id": user_id}), 200

@app.route("/check_job", methods=["POST"])
def check_job():
    data = request.get_json()
    user_id = data.get("user_id")
    job_id = data.get("job_id")

    if not user_id or not job_id:
        return jsonify({"error": "Missing user_id or job_id"}), 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM jobs WHERE user_id = %s AND uid = %s;",
            (user_id, job_id)
        )
        job_row = cursor.fetchone()

        if not job_row:
            return jsonify({"error": "Job not found for this user"}), 404

        desc = [col.name for col in cursor.description]
        job_dict = dict(zip(desc, job_row))
        ibm_job_id = job_dict["job_id"]
        previous_status = job_dict.get("status_str")

        # Load the token from users table
        cursor.execute("SELECT token FROM users WHERE uid = %s;", (user_id,))
        token_row = cursor.fetchone()

        if not token_row or not token_row[0]:
            return jsonify({"error": "Token not found for this user"}), 403

        token = token_row[0]
        logging.info("Loaded token for user..")

        # Initialize Qiskit service
        QiskitRuntimeService.save_account(
            token=token,
            instance="one",  # or read instance from DB if needed
            name="myacc",
            set_as_default=True,
            overwrite=True
        )
        service = QiskitRuntimeService()
        job = service.job(ibm_job_id)

        logging.info(job.status())

        status = str(job.status())
       # Update status_str in database
        result_data = None
        if status == "DONE":
            logging.info("Job is finished")
            result = job.result()
            result_data = {}
            for reg_name, bit_array in result[0].data.__dict__.items():
                try:
                    counts = bit_array.get_counts()
                    result_data[reg_name] = counts
                except Exception as e:
                    result_data[reg_name] = f"Error extracting counts: {str(e)}"

            cursor.execute(
                """
                UPDATE jobs
                SET status_str = %s,
                    results = %s
                WHERE uid = %s;
                """,
                (status, json.dumps(result_data), job_id)
            )

        if previous_status != "DONE":
            cursor.execute(
                """
                UPDATE jobs
                SET end_time = %s
                WHERE uid = %s;
                """,
                (datetime.utcnow(), job_id)
            )


        else:
            cursor.execute(
                """
                UPDATE jobs
                SET status_str = %s
                WHERE uid = %s;
                """,
                (status, job_id)
            )

        conn.commit()
        return jsonify({}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/qvm/submit", methods=["POST"])
def qvm_submit():
    data = request.get_json(silent=True) or {}
    cfg = data.get("config") or {}

    # --- 1) Resolve inputs (new format first, keep old as fallback) ---
    # API key for your gateway
    api_key = (
        data.get("apikey")
        or request.headers.get("X-API-Key")
        or cfg.get("apikey")
    )
    if not api_key:
        return jsonify({"error": "Missing API key"}), 400

    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"error": "Invalid API key"}), 403

    # QASM (base64)
    src_b64 = data.get("src") or data.get("qasm")
    if not src_b64:
        return jsonify({"error": "Missing 'src' (base64)"}), 400

    src_type = (data.get("src_type") or cfg.get("src_type") or "qasm").lower()

    # Execution (prefer explicit `execution` object; else pull mode/shots from config)
    exec_cfg = data.get("execution") or cfg.get("execution") or {}
    mode = (exec_cfg.get("mode") or cfg.get("mode") or "sampler").lower()
    try:
        shots = int(exec_cfg.get("shots", cfg.get("shots", 1024)))
    except Exception:
        shots = 1024

    # Backend (prefer top-level in new format; else from config)
    #backend = (data.get("backend") or cfg.get("backend") or "").lower()
    backend = (data.get("backend") or cfg.get("backend") or cfg.get("submit", {}).get("backend") or "").lower()

    if not backend:
        return jsonify({"error": "Missing 'backend'"}), 400

    # Options: pass through as-is when present; otherwise synthesize from cfg
    options = data.get("options") or cfg.get("options") or cfg.get("submit", {}).get("options") or {}
    if not isinstance(options, dict):
        options = {}
    logging.info(f"Backend: {backend}, Options keys: {list(options.keys())}")

    # Common alias normalization (non-breaking, only fills if missing)
    # IBM-related
    if "instance" not in options and "instance" in cfg:
        options["instance"] = cfg["instance"]
    if "device" not in options and "device" in cfg:
        options["device"] = cfg["device"]
    if "token" not in options and "ibm_token" in cfg:
        options["token"] = cfg["ibm_token"]

    # Q-CTRL-specific (if you keep these in config root, surface into options)
    if "qctrl_api_key" not in options and "qctrl_api_key" in cfg:
        options["qctrl_api_key"] = cfg["qctrl_api_key"]
    if "ibm_token" not in options and "ibm_token" in cfg:
        options["ibm_token"] = cfg["ibm_token"]

    # --- 2) Create job record ---
    try:
        job_uid = create_job_record(
            user_id=user_id,
            qasm_b64=src_b64,
            backend_type=backend,
            instance=options.get("instance", "sim"),
            status_str="QUEUED",
            mode=mode,
            shots=shots,
        )
    except Exception as e:
        logging.exception("DB insert failed")
        return jsonify({"error": f"DB insert failed: {e}"}), 500

    # --- 3) Backend-specific execution ---
    if backend == "ibm":
        try:
            status, payload = _submit_ibm_job_core(
                job_uid=job_uid,
                qasm_b64=src_b64,
                user_id=user_id,
                token=options.get("token") or options.get("ibm_token"),
                inst=options.get("instance"),
                back=options.get("device"),
            )
            if status != 200:
                update_job_status(job_uid, "ERROR", error_msg=payload.get("error"))
                return jsonify(payload | {"job_uid": job_uid}), status
        except Exception as e:
            logging.exception("IBM submit failed")
            update_job_status(job_uid, "ERROR", error_msg=str(e))
            return jsonify({"error": str(e), "job_uid": job_uid}), 500

    elif backend == "cudaq":
        try:
            t = threading.Thread(
                target=_qvm_execute_job_async,
                args=(job_uid, src_b64, shots, backend),
                daemon=True,
            )
            t.start()
        except Exception as e:
            logging.exception("CUDA-Q submit failed")
            update_job_status(job_uid, "ERROR", error_msg=str(e))
            return jsonify({"error": str(e), "job_uid": job_uid}), 500

    elif backend == "qctrl":
        try:
            # Pass through options as provided (they may contain qctrl_api_key, ibm_token, instance, device, etc.)
            status, payload = _submit_qctrl_job_core(
                job_uid=job_uid,
                src_b64=src_b64,
                options=options,
            )
            if status != 200:
                update_job_status(job_uid, "ERROR", error_msg=payload.get("error"))
                return jsonify({"job_uid": job_uid, **payload}), status
        except Exception as e:
            logging.exception("Q-CTRL submit failed")
            update_job_status(job_uid, "ERROR", error_msg=str(e))
            return jsonify({"error": str(e), "job_uid": job_uid}), 500

    elif backend == "zi":
        try:
            status, payload = _submit_zi_job_core(
                job_uid=job_uid,
                qasm_b64=src_b64,
                options=options,
            )
            if status != 200:
                update_job_status(job_uid, "ERROR", error_msg=payload.get("error"))
                return jsonify({"job_uid": job_uid, **payload}), status
        except Exception as e:
            logging.exception("ZI submit failed")
            update_job_status(job_uid, "ERROR", error_msg=str(e))
            return jsonify({"error": str(e), "job_uid": job_uid}), 500

    else:
        update_job_status(job_uid, "ERROR", error_msg=f"Unsupported backend: {backend}")
        return jsonify({
            "error": "Unsupported backend",
            "job_uid": job_uid,
            "details": {"supported": ["ibm", "cudaq", "qctrl"], "received": backend},
        }), 400

    # --- 4) Response ---
    return jsonify({
        "job_uid": job_uid,
        "status": "QUEUED",
        "backend": backend,
        "shots": shots,
        "mode": mode,
        "src_type": src_type,
    }), 202



@app.route("/providers", methods=["GET"])
def get_providers():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM providers;")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        providers = [dict(zip(columns, row)) for row in rows]
        return jsonify(providers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/subs", methods=["GET"])
def get_subs():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptions;")
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        providers = [dict(zip(columns, row)) for row in rows]
        return jsonify(providers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def generate_api_key():
    return secrets.token_hex(32)  # 64 chars

@app.route("/apikeys/<user_id>", methods=["GET"])
def list_apikeys(user_id):
    """List API keys for a user"""
    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT uid, api_key, created_at, active FROM apikeys WHERE user_id = %s;", (user_id,))
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return jsonify([dict(zip(columns, row)) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/apikeys", methods=["POST"])
def create_apikey():
    """Create new API key for a user"""
    data = request.get_json()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    new_uid = str(uuid.uuid4())
    api_key = generate_api_key()

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO apikeys (uid, user_id, api_key)
            VALUES (%s, %s, %s)
            RETURNING uid, api_key, created_at, active;
            """,
            (new_uid, user_id, api_key)
        )
        row = cursor.fetchone()
        conn.commit()
        columns = [desc[0] for desc in cursor.description]
        return jsonify(dict(zip(columns, row)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/apikeys/<uuid:key_id>/deactivate", methods=["POST"])
def deactivate_apikey(key_id):
    """Deactivate an API key"""
    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE apikeys SET active = FALSE WHERE uid = %s RETURNING uid, api_key, active;",
            (str(key_id),)
        )
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": "API key not found"}), 404
        columns = [desc[0] for desc in cursor.description]
        return jsonify(dict(zip(columns, row)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/apikeys/<uuid:key_id>", methods=["DELETE"])
def delete_apikey(key_id):
    """Delete an API key"""
    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM apikeys WHERE uid = %s RETURNING uid;", (str(key_id),))
        row = cursor.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": "API key not found"}), 404
        return jsonify({"message": "API key deleted", "uid": row[0]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/update_user", methods=["POST"])
def update_user():
    data = request.get_json()
    uid = data.get("uid")

    if not uid:
        return jsonify({"error": "Missing uid"}), 400

    update_fields = {k: v for k, v in data.items() if k != "uid"}
    if not update_fields:
        return jsonify({"error": "No fields to update"}), 400

    set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
    values = list(update_fields.values()) + [uid]

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        query = f"UPDATE users SET {set_clause} WHERE uid = %s RETURNING *;"
        cursor.execute(query, values)
        conn.commit()

        updated_row = cursor.fetchone()
        if updated_row is None:
            return jsonify({"error": "User not found"}), 404

        columns = [desc[0] for desc in cursor.description]
        updated_user = dict(zip(columns, updated_row))
        return jsonify(updated_user)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/getuser_by_googleid", methods=["POST"])
def get_or_create_user_by_googleid():
    data = request.get_json()
    google_id = data.get("google_id")
    email = data.get("email")

    if not google_id:
        return jsonify({"error": "Missing google_id"}), 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Try to find user
        cursor.execute("SELECT * FROM users WHERE google_id = %s;", (google_id,))
        row = cursor.fetchone()

        if row:
            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, row))
            return jsonify(user)

        # If not found, insert new user
        cursor.execute(
            "INSERT INTO users (google_id, email) VALUES (%s, %s) RETURNING *;",
            (google_id, email)
        )
       
        conn.commit()

        logging.info(f"New user created with google_id={google_id}")

        new_row = cursor.fetchone()
        columns = [desc[0] for desc in cursor.description]
        user = dict(zip(columns, new_row))
        return jsonify(user)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


@app.route("/get_config", methods=["POST"])
def get_config_for_user():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")

    # === Default fallback config (hardcoded) ===
    default_config = {
        "auth.check": "https://cryspprod3.quantag-it.com:444/api10/check_token_ready",
        "auth.start": "https://cryspprod3.quantag-it.com:444/api10/google-auth-start",
        "prepare.data": "https://cryspprod3.quantag-it.com:444/api2/public/prepareData",
        "submit.files": "https://cryspprod3.quantag-it.com:444/api2/public/submitFiles",
        "get.image": "https://cryspprod3.quantag-it.com:444/api2/public/getImage",
        "get.file": "https://cryspprod3.quantag-it.com:444/api2/public/getFile",
        "cudaq.run": "https://cryspprod3.quantag-it.com:444/api19/cudaq/run",
        "transpile": "https://cryspprod3.quantag-it.com:444/api15/transpile",
        "pyzx.optimize": "https://cryspprod3.quantag-it.com:444/api16/optimize",
        "pyzx.render": "https://cryspprod3.quantag-it.com:444/api16/render",
        "pyzx.render2": "https://cryspprod3.quantag-it.com:444/api16/rend",
        "ibmq.submit": "https://quantum.quantag-it.com/api5/submit_ibm_job",
        "zi.run": "https://cryspprod2.quantag-it.com:4043/api2/run",
        "qasm2qir": "https://api.quantag-it.com/qasm2qir",
        "circuit.web": "https://quantag-it.com/quantum/#/qcd?id=",
        "getuser.by_googleid": "https://quantum.quantag-it.com/api5/getuser_by_googleid",
        "get.config": "https://quantum.quantag-it.com/api5/get_config",
        "qvm.submit": "https://quantum.quantag-it.com/api5/qvm/submit"
    }

    # If no user_id = return default config immediately
    if not user_id:
        logging.warning("No user_id provided, returning default config")
        return jsonify(default_config), 200

    conn, cursor = None, None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT uc.ki, uc.val
            FROM users u
            JOIN user_config uc ON uc.set_id = u.config_set
            WHERE u.uid = %s;
        """, (user_id,))
        rows = cursor.fetchall()

        if not rows:
            logging.warning(f"No config found for user {user_id}, returning default")
            return jsonify(default_config), 200

        config_values = {ki: val for ki, val in rows}
        logging.warning(f"Sent config for user {user_id}..")
        return jsonify(config_values), 200

    except Exception as e:
        logging.error(f"DB error in /get_config: {e}, returning default config")
        return jsonify(default_config), 200

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# ===== 1) Helper to submit IBM job (factored out of the route) =====
def _submit_ibm_job_core(job_uid: str, qasm_b64: str, user_id: str, token: str, inst: str, back: str):
    if not qasm_b64:
        return 400, {"error": "Missing 'qasm' field"}
    if not user_id:
        return 400, {"error": "Missing 'user_id' field"}
    if not token:
        return 400, {"error": "Missing 'token' field"}
    if not inst or not back:
        return 400, {"error": "Missing instance or backend"}

    try:
        # Decode and parse QASM
        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        logging.info(f"received QASM (len={len(qasm_str)})")
        qc = qasm3_loads(qasm_str)

        # Save account and connect
        QiskitRuntimeService.save_account(
            token=token,
            instance=inst,
            set_as_default=True,
            overwrite=True
        )

        service = QiskitRuntimeService()
        backend = service.backend(name=back, instance=inst)

        # Transpile and submit
        tqc = transpile(qc, backend=backend)
        sampler = SamplerV2(backend)
        job = sampler.run([tqc])
        job_id = job.job_id()

        # Store in DB
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        logging.info(f"[DB] update_job_info: job_id={job_id}, uid={job_uid}")
        cursor.execute(
            """
            UPDATE jobs
            SET job_id = %s,
                qpu = %s
            WHERE uid = %s;
            """,
            (job_id, back, job_uid)
        )        

        # Update token in users table
        cursor.execute(
            """
            UPDATE users
            SET token = %s
            WHERE uid = %s;
            """,
            (token, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return 200, {"message": "Job submitted", "job_id": job_id}

    except Exception as e:
        logging.error(f"IBM job submit failed: {repr(e)}")
        logging.error(traceback.format_exc())
        return 500, {"error": str(e)}


# ===== 2) Keep the old route, but forward to the helper =====
@app.route("/submit_ibm_job", methods=["POST"])
def submit_ibm_job():
    data = request.get_json() or {}
    qasm_b64 = data.get("qasm")
    user_id = data.get("user_id")
    token = data.get("token")
    inst = data.get("instance")
    back = data.get("backend")

    status, payload = _submit_ibm_job_core(qasm_b64, user_id, token, inst, back)
    return jsonify(payload), status

# --- helper (put near other DB helpers) ---
def _delete_job_owned_by(user_id: str, job_uid: str) -> tuple[int, dict]:
    conn = cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        # verify ownership
        cursor.execute("SELECT 1 FROM jobs WHERE uid = %s AND user_id = %s;", (job_uid, user_id))
        if cursor.fetchone() is None:
            return 404, {"error": "Job not found for this user"}
        # delete
        cursor.execute("DELETE FROM jobs WHERE uid = %s;", (job_uid,))
        conn.commit()
        return 204, {}
    except Exception as e:
        return 500, {"error": str(e)}
    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- NEW: DELETE /qvm/job/<job_uid> (used by VS Code) ---
@app.route("/qvm/job/<job_uid>", methods=["DELETE"])
def qvm_delete_job(job_uid: str):
    # 1) auth via API key (same style as other /qvm/* endpoints)
    api_key = request.headers.get("X-API-Key") or request.args.get("apikey")
    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"error": "Invalid or missing API key"}), 403

    # 2) delete if owned by this user
    status, payload = _delete_job_owned_by(user_id, job_uid)
    if status == 204:
        # No content on success (panel accepts 204 or 200)
        return ("", 204)
    return jsonify(payload), status


@app.route("/del_job", methods=["POST"])
def delete_job():
    data = request.get_json()
    user_id = data.get("user_id")
    job_uid = data.get("job_id")  # This is your internal job UID

    if not user_id or not job_uid:
        return jsonify({"error": "Missing user_id or job_id"}), 400

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Optional: check that job exists and belongs to the user
        cursor.execute("SELECT * FROM jobs WHERE uid = %s AND user_id = %s;", (job_uid, user_id))
        if not cursor.fetchone():
            return jsonify({"error": "Job not found for this user"}), 404

        # Delete the job
        cursor.execute("DELETE FROM jobs WHERE uid = %s;", (job_uid,))
        conn.commit()

        return jsonify({"message": "Job deleted"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()

@app.route("/qvm/run", methods=["POST"])
def qvm_run():
    data = request.get_json(silent=True) or {}

    api_key = data.get("apikey") or request.headers.get("X-API-Key")
    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"error": "Invalid or missing API key"}), 403

    qasm = data.get("qasm")
    shots = int(data.get("shots", 1024))
    backend_type = data.get("backend", "cudaq")

    if not qasm:
        return jsonify({"error": "qasm is required"}), 400

    node_b_url = "https://cloud.quantag-it.com/api1/run"
    payload = {"qasm_b64": qasm, "shots": shots}

    try:
        logging.info(f"Forwarding job to Node B at {node_b_url}, shots={shots}, qasm_size={len(qasm)} bytes")
        resp = requests.post(node_b_url, json=payload, timeout=60)

        # Log raw response
        logging.info(f"Node B response status: {resp.status_code}")
        logging.debug(f"Node B response text: {resp.text[:500]}...")

        # Try to parse JSON always
        try:
            node_b_result = resp.json()
        except Exception:
            node_b_result = {"error": resp.text.strip()}

        if resp.status_code != 200:
            return jsonify({
                "error": "QVM node error",
                "details": node_b_result
            }), resp.status_code

    except requests.RequestException as e:
        logging.error(f"Error forwarding to Node B: {e}")
        return jsonify({"error": f"QVM node unreachable: {e}"}), 502

    # Success case
    return jsonify({
        "user_id": user_id,
        "backend": backend_type,
        "shots": shots,
        "results": node_b_result
    }), 200



@app.route("/users", methods=["GET"])
def users_endpoint():
    return jsonify(get_users())

if __name__ == "__main__":
    app.run(debug=True, port=config.get("flask_port", 5000))

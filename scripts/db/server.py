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
        "ibmq.submit": "https://quantum.quantag-it.com/api5/submit_ibm_job",
        "zi.run": "https://cryspprod2.quantag-it.com:4043/api2/run",
        "qasm2qir": "https://api.quantag-it.com/qasm2qir",
        "circuit.web": "https://quantag-it.com/quantum/#/qcd?id=",
        "getuser.by_googleid": "https://quantum.quantag-it.com/api5/getuser_by_googleid",
        "get.config": "https://quantum.quantag-it.com/api5/get_config"
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



@app.route("/submit_ibm_job", methods=["POST"])
def submit_ibm_job():
    data = request.get_json()
    qasm_b64 = data.get("qasm")
    user_id = data.get("user_id")
    token = data.get("token")
    inst = data.get("instance")
    back = data.get("backend")

    if not qasm_b64:
        logging.error("missing 'qasm' field in request")
        return jsonify({"error": "Missing 'qasm' field"}), 400

    if not user_id:
        logging.error("missing 'user_id' field in request")
        return jsonify({"error": "Missing 'user_id' field"}), 400

    if not token:
        logging.error("missing 'token' field in request")
        return jsonify({"error": "Missing 'token' field"}), 400

    if not inst or not back:
        logging.error("missing some required field")
        return jsonify({"error": "Missing instance or backend"}), 400


    try:
        # Decode and parse QASM
        qasm_str = base64.b64decode(qasm_b64).decode("utf-8")
        logging.info(f"received QASM: {qasm_str}")
        qc = qasm3_loads(qasm_str)

        logging.info(f"Loaded QASM")
        # Save account and connect
        QiskitRuntimeService.save_account(
            token=token,
            instance=inst,
#            name="myacc",
            set_as_default=True,
            overwrite=True
        )

        # Connect to IBM backend
        logging.info(f"Connecting to IBM service..")
        service = QiskitRuntimeService()
        logging.info(f"Connecting to IBM backend..")
        backend = service.backend(name=back, instance=inst)
        logging.info(f"Connected to backend: {back}")

        # Transpile and submit job
        tqc = transpile(qc, backend=backend)
        sampler = SamplerV2(backend)
        job = sampler.run([tqc])
        job_id = job.job_id()

        # Store in DB
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (job_id, user_id, submitted_at, input, instance, qpu)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (job_id, user_id, datetime.utcnow(), qasm_str, inst, back)
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

        return jsonify({"message": "Job submitted", "job_id": job_id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

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

    # 1) Validate API key
    api_key = data.get("apikey") or request.headers.get("X-API-Key")
    user_id = validate_api_key(api_key)
    if not user_id:
        return jsonify({"error": "Invalid or missing API key"}), 403

    # 2) Extract circuit info
    qasm = data.get("qasm")
    shots = int(data.get("shots", 1024))
    backend_type = data.get("backend", "cudaq")

    if not qasm:
        return jsonify({"error": "qasm is required"}), 400

    # 3) Forward request to Node B
    try:
        node_b_url = "https://cloud.quantag-it.com/api1/run"
        payload = {"qasm_b64": qasm, "shots": shots}
        resp = requests.post(node_b_url, json=payload, timeout=60)
        resp.raise_for_status()
        node_b_result = resp.json()
    except Exception as e:
        return jsonify({"error": f"QVM node unreachable: {e}"}), 502

    # 4) Return Node B result + job metadata
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

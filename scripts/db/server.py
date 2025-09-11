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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__)

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

@app.route("/users", methods=["GET"])
def users_endpoint():
    return jsonify(get_users())

if __name__ == "__main__":
    app.run(debug=True, port=config.get("flask_port", 5000))

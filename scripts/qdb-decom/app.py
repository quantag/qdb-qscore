from flask import Flask, request, jsonify
import base64
import logging
import datetime
import os
import sys
import subprocess

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(filename='logs/app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": 0}), 200

@app.route("/dec", methods=["POST"])
def dec():
    try:
        data = request.get_json(force=True)
        if not data or "src" not in data:
            return jsonify({"status": 2, "err": "Missing 'src' field"}), 200

        # Decode source code
        src_b64 = data["src"]
        decoded_bytes = base64.b64decode(src_b64)
        decoded_text = decoded_bytes.decode("utf-8", errors="replace")

        logging.info(f"Incoming script:\n{decoded_text}")

        # Optional env parameter: folder of venv, for example "../.venv"
        env_folder = data.get("env")

        # --------------------------------------------------------------
        # Case 1: no env provided -> keep old behavior with in-process exec
        # --------------------------------------------------------------
        if not env_folder:
            logging.info("No env provided, using in-process exec() (legacy mode)")

            loc = {}
            exec(decoded_bytes, globals(), loc)
            result = loc.get("code777")

            if result is not None:
                encoded_result = base64.b64encode(str(result).encode()).decode()
                logging.info(f"Execution result: {result}")
                return jsonify({"status": 0, "res": encoded_result}), 200
            else:
                logging.error("Expected result was not found (code777 is None)")
                return jsonify(
                    {"status": 1, "err": "Expected result was not found"}
                ), 200

        # --------------------------------------------------------------
        # Case 2: env provided -> run code in a separate python from this venv
        # --------------------------------------------------------------
        # env_folder may be relative, for example "../.venv"
        venv_path = os.path.abspath(env_folder)
        logging.info(f"env provided: {env_folder}, resolved venv: {venv_path}")

        # Check that venv folder exists
        if not os.path.isdir(venv_path):
            err = f"Env folder does not exist: {venv_path}"
            logging.error(err)
            return jsonify({"status": 2, "err": err}), 200

        python_bin = os.path.join(venv_path, "bin", "python")
        logging.info(f"Using python interpreter: {python_bin}")

        # Check that python interpreter exists inside venv
        if not os.path.exists(python_bin):
            err = (
                f"Python interpreter not found in env '{env_folder}' "
                f"(expected {python_bin})"
            )
            logging.error(err)
            return jsonify({"status": 2, "err": err}), 200

        # Save original script to file (for logging / debugging)
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        script_filename = f"scripts/script{timestamp}.py"
        os.makedirs(os.path.dirname(script_filename), exist_ok=True)
        with open(script_filename, "w", encoding="utf-8") as f:
            f.write(decoded_text)

        # Build wrapper code:
        # - execute original script
        # - then read globals()["code777"] and write it to stdout
        wrapper_code = (
            decoded_text
            + "\n\n"
            "import sys\n"
            "result = globals().get('code777', None)\n"
            "sys.stdout.write('' if result is None else str(result))\n"
        )

        proc = subprocess.run(
            [python_bin, "-"],
            input=wrapper_code,
            text=True,
            capture_output=True,
            timeout=30,
        )

        if proc.returncode != 0:
            err = (
                f"Python exited with code {proc.returncode}: "
                f"{proc.stderr.strip()}"
            )
            logging.error(err)
            return jsonify({"status": 2, "err": err}), 200

        result_text = proc.stdout
        if not result_text:
            logging.error(
                "Expected result was not found (code777 missing or empty in env mode)"
            )
            return jsonify(
                {"status": 1, "err": "Expected result was not found"}
            ), 200

        encoded_result = base64.b64encode(result_text.encode()).decode()
        logging.info(f"Execution result (env mode): {result_text}")
        return jsonify({"status": 0, "res": encoded_result}), 200

    except Exception as e:
        logging.exception("An error occurred in /dec")
        return jsonify({"status": 2, "err": str(e)}), 200


@app.route('/dec2', methods=['POST'])
def dec2():
    try:
        data = request.json
        decodedSrc = base64.b64decode(data['src'])
        logging.info(f"Incoming script: {decodedSrc.decode()}")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        script_filename = f"scripts/script{timestamp}.py"
        with open(script_filename, 'w') as f:
            f.write(decodedSrc.decode())

        loc = {}
        exec(decodedSrc, globals(), loc)
        result = loc.get('code777')
        if result is not None:
            encoded_result = base64.b64encode(str(result).encode()).decode()
            logging.info(f"Execution result: {result}")
            return jsonify({'status':0,'res': encoded_result})
        else:
            logging.error('Expected result was not found')
            return jsonify({'status':1,'err':'Expected result was not found'})
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({'status':2,'err': str(e)})

if __name__ == '__main__':
    app.run(port=5000)
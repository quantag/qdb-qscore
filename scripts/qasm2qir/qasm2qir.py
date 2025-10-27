from flask import Flask, request, jsonify
from qbraid_qir.qasm3 import qasm3_to_qir
from flask_cors import CORS
import base64
import logging
import traceback
import sys

# --------------------------------------------------------------------
# Logging setup
# --------------------------------------------------------------------
logger = logging.getLogger("qasm2qir")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(handler)

# --------------------------------------------------------------------
# Flask app
# --------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    logger.info("Health check requested")
    return jsonify({"status": 0}), 200


@app.route("/qasm2qir", methods=["POST"])
def create_resource():
    logger.info("Received POST /qasm2qir")
    try:
        data = request.get_json(silent=True)
        if not data or "qasm" not in data:
            msg = "Missing 'qasm' in JSON"
            logger.error(msg)
            return jsonify({"status": 1, "error": msg}), 400

        fmt = (data.get("format") or "text").lower()
        logger.info(f"Requested format: {fmt}")

        # Decode QASM
        qasm_bytes = base64.b64decode(data["qasm"])
        qasm3_code = qasm_bytes.decode("utf-8", errors="replace")
        logger.debug("----- BEGIN QASM INPUT -----")
        logger.debug(qasm3_code)
        logger.debug("----- END QASM INPUT -----")

        # Convert QASM  QIR
        logger.info("Converting QASM to QIR...")
        qir_output = qasm3_to_qir(qasm3_code)
        logger.info("Conversion complete")

        # Determine format
        if fmt == "bitcode":
            if hasattr(qir_output, "bitcode"):
                qir_bytes = qir_output.bitcode
            else:
                msg = "QIR module has no .bitcode() method"
                logger.error(msg)
                return jsonify({"status": 2, "error": msg}), 500
        else:
            qir_bytes = str(qir_output).encode("utf-8")

        qir_base64 = base64.b64encode(qir_bytes).decode("utf-8")
        logger.info(f"QIR generated ({len(qir_bytes)} bytes)")
        return jsonify({"status": 0, "format": fmt, "qir": qir_base64}), 200

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Exception during processing:\n" + tb)
        # return actual message and trace
        return jsonify({
            "status": 3,
            "error": str(e),
            "trace": tb
        }), 500


if __name__ == "__main__":
    logger.info("Starting QASM QIR service on port 5007...")
    app.run(host="0.0.0.0", port=5007, debug=False)

import os
import base64
import tempfile
import subprocess
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

# Config via env (with safe defaults)
QBIN_COMPILE = os.getenv("QBIN_COMPILE", "qbin-compile")
QBIN_DECOMPILE = os.getenv("QBIN_DECOMPILE", "qbin-decompile")
MAX_UPLOAD_BYTES = int(os.getenv("QBIN_MAX_UPLOAD_BYTES", "10485760"))  # 10 MiB
DEFAULT_TIMEOUT_SEC = int(os.getenv("QBIN_TIMEOUT_SEC", "20"))

def b64_decode_field(data_b64: str) -> bytes:
    try:
        return base64.b64decode(data_b64, validate=True)
    except Exception:
        # try non-strict to be forgiving
        return base64.b64decode(data_b64)

def b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")

def run_tool(args, timeout_sec):
    start = time.time()
    proc = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_sec,
        check=False
    )
    elapsed_ms = int(1000 * (time.time() - start))
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace"), elapsed_ms

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "compile": QBIN_COMPILE, "decompile": QBIN_DECOMPILE})

@app.route("/compile", methods=["POST"])
def compile_qasm_to_qbin():
    """
    JSON body:
    {
      "qasm_b64": "<base64 of .qasm text>",
      "timeout_sec": 20  (optional)
    }
    Response:
    { "qbin_b64": "...", "elapsed_ms": 123, "size_in": 1234, "size_out": 567 }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    body = request.get_json(silent=True) or {}
    qasm_b64 = body.get("qasm_b64")
    if not qasm_b64:
        return jsonify({"error": "Missing field qasm_b64"}), 400

    try:
        qasm_bytes = b64_decode_field(qasm_b64)
    except Exception as e:
        return jsonify({"error": f"Invalid base64 for qasm_b64: {e}"}), 400

    if len(qasm_bytes) > MAX_UPLOAD_BYTES:
        return jsonify({"error": f"Input too large: {len(qasm_bytes)} bytes, limit {MAX_UPLOAD_BYTES}"}), 413

    timeout_sec = int(body.get("timeout_sec", DEFAULT_TIMEOUT_SEC))

    with tempfile.TemporaryDirectory() as tmp:
        qasm_path = os.path.join(tmp, "in.qasm")
        qbin_path = os.path.join(tmp, "out.qbin")
        with open(qasm_path, "wb") as f:
            f.write(qasm_bytes)

        rc, out, err, elapsed_ms = run_tool([QBIN_COMPILE, qasm_path, "-o", qbin_path], timeout_sec)
        if rc != 0 or not os.path.exists(qbin_path):
            return jsonify({
                "error": "qbin-compile failed",
                "return_code": rc,
                "stdout": out,
                "stderr": err,
                "elapsed_ms": elapsed_ms
            }), 500

        with open(qbin_path, "rb") as f:
            qbin_bytes = f.read()

    return jsonify({
        "qbin_b64": b64_encode(qbin_bytes),
        "elapsed_ms": elapsed_ms,
        "size_in": len(qasm_bytes),
        "size_out": len(qbin_bytes)
    })

@app.route("/decompile", methods=["POST"])
def decompile_qbin_to_qasm():
    """
    JSON body:
    {
      "qbin_b64": "<base64 of .qbin bytes>",
      "timeout_sec": 20  (optional)
    }
    Response:
    { "qasm_b64": "...", "elapsed_ms": 123, "size_in": 567, "size_out": 1234 }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    body = request.get_json(silent=True) or {}
    qbin_b64 = body.get("qbin_b64")
    if not qbin_b64:
        return jsonify({"error": "Missing field qbin_b64"}), 400

    try:
        qbin_bytes = b64_decode_field(qbin_b64)
    except Exception as e:
        return jsonify({"error": f"Invalid base64 for qbin_b64: {e}"}), 400

    if len(qbin_bytes) > MAX_UPLOAD_BYTES:
        return jsonify({"error": f"Input too large: {len(qbin_bytes)} bytes, limit {MAX_UPLOAD_BYTES}"}), 413

    timeout_sec = int(body.get("timeout_sec", DEFAULT_TIMEOUT_SEC))

    with tempfile.TemporaryDirectory() as tmp:
        qbin_path = os.path.join(tmp, "in.qbin")
        qasm_path = os.path.join(tmp, "out.qasm")
        with open(qbin_path, "wb") as f:
            f.write(qbin_bytes)

        rc, out, err, elapsed_ms = run_tool([QBIN_DECOMPILE, qbin_path, "-o", qasm_path], timeout_sec)
        if rc != 0 or not os.path.exists(qasm_path):
            return jsonify({
                "error": "qbin-decompile failed",
                "return_code": rc,
                "stdout": out,
                "stderr": err,
                "elapsed_ms": elapsed_ms
            }), 500

        with open(qasm_path, "rb") as f:
            qasm_bytes = f.read()

    return jsonify({
        "qasm_b64": b64_encode(qasm_bytes),
        "elapsed_ms": elapsed_ms,
        "size_in": len(qbin_bytes),
        "size_out": len(qasm_bytes)
    })

if __name__ == "__main__":
    # For local dev only. Use a real WSGI/ASGI server in production.
    app.run(host="0.0.0.0", port=5039, debug=False)

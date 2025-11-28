import base64
import os
import tempfile
from flask import Flask, request, jsonify

from bqskit import compile as bq_compile, Circuit

app = Flask(__name__)

STATUS_OK = 0
STATUS_BAD_REQUEST = 1
STATUS_DECODE_ERROR = 2
STATUS_NOT_IMPLEMENTED = 3
STATUS_BQSKIT_ERROR = 4
STATUS_INTERNAL_ERROR = 5


def b64_to_text(b64_str: str) -> str:
    raw = base64.b64decode(b64_str, validate=True)
    return raw.decode("utf-8")


def text_to_b64(text: str) -> str:
    raw = text.encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def optimize_bqskit(qasm_in: str) -> str:
    """
    Logical-only optimization with BQSKit.
    Uses temp files for the most stable QASM IO.
    """
    in_path = None
    out_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".qasm", delete=False, encoding="utf-8"
        ) as f_in:
            in_path = f_in.name
            f_in.write(qasm_in)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".qasm", delete=False, encoding="utf-8"
        ) as f_out:
            out_path = f_out.name

        circuit = Circuit.from_file(in_path)
        opt_circuit = bq_compile(circuit)  # no hardware model -> logical-only
        opt_circuit.save(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            return f.read()

    finally:
        for p in (in_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


@app.route("/optimize", methods=["POST"])
def optimize():
    if not request.is_json:
        return jsonify({"status": STATUS_BAD_REQUEST, "src": ""}), 400

    data = request.get_json(silent=True) or {}

    # Validate src
    src_b64 = data.get("src")
    if not isinstance(src_b64, str):
        return jsonify({"status": STATUS_BAD_REQUEST, "src": ""}), 400

    # Validate type
    opt_type = data.get("type")
    if not isinstance(opt_type, int):
        return jsonify({"status": STATUS_BAD_REQUEST, "src": ""}), 400

    # Decode base64
    try:
        qasm_in = b64_to_text(src_b64)
    except Exception:
        return jsonify({"status": STATUS_DECODE_ERROR, "src": ""}), 400

    # Dispatch by type
    try:
        if opt_type == 0:
            qasm_out = optimize_bqskit(qasm_in)
            return jsonify({"status": STATUS_OK, "src": text_to_b64(qasm_out)}), 200
        else:
            # Placeholder for future optimizers
            return jsonify({"status": STATUS_NOT_IMPLEMENTED, "src": ""}), 501

    except Exception:
        # Any optimizer failure falls here
        return jsonify({"status": STATUS_BQSKIT_ERROR, "src": ""}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8089"))
    app.run(host="127.0.0.1", port=port)

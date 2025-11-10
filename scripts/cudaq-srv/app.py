import os
import base64
import json
import sys
import tempfile
import importlib.util
from flask import Flask, request, jsonify
import cudaq
import subprocess
import psutil
from flask_cors import CORS

VERSION = "1.0.0"

app = Flask(__name__)
CORS(app)


# Default target (can be overridden in request)
DEFAULT_TARGET = os.environ.get("CUDAQ_TARGET", "qpp-cpu")

def save_to_tempfile(source_code: str, suffix=".py"):
    """Save code to a temporary file and return path."""
    tmp = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False)
    tmp.write(source_code)
    tmp_path = tmp.name
    tmp.close()
    return tmp_path

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

@app.route("/cudaq/ir", methods=["POST"])
def get_ir():
    """
    Return MLIR IR of a CUDA-Q kernel.
    Request:
    { "source_b64": "...", "lang": "python", "kernel": "bell" }
    """
    try:
        body = request.get_json(force=True)
        src_b64 = body.get("source_b64")
        kernel_name = body.get("kernel", "kernel")
        lang = body.get("lang", "python")

        if not src_b64:
            return jsonify({"error": "Missing source_b64"}), 400

        if lang != "python":
            return jsonify({"error": "Only python supported"}), 400

        source_code = base64.b64decode(src_b64).decode("utf-8")
        kernel = load_python_kernel(source_code, kernel_name)

        if not kernel:
            return jsonify({"error": f"Kernel {kernel_name} not found"}), 400

        ir_text = cudaq.get_ir(kernel)
        return jsonify({"ir": ir_text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/cudaq/qasm", methods=["POST"])
def to_qasm():
    """
    Convert CUDA-Q source to OpenQASM 3.0.
    Request JSON:
    {
      "source_b64": "<base64 python/cpp source>",
      "lang": "python" | "cpp"
    }
    """
    try:
        body = request.get_json(force=True)
        src_b64 = body.get("source_b64")
        lang = body.get("lang", "python")

        if not src_b64:
            return jsonify({"error": "Missing source_b64"}), 400

        source_code = base64.b64decode(src_b64).decode("utf-8")

        suffix = ".py" if lang == "python" else ".cpp"
        tmp_path = save_to_tempfile(source_code, suffix)

        # Run q-convert (must be installed and in PATH)
        cmd = ["q-convert", "--from", "cudaq", "--to", "qasm3", tmp_path]
        sys.stdout.write("[CMD] " + " ".join(cmd) + "\n")
        sys.stdout.flush()

        result = subprocess.run(
            cmd, capture_output=True, text=True
        )

        if result.returncode != 0:
            return jsonify({
                "error": "q-convert failed",
                "stderr": result.stderr
            }), 500

        qasm = result.stdout

        return jsonify({
            "qasm": qasm,
            "lang": lang
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def load_python_kernel(source_code: str, kernel_name: str):
    """
    Save source_code to a temporary file and import it as a module.
    This avoids the 'could not get source code' error from @cudaq.kernel.
    """
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmp:
            tmp.write(source_code)
            tmp_path = tmp.name

        spec = importlib.util.spec_from_file_location("user_module", tmp_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, kernel_name):
            return getattr(module, kernel_name)

        # Fallback: find any CUDA-Q kernel in the module
        for name in dir(module):
            obj = getattr(module, name)
            if hasattr(obj, "__cudaq_kernel__"):
                sys.stdout.write(f"[INFO] Auto-detected kernel: {name}\n")
                sys.stdout.flush()
                return obj

        return None
    except Exception as e:
        sys.stderr.write(f"[ERROR] load_python_kernel failed: {e}\n")
        sys.stderr.flush()
        raise


@app.route("/cudaq/run", methods=["POST"])
def run_kernel():
    """
    Run a CUDA-Q kernel.
    Request JSON:
    {
      "source_b64": "<base64 of Python source>",
      "lang": "python",
      "kernel": "bell",
      "target": "nvidia" | "qpp-cpu" | "density-matrix-cpu" | "ionq" | "quantinuum",
      "shots": 1000,
      "state": true|false
    }
    """
    try:
        body = request.get_json(force=True)
        sys.stdout.write("[REQUEST] " + json.dumps(body) + "\n")
        sys.stdout.flush()

        src_b64 = body.get("source_b64")
        lang = body.get("lang", "python")
        kernel_name = body.get("kernel", "kernel")
        target = body.get("target", DEFAULT_TARGET)
        shots = int(body.get("shots", 1000))
        want_state = bool(body.get("state", False))

        if not src_b64:
            return jsonify({"error": "Missing source_b64"}), 400

        source_code = base64.b64decode(src_b64).decode("utf-8")

        # --- Set target ---
        try:
            cudaq.set_target(target)
        except Exception as e:
            sys.stderr.write(f"[ERROR] Failed to set target {target}: {e}\n")
            sys.stderr.flush()
            return jsonify({"error": f"Invalid target {target}"}), 400

        # --- Load kernel ---
        if lang == "python":
            kernel = load_python_kernel(source_code, kernel_name)
            if not kernel:
                return jsonify({"error": f"Kernel {kernel_name} not found"}), 400
        elif lang == "cpp":
            return jsonify({"error": "C++ CUDA-Q not supported yet"}), 501
        else:
            return jsonify({"error": "Unsupported language"}), 400

        # --- Run kernel ---
        try:
            result = cudaq.sample(kernel, shots_count=shots)
        except Exception as e:
            sys.stderr.write("[ERROR] cudaq.sample failed: " + str(e) + "\n")
            sys.stderr.flush()
            return jsonify({"error": "cudaq.sample failed: " + str(e)}), 500

        payload = {"counts": dict(result)}

        if want_state:
            try:
                state = cudaq.get_state(kernel)
                payload["statevector_amplitudes"] = [str(a) for a in state]
            except Exception as e:
                sys.stderr.write("[WARN] get_state failed: " + str(e) + "\n")
                sys.stderr.flush()

        sys.stdout.write("[RESPONSE] " + json.dumps(payload) + "\n")
        sys.stdout.flush()
        return jsonify(payload)

    except Exception as e:
        sys.stderr.write("[ERROR] " + str(e) + "\n")
        sys.stderr.flush()
        return jsonify({"error": str(e)}), 500


@app.route("/cudaq/targets", methods=["GET"])
def list_targets():
    """List available CUDA-Q targets (simulators + hardware)."""
    try:
        targets = cudaq.get_targets()
        return jsonify({"targets": targets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cudaq/selftest", methods=["GET"])
def selftest():
    """Run a built-in Bell kernel to verify CUDA-Q works."""
    try:
        @cudaq.kernel
        def bell():
            q = cudaq.qvector(2)
            cudaq.h(q[0])
            cudaq.cx(q[0], q[1])

        cudaq.set_target(DEFAULT_TARGET)
        result = cudaq.sample(bell, shots_count=100)
        return jsonify({"counts": dict(result)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5040))
    app.run(host="0.0.0.0", port=port)

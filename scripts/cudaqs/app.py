import os
import base64
import json
from flask import Flask, request, jsonify
import cudaq

app = Flask(__name__)

# Default target (can be overridden in request)
DEFAULT_TARGET = os.environ.get("CUDAQ_TARGET", "qpp-cpu")

@app.route("/cudaq/run", methods=["POST"])
def run_kernel():
    """
    Run a CUDA-Q kernel.
    Request JSON:
    {
      "source_b64": "<base64 of Python/C++ source>",
      "lang": "python" | "cpp",
      "kernel": "bell",
      "target": "nvidia" | "qpp-cpu" | "density-matrix-cpu" | "ionq" | "quantinuum",
      "shots": 1000,
      "state": true|false
    }
    """
    try:
        body = request.get_json(force=True)

        src_b64 = body.get("source_b64")
        lang = body.get("lang", "python")
        kernel_name = body.get("kernel", "kernel")
        target = body.get("target", DEFAULT_TARGET)
        shots = int(body.get("shots", 1000))
        want_state = bool(body.get("state", False))

        if not src_b64:
            return jsonify({"error": "Missing source_b64"}), 400

        source_code = base64.b64decode(src_b64).decode("utf-8")

        # --- Set target (GPU sim, CPU sim, or hardware) ---
        cudaq.set_target(target)

        # --- Load kernel ---
        if lang == "python":
            # Execute Python source code so @cudaq.kernel functions are defined
            namespace = {}
            exec(source_code, namespace, namespace)

            if kernel_name not in namespace:
                return jsonify({"error": f"Kernel {kernel_name} not found"}), 400

            kernel = namespace[kernel_name]

        elif lang == "cpp":
            # For C++ we would need to call nvq++ compiler or q-convert.
            # Placeholder: not supported yet
            return jsonify({"error": "C++ CUDA-Q not yet supported in this service"}), 501

        else:
            return jsonify({"error": "Unsupported language"}), 400

        # --- Run kernel ---
        result = cudaq.sample(kernel, shots_count=shots)

        payload = {"counts": dict(result)}

        if want_state:
            state = cudaq.get_state(kernel)
            # Convert complex amplitudes to strings for JSON
            payload["statevector_amplitudes"] = [str(a) for a in state]

        return jsonify(payload)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cudaq/targets", methods=["GET"])
def list_targets():
    """
    List available CUDA-Q targets (simulators + hardware).
    """
    try:
        targets = cudaq.get_targets()
        return jsonify({"targets": targets})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5040))
    app.run(host="0.0.0.0", port=port)

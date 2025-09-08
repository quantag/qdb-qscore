from flask import Flask, request, jsonify
import cudaq
import math
import sys
import json
import base64
import os
from datetime import datetime
from typing import Tuple, Dict
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# -------------------------
# Helpers for base64 I/O
# -------------------------
def b64e(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")

def b64d(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


# -------------------------
# Logging helper
# -------------------------
def log_qasm(qasm_text: str, prefix: str) -> str:
    """Save QASM text into logs/ with timestamp, return path, and print."""
    os.makedirs("logs", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    fname = f"logs/{prefix}_{ts}.qasm"
    with open(fname, "w", encoding="ascii", errors="ignore") as f:
        f.write(qasm_text)

    # log to console
    print(f"[LOG] {prefix} request saved to {fname} ({len(qasm_text)} chars)")

    return fname

# -------------------------
# Angle parsing
# -------------------------
def parse_angle(expr: str) -> float:
    expr = expr.strip().replace(";", "")
    if expr == "pi":
        return math.pi
    if expr.startswith("pi/"):
        denom = float(expr.split("/")[1])
        return math.pi / denom
    if "*" in expr and "pi" in expr:
        # e.g. "3*pi/8"
        parts = expr.split("*")
        factor = float(parts[0])
        rest = parts[1]
        if "/" in rest:
            denom = float(rest.split("/")[1])
            return factor * math.pi / denom
        return factor * math.pi
    if "/" in expr and "pi" in expr:
        num, denom = expr.split("/")
        num = num.replace("pi", str(math.pi))
        return float(num) / float(denom)
    try:
        return float(expr)
    except Exception:
        raise ValueError(f"Unsupported angle format: {expr}")

# -------------------------
# Parser -> executable kernel
# -------------------------
def qasm_to_kernel(qasm: str) -> Tuple["cudaq.Kernel", int]:
    kernel = cudaq.make_kernel()
    q = None
    creg_size = 0

    for line in qasm.splitlines():
        line = line.strip()
        if (not line
            or line.startswith("//")
            or line.startswith("OPENQASM")
            or line.startswith("include")):
            continue
        #print(f"[DEBUG] parsing line: {line}", file=sys.stderr)

        if line.startswith("qreg"):
            n = int(line.split("[")[1].split("]")[0])
            q = kernel.qalloc(n)
        #    print(f"[DEBUG] allocated qreg with {n} qubits", file=sys.stderr)

        elif line.startswith("creg"):
            creg_size = int(line.split("[")[1].split("]")[0])

        elif line.startswith("h "):
            idx = int(line.split("[")[1].split("]")[0])
            kernel.h(q[idx])

        elif line.startswith("x "):
            idx = int(line.split("[")[1].split("]")[0])
            kernel.x(q[idx])

        elif line.startswith("cx"):
            parts = line.replace(";", "").split(",")
            c1 = int(parts[0].split("[")[1].split("]")[0])
            c2 = int(parts[1].split("[")[1].split("]")[0])
            kernel.cx(q[c1], q[c2])

        elif line.startswith("rz"):
            angle = line[line.find("(")+1:line.find(")")]
            idx = int(line.split("[")[1].split("]")[0])
            kernel.rz(parse_angle(angle), q[idx])

        elif line.startswith("cu1"):
            line2 = line.replace(";", "")
            angle = line2[line2.find("(")+1:line2.find(")")]
            ctrl_idx = int(line2.split("[")[1].split("]")[0])
            tgt_idx  = int(line2.split("[")[2].split("]")[0])
            theta = parse_angle(angle)
            try:
                kernel.cp(theta, q[ctrl_idx], q[tgt_idx])
            except Exception:
                kernel.cr1(theta, q[ctrl_idx], q[tgt_idx])

        elif line.startswith("barrier"):
            continue

        elif line.startswith("measure"):
            continue

        else:
            raise ValueError(f"Unsupported or unrecognized statement: {line}")

    return kernel, creg_size

# -------------------------
# Parser -> C++ kernel code (string)
# -------------------------
def qasm_to_kernel_cpp(qasm: str) -> str:
    lines = []
    lines.append("#include <cudaq.h>")
    lines.append("")
    lines.append("cudaq::kernel auto make_kernel_from_qasm() {")
    creg_size = 0

    for raw in qasm.splitlines():
        line = raw.strip()
        if (not line
            or line.startswith("//")
            or line.startswith("OPENQASM")
            or line.startswith("include")):
            continue

        if line.startswith("qreg"):
            n = int(line.split("[")[1].split("]")[0])
            lines.append(f"    auto q = cudaq::qalloc({n});")

        elif line.startswith("creg"):
            creg_size = int(line.split("[")[1].split("]")[0])

        elif line.startswith("h "):
            idx = int(line.split("[")[1].split("]")[0])
            lines.append(f"    h(q[{idx}]);")

        elif line.startswith("x "):
            idx = int(line.split("[")[1].split("]")[0])
            lines.append(f"    x(q[{idx}]);")

        elif line.startswith("cx"):
            parts = line.replace(";", "").split(",")
            c1 = int(parts[0].split("[")[1].split("]")[0])
            c2 = int(parts[1].split("[")[1].split("]")[0])
            lines.append(f"    cx(q[{c1}], q[{c2}]);")

        elif line.startswith("rz"):
            angle_expr = line[line.find("(")+1:line.find(")")]
            idx = int(line.split("[")[1].split("]")[0])
            theta = parse_angle(angle_expr)
            lines.append(f"    rz({theta}, q[{idx}]);")

        elif line.startswith("cu1"):
            l2 = line.replace(";", "")
            angle_expr = l2[l2.find("(")+1:l2.find(")")]
            ctrl_idx = int(l2.split("[")[1].split("]")[0])
            tgt_idx  = int(l2.split("[")[2].split("]")[0])
            theta = parse_angle(angle_expr)
            lines.append(f"    cp({theta}, q[{ctrl_idx}], q[{tgt_idx}]);")

        elif line.startswith("barrier"):
            continue

        elif line.startswith("measure"):
            continue

        else:
            raise ValueError(f"Unsupported or unrecognized statement: {line}")

    lines.append("}")
    lines.append(f"// creg_size_hint = {creg_size}")
    return "\n".join(lines)


# -------------------------
# Parser -> Python kernel code (string)
# -------------------------
def qasm_to_kernel_code(qasm: str) -> str:
    lines = []
    n_qubits = None
    body = []
    body.append("kernel = cudaq.make_kernel()")
    body.append("q = None")
    creg_size = 0

    for raw in qasm.splitlines():
        line = raw.strip()
        if (not line
            or line.startswith("//")
            or line.startswith("OPENQASM")
            or line.startswith("include")):
            continue

        if line.startswith("qreg"):
            n = int(line.split("[")[1].split("]")[0])
            n_qubits = n
            body.append(f"q = kernel.qalloc({n})")

        elif line.startswith("creg"):
            creg_size = int(line.split("[")[1].split("]")[0])

        elif line.startswith("h "):
            idx = int(line.split("[")[1].split("]")[0])
            body.append(f"kernel.h(q[{idx}])")

        elif line.startswith("x "):
            idx = int(line.split("[")[1].split("]")[0])
            body.append(f"kernel.x(q[{idx}])")

        elif line.startswith("cx"):
            parts = line.replace(";", "").split(",")
            c1 = int(parts[0].split("[")[1].split("]")[0])
            c2 = int(parts[1].split("[")[1].split("]")[0])
            body.append(f"kernel.cx(q[{c1}], q[{c2}])")

        elif line.startswith("rz"):
            angle_expr = line[line.find("(")+1:line.find(")")]
            idx = int(line.split("[")[1].split("]")[0])
            theta = parse_angle(angle_expr)
            body.append(f"kernel.rz({theta}, q[{idx}])")

        elif line.startswith("cu1"):
            l2 = line.replace(";", "")
            angle_expr = l2[l2.find("(")+1:l2.find(")")]
            ctrl_idx = int(l2.split("[")[1].split("]")[0])
            tgt_idx  = int(l2.split("[")[2].split("]")[0])
            theta = parse_angle(angle_expr)
            body.append(f"try:\n    kernel.cp({theta}, q[{ctrl_idx}], q[{tgt_idx}])\nexcept Exception:\n    kernel.cr1({theta}, q[{ctrl_idx}], q[{tgt_idx}])")

        elif line.startswith("barrier"):
            continue

        elif line.startswith("measure"):
            continue

        else:
            raise ValueError(f"Unsupported or unrecognized statement: {line}")

    if n_qubits is None:
        raise ValueError("qreg declaration not found.")

    src = [
        "import cudaq",
        "",
        "def make_kernel_from_qasm() -> 'cudaq.Kernel':",
    ]
    src.extend(["    " + b for b in body])
    src.append("    return kernel")
    src.append(f"# creg_size_hint = {creg_size}")
    return "\n".join(src)

# -------------------------
# /run endpoint
# -------------------------
@app.route("/run", methods=["POST"])
def run_qasm():
    try:
        data = request.get_json(force=True) or {}
        qasm_b64 = data.get("qasm_b64")
        if not qasm_b64:
            return jsonify({"error": "qasm_b64 is required"}), 400

        shots_txt = "1000"
        if "shots_b64" in data and data["shots_b64"]:
            shots_txt = b64d(data["shots_b64"])
        shots = int(shots_txt)

        qasm = b64d(qasm_b64)

        # log input
        log_qasm(qasm, "run")

        kernel, creg_size = qasm_to_kernel(qasm)
        result = cudaq.sample(kernel, shots_count=shots)

        histogram: Dict[str, int] = {}
        for bitstring, count in result.items():
            if not isinstance(bitstring, str):
                bitstring = "".join(str(b) for b in bitstring)
            if creg_size and len(bitstring) < creg_size:
                bitstring = bitstring.zfill(creg_size)
            histogram[bitstring] = count

        payload = json.dumps({"histogram": histogram, "creg_size": creg_size})
        return jsonify({"result_b64": b64e(payload)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# /compile endpoint
# -------------------------
@app.route("/compile", methods=["POST"])
def compile_qasm():
    try:
        data = request.get_json(force=True) or {}
        qasm_b64 = data.get("qasm")
        if not qasm_b64:
            return jsonify({"error": "qasm is required"}), 400

        qasm = b64d(qasm_b64)
        target_type = (data.get("type") or "python").lower()

        # log input
        log_qasm(qasm, f"compile_{target_type}")

        #src = qasm_to_kernel_code(qasm)
        if target_type == "cpp":
            src = qasm_to_kernel_cpp(qasm)
            return jsonify({"output": b64e(src)})
        else:
            src = qasm_to_kernel_code(qasm)
            return jsonify({"output": b64e(src)})
        return jsonify({"output": b64e(src)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)

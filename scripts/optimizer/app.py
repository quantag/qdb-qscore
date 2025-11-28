import base64
import os
import sys
import tempfile
import traceback
import logging
from logging.handlers import RotatingFileHandler
import threading
import importlib

from flask import Flask, request, jsonify
from flask_cors import CORS

from bqskit import Circuit
from bqskit.compiler import Compiler
from bqskit.compiler.workflow import Workflow


# -----------------------------
# Flask app + CORS
# -----------------------------
app = Flask(__name__)
CORS(app)

# -----------------------------
# Status codes
# -----------------------------
STATUS_OK = 0
STATUS_BAD_REQUEST = 1
STATUS_DECODE_ERROR = 2
STATUS_NOT_IMPLEMENTED = 3
STATUS_BQSKIT_ERROR = 4
STATUS_INTERNAL_ERROR = 5


# -----------------------------
# Logging (default ./logs/)
# -----------------------------
def setup_logging():
    logger = logging.getLogger("optimizer")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    default_dir = "logs"
    default_file = os.path.join(default_dir, "optimizer.log")
    log_file = os.environ.get("LOG_FILE", default_file)

    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        ))
        logger.addHandler(fh)
        logger.info("File logging enabled at %s", log_file)
    except Exception as e:
        # Do not fail the service on logging errors.
        logger.warning("Could not enable file logging at %s: %s", log_file, str(e))

    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    ))
    logger.addHandler(sh)
    logger.info("Stderr logging enabled")

    return logger


logger = setup_logging()
logger.info("Optimizer service module loaded OK.")


# -----------------------------
# Base64 helpers
# -----------------------------
def b64_to_text(b64_str: str) -> str:
    raw = base64.b64decode(b64_str, validate=True)
    return raw.decode("utf-8")


def text_to_b64(text: str) -> str:
    raw = text.encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


# -----------------------------
# QASM measurement handling
# -----------------------------
def split_unitary_and_measurements(qasm_text: str):
    """
    Splits QASM into:
      - unitary_lines: all non-measure lines (keeps headers, regs, gates)
      - meas_lines: all lines starting with "measure "
      - trailing_barrier_lines: barriers at the very end (kept to append before measures)
    """
    lines = [ln.rstrip("\n") for ln in qasm_text.splitlines()]

    meas_lines = []
    non_meas_lines = []
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("measure "):
            meas_lines.append(ln)
        else:
            non_meas_lines.append(ln)

    trailing_barrier_lines = []
    while non_meas_lines:
        s = non_meas_lines[-1].strip()
        if s.startswith("barrier "):
            trailing_barrier_lines.insert(0, non_meas_lines.pop())
        else:
            break

    unitary_lines = non_meas_lines
    return unitary_lines, meas_lines, trailing_barrier_lines


def join_with_measurements(unitary_qasm: str, meas_lines, trailing_barrier_lines):
    out_lines = [ln.rstrip("\n") for ln in unitary_qasm.splitlines() if ln.strip() != ""]
    if trailing_barrier_lines:
        out_lines.extend(trailing_barrier_lines)
    if meas_lines:
        out_lines.extend(meas_lines)
    return "\n".join(out_lines) + "\n"


# -----------------------------
# Dynamic pass discovery
# -----------------------------
def _try_import(module_name, class_name):
    try:
        mod = importlib.import_module(module_name)
        cls = getattr(mod, class_name)
        return cls
    except Exception:
        return None


def _find_first_class(candidates):
    """
    candidates: list of (module, class_name)
    Returns an instantiated pass or None.
    """
    for module_name, class_name in candidates:
        cls = _try_import(module_name, class_name)
        if cls is not None:
            try:
                return cls()
            except Exception:
                continue
    return None


def build_default_workflow():
    """
    Builds a logical-only workflow using passes that exist in your BQSKit.
    Returns (workflow, passes_list). Raises if none found.
    """
    partitioners = [
        ("bqskit.passes.partitioning", "QuickPartitioner"),
        ("bqskit.passes.partitioning", "ScanPartitioner"),
        ("bqskit.passes.partitioning", "GreedyPartitioner"),
        ("bqskit.passes", "QuickPartitioner"),
        ("bqskit.passes", "ScanPartitioner"),
    ]

    consolidators = [
        ("bqskit.passes.consolidation", "ConsolidateBlocks"),
        ("bqskit.passes", "ConsolidateBlocks"),
    ]

    synthesizers = [
        ("bqskit.passes.synthesis", "QSearchSynthesisPass"),
        ("bqskit.passes.synthesis", "LEAPSynthesisPass"),
        ("bqskit.passes.synthesis", "UnitarySynthesisPass"),
        ("bqskit.passes", "QSearchSynthesisPass"),
        ("bqskit.passes", "LEAPSynthesisPass"),
    ]

    peepholes = [
        ("bqskit.passes.optimization", "PeepholeOptimize"),
        ("bqskit.passes.optimization", "PeepholeOptimizationPass"),
        ("bqskit.passes", "PeepholeOptimize"),
        ("bqskit.passes", "PeepholeOptimizationPass"),
    ]

    p_part = _find_first_class(partitioners)
    p_cons = _find_first_class(consolidators)
    p_syn = _find_first_class(synthesizers)
    p_peephole = _find_first_class(peepholes)

    passes = []
    for p in (p_part, p_cons, p_syn, p_peephole):
        if p is not None:
            passes.append(p)

    if not passes:
        raise RuntimeError("No usable BQSKit passes found in this installation.")

    wf = Workflow(passes, name="logical_default")
    return wf, passes


# -----------------------------
# Global compiler (main thread)
# -----------------------------
compiler_lock = threading.Lock()
compiler = Compiler()
logger.info("BQSKit Compiler initialized in main thread.")

try:
    default_workflow, default_passes = build_default_workflow()
    logger.info(
        "Default BQSKit workflow initialized with passes: %s",
        ", ".join([p.__class__.__name__ for p in default_passes]),
    )
except Exception as e:
    logger.error("Failed to initialize default workflow: %s", str(e))
    default_workflow = None


# -----------------------------
# BQSKit optimization
# -----------------------------
def optimize_bqskit(qasm_in: str) -> str:
    if default_workflow is None:
        raise RuntimeError("Default BQSKit workflow is not initialized.")

    # Remove measurements before unitary synthesis.
    unitary_lines, meas_lines, trailing_barrier_lines = split_unitary_and_measurements(qasm_in)
    unitary_qasm = "\n".join(unitary_lines) + "\n"

    in_path = None
    out_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".qasm", delete=False, encoding="utf-8"
        ) as f_in:
            in_path = f_in.name
            f_in.write(unitary_qasm)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".qasm", delete=False, encoding="utf-8"
        ) as f_out:
            out_path = f_out.name

        logger.info("BQSKit: reading unitary-only circuit from %s", in_path)
        circuit = Circuit.from_file(in_path)

        logger.info("BQSKit: compiling circuit with global compiler")
        with compiler_lock:
            opt_circuit = compiler.compile(circuit, default_workflow)

        logger.info("BQSKit: saving optimized unitary circuit to %s", out_path)
        opt_circuit.save(out_path)

        with open(out_path, "r", encoding="utf-8") as f:
            unitary_out = f.read()

        # Re-attach trailing barriers and measurements.
        qasm_out = join_with_measurements(unitary_out, meas_lines, trailing_barrier_lines)

        logger.info(
            "BQSKit: optimization complete. unitary_out_len=%d full_out_len=%d",
            len(unitary_out),
            len(qasm_out),
        )
        return qasm_out

    finally:
        for p in (in_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


# -----------------------------
# HTTP endpoint
# -----------------------------
@app.route("/optimize", methods=["POST"])
def optimize():
    req_id = os.urandom(4).hex()
    try:
        logger.info(
            "REQ %s: start remote=%s content_type=%s",
            req_id,
            request.remote_addr,
            request.content_type,
        )

        if not request.is_json:
            logger.warning("REQ %s: bad request, not json", req_id)
            return jsonify({"status": STATUS_BAD_REQUEST, "src": ""}), 400

        data = request.get_json(silent=True) or {}
        src_b64 = data.get("src")
        opt_type = data.get("type")

        if not isinstance(src_b64, str) or not isinstance(opt_type, int):
            logger.warning(
                "REQ %s: bad fields. src_type=%s type_type=%s",
                req_id,
                type(src_b64).__name__,
                type(opt_type).__name__,
            )
            return jsonify({"status": STATUS_BAD_REQUEST, "src": ""}), 400

        logger.info(
            "REQ %s: received type=%d src_b64_len=%d",
            req_id,
            opt_type,
            len(src_b64),
        )

        try:
            qasm_in = b64_to_text(src_b64)
            logger.info("REQ %s: base64 decode ok. qasm_len=%d", req_id, len(qasm_in))
        except Exception as e:
            logger.warning("REQ %s: base64 decode error: %s", req_id, str(e))
            return jsonify({"status": STATUS_DECODE_ERROR, "src": ""}), 400

        if opt_type == 0:
            try:
                qasm_out = optimize_bqskit(qasm_in)
                out_b64 = text_to_b64(qasm_out)
                logger.info("REQ %s: success. out_b64_len=%d", req_id, len(out_b64))
                return jsonify({"status": STATUS_OK, "src": out_b64}), 200
            except Exception as e:
                logger.error(
                    "REQ %s: BQSKit error: %s\n%s",
                    req_id,
                    str(e),
                    traceback.format_exc(),
                )
                return jsonify({"status": STATUS_BQSKIT_ERROR, "src": ""}), 500

        logger.info("REQ %s: type %d not implemented", req_id, opt_type)
        return jsonify({"status": STATUS_NOT_IMPLEMENTED, "src": ""}), 501

    except Exception as e:
        logger.error(
            "REQ %s: internal error: %s\n%s",
            req_id,
            str(e),
            traceback.format_exc(),
        )
        return jsonify({"status": STATUS_INTERNAL_ERROR, "src": ""}), 500

    finally:
        logger.info("REQ %s: end", req_id)


# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8089"))
    app.run(host="127.0.0.1", port=port)

"""Tests of the CUDA-Q (Python) debug bridge (processors/CudaQBridge.h).

The bridge runs a CUDA-Q program, converts the kernel to debug to OpenQASM 2.0 and
reports the program line of every QASM instruction. The test assembles the script like
CudaQProcessor::buildBridgeSource, runs it from a file like qdb-decom, and checks the
lines and that the QASM has the same state as the conversion without lines (verified
against Qiskit). Needs cudaq (tested with 0.16.0) and qiskit:

    python3 test/python/test_cudaq_bridge.py
"""
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADER = ROOT / "processors" / "CudaQBridge.h"
MARKER = "// qscore-lines:"


def literal(name):
    """Value of a static const char* made of one or more raw string literals."""
    text = HEADER.read_text(encoding="utf-8")
    m = re.search(r"static const char\* const %s = (.*?);\n" % name, text, re.S)
    assert m, name
    return "".join(re.findall(r'R"QSPY\((.*?)\)QSPY"', m.group(1), re.S))


def hint(source):
    m = re.search(r"cudaq\.(?:sample|sample_async|observe|observe_async|run|run_async|draw|get_state|"
                  r"get_state_async|translate)\(\s*([A-Za-z_][A-Za-z0-9_]*)", source)
    return m.group(1) if m else None


def py_literal(value):
    return "None" if not value else repr(value)


def bridge(source, with_lines=True, root=None, program_path=None):
    """Same assembly as CudaQProcessor::buildBridgeSource."""
    lines = source.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from __future__ import"):
            insert_at = i + 1
    prologue = literal("CUDAQ_PROLOGUE")
    lines_before = prologue.count("\n")
    prologue = prologue.replace("__QS_PROJECT_ROOT__", py_literal(root), 1)
    prologue = prologue.replace("__QS_PROGRAM_DIR__", py_literal(str(Path(program_path).parent) if program_path else None), 1)
    assert prologue.count("\n") == lines_before
    out = "".join(l + "\n" for l in lines[:insert_at]) + prologue
    out += "".join(l + "\n" for l in lines[insert_at:])
    out += "\n_QS_KERNEL_HINT = %r\n" % hint(source)
    out += literal("CUDAQ_EPILOGUE")
    out += "_QS_LINE_SHIFT = (%d, %d)\n" % (insert_at, prologue.count("\n"))
    if with_lines:
        out += literal("CUDAQ_LINES")
    else:
        out += "code777 = _qs_cudaq_to_qasm(globals(), _QS_KERNEL_HINT)\n"
    out += literal("CUDAQ_RESTORE_STDOUT")
    return out


def run(source, with_lines=True, root=None, program_path=None):
    """Runs the bridge from a file like qdb-decom (env mode); returns (code, result, stderr)."""
    script = bridge(source, with_lines, root, program_path) + (
        "\n\nimport sys\nresult = globals().get('code777', None)\n"
        "sys.stdout.write('' if result is None else str(result))\n")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script)
    proc = subprocess.run([sys.executable, f.name], capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout, proc.stderr


def instruction_lines(result):
    lines = result.splitlines()
    assert lines and lines[-1].startswith(MARKER), "no source lines in the result:\n" + result
    numbers = [int(n) for n in lines[-1][len(MARKER):].split(",")]
    qasm = lines[:-1]
    assert len(numbers) == len(qasm), (len(numbers), len(qasm))
    declaration = re.compile(r"^\s*((OPENQASM|include|qreg|creg|gate|opaque|barrier)\b|//|$)")
    return [(q.strip(), n) for q, n in zip(qasm, numbers) if not declaration.match(q)]


def probabilities(qasm):
    """Measurement probabilities of a QASM program (measurements removed), by Qiskit."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Statevector
    body = "\n".join(l for l in qasm.splitlines() if not l.strip().startswith(("measure", MARKER)))
    circuit = QuantumCircuit.from_qasm_str(body)
    return Statevector(circuit).probabilities_dict(decimals=9)


def program_line(program, text):
    found = [i + 1 for i, line in enumerate(program.splitlines()) if text in line]
    assert len(found) == 1, (text, found)
    return found[0]


PASSED, FAILED = [], []


def case(name):
    def wrap(fn):
        try:
            fn()
            PASSED.append(name)
            print("OK  ", name)
        except Exception as error:  # noqa: BLE001
            FAILED.append(name)
            print("FAIL", name, "-", error)
        return fn
    return wrap


def check(program, expected):
    """expected: list of program texts, one per QASM instruction (the line containing it)."""
    code, out, err = run(program)
    assert code == 0, err
    got = [n for _, n in instruction_lines(out)]
    want = [program_line(program, t) for t in expected]
    assert got == want, "lines %s, expected %s" % (got, want)
    code, plain, err = run(program, with_lines=False)
    assert code == 0, err
    assert probabilities(out) == probabilities(plain), "QASM differs from the conversion without lines"


@case("straight-line kernel, register gates, prints and comments")
def _():
    program = textwrap.dedent('''\
        import cudaq
        print("start")

        # Grover on two qubits
        @cudaq.kernel
        def grover():
            q = cudaq.qvector(2)
            h(q)
            z.ctrl(q[0], q[1])
            h(q)
            mz(q)

        print(cudaq.sample(grover, shots_count=100))
        ''')
    code, out, err = run(program)
    assert code == 0, err
    got = [n for _, n in instruction_lines(out)]
    lines = program.splitlines()
    h = [i + 1 for i, l in enumerate(lines) if l.strip() == "h(q)"]
    z, m = program_line(program, "z.ctrl("), program_line(program, "mz(q)")
    assert got == [h[0], h[0], z, h[1], h[1], m, m], got
    assert "start" not in out


@case("loops, called kernels, rotations and adjoints")
def _():
    program = textwrap.dedent('''\
        from __future__ import annotations
        import math
        import cudaq


        @cudaq.kernel
        def layer(q: cudaq.qview):
            for i in range(2):
                ry(math.pi / 3, q[i])
            x.ctrl(q[0], q[1])


        @cudaq.kernel
        def main_kernel():
            q = cudaq.qvector(3)
            h(q[0])
            layer(q)
            t.adj(q[2])
            swap(q[1], q[2])
            mz(q)


        print(cudaq.sample(main_kernel))
        ''')
    check(program, ["h(q[0])", "ry(math.pi", "ry(math.pi", "x.ctrl(", "t.adj(", "swap(", "mz(q)", "mz(q)", "mz(q)"])


@case("samples: bell-state, grover-search, oblivious-amplitude-amplification")
def _():
    samples = ROOT.parent / "quantag-studio" / "backend" / "samples" / "algorithms"
    if not samples.is_dir():
        print("     (quantag-studio samples not found next to qdb-qscore, skipped)")
        return
    for name in ("bell-state", "grover-search", "oblivious-amplitude-amplification"):
        program = (samples / name / "cudaq" / "main.py").read_text(encoding="utf-8")
        code, out, err = run(program)
        assert code == 0, (name, err)
        got = instruction_lines(out)
        assert all(n > 0 for _, n in got), (name, got)
        code, plain, err = run(program, with_lines=False)
        assert probabilities(out) == probabilities(plain), name


@case("kernel that cannot be converted with lines falls back to the conversion without lines")
def _():
    program = textwrap.dedent('''\
        import cudaq


        @cudaq.kernel
        def k():
            q = cudaq.qvector(2)
            h(q[0])
            if mz(q[0]):
                x(q[1])

        print(cudaq.sample(k))
        ''')
    code, out, err = run(program)
    lines_code, plain, plain_err = run(program, with_lines=False)
    # same outcome as without lines (QASM or the same error), never a different error
    assert MARKER not in out
    assert code == lines_code and (code != 0 or out == plain), (err, plain_err)


@case("project root: local module import and relative data path in the program")
def _():
    root = Path(tempfile.mkdtemp())
    (root / "consts.py").write_text("ANGLE = 0.25\n")
    (root / "data").mkdir()
    (root / "data" / "n.txt").write_text("3\n")
    program = textwrap.dedent('''\
        import cudaq
        from consts import ANGLE
        N = int(open("data/n.txt").read())


        @cudaq.kernel
        def k():
            q = cudaq.qvector(3)
            ry(0.25, q[0])
            x.ctrl(q[0], q[1])
            mz(q)


        assert N == 3 and ANGLE == 0.25
        print(cudaq.sample(k))
        ''')
    (root / "main.py").write_text(program)
    code, out, err = run(program, root=str(root), program_path=str(root / "main.py"))
    assert code == 0, err[-800:]
    got = [n for _, n in instruction_lines(out)]
    assert got == [program_line(program, "ry(0.25"), program_line(program, "x.ctrl(")] + [program_line(program, "mz(q)")] * 3, got


print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
sys.exit(1 if FAILED else 0)

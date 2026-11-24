/*
 * Copyright (c) 2024 Quantag IT Solutions GmbH
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// Python code that CudaQProcessor adds around a CUDA-Q program before it is sent to
// the Python executor (qdb-decom). The program runs unchanged; its output is kept
// out of the result, and at the end the kernel to debug is converted to OpenQASM 2.0:
//  1. cudaq.translate(kernel, format="openqasm2") for kernels that call no other kernels;
//  2. otherwise cudaq.translate(kernel, format="qir-adaptive") (all calls inlined) and
//     the QIR gate calls are converted to OpenQASM 2.0 (qelib1.inc gates only).
// The kernel is the one passed to cudaq.sample/observe/... (hint) or the last kernel
// without parameters. Verified with cudaq 0.16.0 (state vectors compared with Qiskit).
//
// Source lines (CUDAQ_LINES): the prologue makes the CUDA-Q AST bridge attach the
// Python line to every operation of a kernel. At the end the kernel is merged with the
// kernels it calls, inlined and unrolled with CUDA-Q passes, and its Quake is converted
// to OpenQASM 2.0 keeping the line of every gate (the conversion of cudaq-cpp-qasm,
// used for C++). The result ends with "// qscore-lines: ..." (QASM_LINES_MARKER), read by
// BaseQVM. When that fails, the conversion above (without lines) is used.

#pragma once

// Inserted before the program (after "from __future__" imports)
// CudaQProcessor reports its number of lines to CUDAQ_LINES (_QS_LINE_SHIFT) so that
// the lines of the program are not shifted. CudaQProcessor replaces __QS_PROJECT_ROOT__
// and __QS_PROGRAM_DIR__ with Python literals (same number of lines): the program runs
// as if started in the project root (sys.path, working directory).
static const char* const CUDAQ_PROLOGUE = R"QSPY(# --- Quantag QSCore: keep prints of the user code out of the result, source lines for kernels (prepended by CudaQProcessor) ---
import sys as _qs_sys, io as _qs_io
_qs_saved_stdout = _qs_sys.stdout
_qs_sys.stdout = _qs_io.StringIO()
def _qs_locate_kernels():
    try:
        import ast
        from cudaq.kernel import ast_bridge
        from cudaq.mlir.ir import Location
    except Exception:
        return
    visit = ast_bridge.PyASTBridge.visit
    def located(self, node):
        try:
            if isinstance(node, ast.Module) or getattr(node, "lineno", None) is None:
                raise LookupError
            loc = Location.file(self.locationOffset[0], node.lineno + self.locationOffset[1] - 1,
                                getattr(node, "col_offset", 0) or 0, context=self.ctx)
        except Exception:
            return visit(self, node)
        with loc:
            return visit(self, node)
    ast_bridge.PyASTBridge.visit = located
_qs_locate_kernels()
_QS_PROJECT_ROOT = __QS_PROJECT_ROOT__
_QS_PROGRAM_DIR = __QS_PROGRAM_DIR__
import os as _qs_os
_qs_saved_cwd, _qs_saved_path, _qs_saved_modules = _qs_os.getcwd(), list(_qs_sys.path), set(_qs_sys.modules)
for _qs_dir in (_QS_PROJECT_ROOT, _QS_PROGRAM_DIR):
    if _qs_dir and _qs_os.path.isdir(_qs_dir) and _qs_dir not in _qs_sys.path:
        _qs_sys.path.insert(0, _qs_dir)
if _QS_PROJECT_ROOT and _qs_os.path.isdir(_QS_PROJECT_ROOT):
    _qs_os.chdir(_QS_PROJECT_ROOT)
)QSPY";

// Appended after the program and the line "_QS_KERNEL_HINT = <name or None>"
static const char* const CUDAQ_EPILOGUE = R"QSPY(# --- Quantag QSCore: CUDA-Q kernel -> OpenQASM 2.0 (appended by CudaQProcessor) ---
def _qs_cudaq_to_qasm(_qs_ns, _qs_hint):
    import math
    import re
    import struct
    import cudaq

    def is_kernel(obj):
        try:
            from cudaq.kernel.kernel_decorator import isa_kernel_decorator
            return isa_kernel_decorator(obj)
        except Exception:
            return hasattr(obj, "formal_arity") and hasattr(obj, "launch_args_required")

    kernels = {n: o for n, o in list(_qs_ns.items()) if not n.startswith("_qs_") and is_kernel(o)}
    if not kernels:
        raise RuntimeError("QSCore: no @cudaq.kernel found in the file")
    if _qs_hint and _qs_hint in kernels:
        name = _qs_hint
    else:
        free = [n for n, k in kernels.items() if k.formal_arity() == 0]
        if not free:
            raise RuntimeError("QSCore: debugging needs a CUDA-Q kernel without parameters "
                               "(found only kernels with parameters: " + ", ".join(kernels) + ")")
        name = free[-1]
    kernel = kernels[name]
    if kernel.formal_arity() != 0:
        raise RuntimeError("QSCore: kernel '" + name + "' has parameters; debugging needs a kernel without parameters")

    # 1. Direct translation (works for kernels that do not call other kernels)
    try:
        return cudaq.translate(kernel, format="openqasm2")
    except Exception:
        pass

    # 2. Kernels that call other kernels: translate to QIR (adaptive profile, all
    #    calls inlined, static qubits) and convert the gate calls to OpenQASM 2.0.
    qir = cudaq.translate(kernel, format="qir-adaptive")

    def operands(text):
        out, depth, cur = [], 0, ""
        for ch in text:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur.strip())
        return out

    def qubit(op):
        if re.search(r"\bnull\b", op):
            return 0
        m = re.search(r"inttoptr\s*\(\s*i64\s+(\d+)\s+to", op)
        if not m:
            raise RuntimeError("QSCore: dynamic qubit addressing is not supported: " + op)
        return int(m.group(1))

    def number(op):
        v = op.split()[-1]
        if v.lower().startswith("0x"):
            return struct.unpack(">d", bytes.fromhex(v[2:].rjust(16, "0")))[0]
        return float(v)

    def ang(x):
        return repr(float(x))

    simple = {"h": "h", "x": "x", "y": "y", "z": "z", "s": "s", "t": "t"}
    adjoint = {"s": "sdg", "t": "tdg"}
    rotation = {"rx": "rx", "ry": "ry", "rz": "rz", "r1": "u1"}
    lines, nq, ncl = [], 0, 0

    def q(i):
        nonlocal nq
        nq = max(nq, i + 1)
        return "q[%d]" % i

    def controlled(op, params, ctrls, targets):
        c, t = [q(i) for i in ctrls], [q(i) for i in targets]
        k = len(c)
        if op == "x" and k == 1:
            return ["cx %s, %s;" % (c[0], t[0])]
        if op == "x" and k == 2:
            return ["ccx %s, %s, %s;" % (c[0], c[1], t[0])]
        if op == "z" and k == 1:
            return ["cz %s, %s;" % (c[0], t[0])]
        if op == "z" and k == 2:
            return ["h %s;" % t[0], "ccx %s, %s, %s;" % (c[0], c[1], t[0]), "h %s;" % t[0]]
        if k != 1:
            raise RuntimeError("QSCore: %s with %d controls is not supported" % (op, k))
        if op == "y":
            return ["cy %s, %s;" % (c[0], t[0])]
        if op == "h":
            return ["ch %s, %s;" % (c[0], t[0])]
        if op in ("s", "t", "sdg", "tdg"):
            a = {"s": math.pi / 2, "t": math.pi / 4, "sdg": -math.pi / 2, "tdg": -math.pi / 4}[op]
            return ["cu1(%s) %s, %s;" % (ang(a), c[0], t[0])]
        if op == "rz":
            return ["crz(%s) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "r1":
            return ["cu1(%s) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "rx":
            return ["cu3(%s,%s,%s) %s, %s;" % (ang(params[0]), ang(-math.pi / 2), ang(math.pi / 2), c[0], t[0])]
        if op == "ry":
            return ["cu3(%s,0,0) %s, %s;" % (ang(params[0]), c[0], t[0])]
        if op == "swap":  # controlled swap via Toffoli (cswap is not in qelib1.inc)
            return ["cx %s, %s;" % (t[1], t[0]), "ccx %s, %s, %s;" % (c[0], t[0], t[1]), "cx %s, %s;" % (t[1], t[0])]
        raise RuntimeError("QSCore: controlled %s is not supported" % op)

    call_re = re.compile(r"call\s+[^@]*@([\w.]+)\s*\((.*)\)\s*$")
    for raw in qir.splitlines():
        m = call_re.search(raw.strip())
        if not m:
            continue
        fn, args = m.group(1), operands(m.group(2))
        if fn == "generalizedInvokeWithRotationsControlsTargets":
            nrot, narr, nctl, ntgt = (int(a.split()[-1]) for a in args[:4])
            fm = re.search(r"@__quantum__qis__(\w+?)__(ctl|ctladj)\b", args[4])
            if not fm or narr:
                raise RuntimeError("QSCore: unsupported controlled call: " + raw.strip())
            op = fm.group(1)
            if fm.group(2) == "ctladj":
                op = {"s": "sdg", "t": "tdg"}.get(op, op)
            rest = args[5:]
            params = [number(a) for a in rest[:nrot]]
            if fm.group(2) == "ctladj" and op in rotation:
                params = [-p for p in params]
            ctrls = [qubit(a) for a in rest[nrot:nrot + nctl]]
            targets = [qubit(a) for a in rest[nrot + nctl:nrot + nctl + ntgt]]
            lines += controlled(op, params, ctrls, targets)
            continue
        qm = re.match(r"__quantum__qis__(\w+?)__(body|adj)$", fn)
        if not qm:
            continue  # runtime calls (allocation, output recording, ...)
        op, kind = qm.groups()
        if op in ("mz", "m"):
            i, r = qubit(args[0]), qubit(args[1]) if len(args) > 1 else 0
            ncl = max(ncl, r + 1)
            lines.append("measure %s -> c[%d];" % (q(i), r))
        elif op == "reset":
            lines.append("reset %s;" % q(qubit(args[0])))
        elif op in simple and kind == "body":
            lines.append("%s %s;" % (simple[op], q(qubit(args[0]))))
        elif op in adjoint and kind == "adj":
            lines.append("%s %s;" % (adjoint[op], q(qubit(args[0]))))
        elif op in ("x", "y", "z", "h") and kind == "adj":
            lines.append("%s %s;" % (op, q(qubit(args[0]))))
        elif op in rotation:
            a = number(args[0]) * (-1 if kind == "adj" else 1)
            lines.append("%s(%s) %s;" % (rotation[op], ang(a), q(qubit(args[1]))))
        elif op == "u3":
            a = [number(x) for x in args[:3]]
            lines.append("u3(%s,%s,%s) %s;" % (ang(a[0]), ang(a[1]), ang(a[2]), q(qubit(args[3]))))
        elif op == "cnot":
            lines.append("cx %s, %s;" % (q(qubit(args[0])), q(qubit(args[1]))))
        elif op == "cz":
            lines.append("cz %s, %s;" % (q(qubit(args[0])), q(qubit(args[1]))))
        elif op == "swap":  # swap is not in qelib1.inc
            a, b = q(qubit(args[0])), q(qubit(args[1]))
            lines += ["cx %s, %s;" % (a, b), "cx %s, %s;" % (b, a), "cx %s, %s;" % (a, b)]
        else:
            raise RuntimeError("QSCore: CUDA-Q operation '%s' is not supported" % op)

    m = re.search(r'"(?:requiredQubits|required_num_qubits)"="(\d+)"', qir)
    if m:
        nq = max(nq, int(m.group(1)))
    m = re.search(r'"(?:requiredResults|required_num_results)"="(\d+)"', qir)
    if m and ncl:
        ncl = max(ncl, int(m.group(1)))
    head = ["// Converted from CUDA-Q kernel '%s' by QSCore" % name, "OPENQASM 2.0;", 'include "qelib1.inc";',
            "qreg q[%d];" % max(nq, 1)]
    if ncl:
        head.append("creg c[%d];" % ncl)
    return "\n".join(head + lines) + "\n"


)QSPY";

// Appended after CUDAQ_EPILOGUE and the line "_QS_LINE_SHIFT = (<line>, <count>)":
// the prologue was inserted after line <line> of the program and has <count> lines.
static const char* const CUDAQ_LINES = R"QSPY(# --- Quantag QSCore: CUDA-Q kernel -> OpenQASM 2.0 with source lines (appended by CudaQProcessor) ---
# The prologue makes the CUDA-Q AST bridge attach the Python line to every operation it
# builds. Here the kernel to debug is merged with the kernels it calls, inlined and
# unrolled (CUDA-Q passes), and its Quake is converted to OpenQASM 2.0 keeping the
# program line of every gate (same conversion as cudaq-cpp-qasm for C++). The result is
# the QASM followed by "// qscore-lines: l1,l2,..." (read by QSCore). If any step fails,
# the kernel is converted without lines by _qs_cudaq_to_qasm (fallback).
def _qs_cudaq_with_lines(_qs_ns, _qs_hint, _qs_shift, _qs_fallback):
    import math
    import os
    import re
    import sys

    class TranslationError(Exception):
        pass

    def pick_kernel():
        from cudaq.kernel.kernel_decorator import isa_kernel_decorator
        kernels = {n: o for n, o in list(_qs_ns.items()) if not n.startswith("_qs_") and isa_kernel_decorator(o)}
        if not kernels:
            raise TranslationError("no @cudaq.kernel found")
        if _qs_hint and _qs_hint in kernels:
            name = _qs_hint
        else:
            free = [n for n, k in kernels.items() if k.formal_arity() == 0]
            if not free:
                raise TranslationError("no kernel without parameters")
            name = free[-1]
        if kernels[name].formal_arity() != 0:
            raise TranslationError("kernel '%s' has parameters" % name)
        return name, kernels

    def split_top(text):
        """Split by commas that are not inside brackets ("->" does not close one)."""
        text = text.replace("->", "\x00")
        out, depth, cur = [], 0, ""
        for ch in text:
            if ch in "([<{":
                depth += 1
            elif ch in ")]>}":
                depth -= 1
            if ch == "," and depth == 0:
                out.append(cur.strip())
                cur = ""
            else:
                cur += ch
        if cur.strip():
            out.append(cur.strip())
        return [x.replace("\x00", "->") for x in out]

    def located_quake(name, kernels):
        """Quake of the kernel with the kernels it calls merged in, inlined and unrolled."""
        from cudaq.mlir.ir import Module
        from cudaq.mlir.passmanager import PassManager
        from cudaq.mlir._mlir_libs._quakeDialects import cudaq_runtime

        def asm(module):
            return module.operation.get_asm(enable_debug_info=True)

        module = kernels[name].qkeModule
        merged = {name}
        while True:
            missing = [s for s in set(re.findall(r'\{symbol = "(\w+)"\}', asm(module))) if s not in merged]
            if not missing:
                break
            for symbol in missing:
                if symbol not in kernels:
                    raise TranslationError("called kernel '%s' not found" % symbol)
                module = cudaq_runtime.mergeExternalMLIR(module, kernels[symbol].qkeModule)
                merged.add(symbol)

        text = asm(module)
        functions = {}
        for symbol, kernel in re.findall(r"func\.func (?:private )?@(__nvqpp__mlirgen__(\w+)\.\.0x[0-9a-f]+)", text):
            functions.setdefault(kernel, symbol)
        call = re.compile(r'cc\.call_callable (%[\w.]+), (.+?) : \((.*)\) -> \(\) \{symbol = "(\w+)"\} (loc\(.*\))$')

        def direct(line):
            # Called kernels are lifted to callable arguments; call them directly.
            m = call.search(line)
            if not m:
                return line
            if m.group(4) not in functions:
                raise TranslationError("called kernel '%s' not found" % m.group(4))
            types = split_top(m.group(3))[1:]
            return line[:m.start()] + "func.call @%s(%s) : (%s) -> () %s" % (
                functions[m.group(4)], m.group(2), ", ".join(types), m.group(5))

        text = "\n".join(direct(line) for line in text.splitlines())
        module = Module.parse(text, context=kernels[name].qkeModule.context)
        PassManager.parse(
            "builtin.module(lambda-lifting,apply-op-specialization,inline,canonicalize,"
            "func.func(memtoreg{quantum=0}),canonicalize,cc-loop-unroll,canonicalize,cse)",
            context=module.context).run(module.operation)
        return asm(module), functions[name]

)QSPY"
// (split in two literals: MSVC limits one string literal to 16 KB)
R"QSPY(    LOC_DEF = re.compile(r"^(#loc\d*)\s*=\s*loc\((.*)\)\s*$")
    FILE_LOC = re.compile(r'^"([^"]*)":(\d+):(\d+)')

    class Locations:
        def __init__(self, text, main_file):
            self.defs = {}
            for line in text.splitlines():
                m = LOC_DEF.match(line.strip())
                if m:
                    self.defs[m.group(1)] = m.group(2)
            self.main_base = os.path.basename(main_file)
            self.cache = {}

        def chain(self, body, depth=0):
            """File locations of a loc() body, innermost first."""
            if depth > 50:
                return []
            body = body.strip()
            if body.startswith("#loc"):
                ref = re.match(r"(#loc\d*)", body).group(1)
                return self.chain(self.defs[ref], depth + 1) if ref in self.defs else []
            m = FILE_LOC.match(body)
            if m:
                return [(m.group(1), int(m.group(2)))]
            m = re.match(r"^callsite\((.*) at (.*)\)$", body)
            if m:
                return self.chain(m.group(1), depth + 1) + self.chain(m.group(2), depth + 1)
            m = re.match(r"^fused(?:<[^>]*>)?\[(.*)\]$", body)
            if m:
                out = []
                for part in split_top(m.group(1)):
                    out += self.chain(part, depth + 1)
                return out
            m = re.match(r'^"[^"]*"\((.*)\)$', body)
            if m:
                return self.chain(m.group(1), depth + 1)
            return []

        def line_of(self, op_line):
            m = re.search(r"loc\((.*)\)\s*$", op_line)
            if not m:
                return 0
            key = m.group(1)
            if key not in self.cache:
                line = 0
                for path, num in self.chain(key):
                    if os.path.basename(path) == self.main_base:
                        line = num
                        break
                # the prologue inserted before the program shifts its lines
                at, by = _qs_shift
                if line > at:
                    line = line - by if line > at + by else 0
                self.cache[key] = line
            return self.cache[key]

    def kernel_body(text, symbol):
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^\s*func\.func\s+(?:private\s+)?@" + re.escape(symbol) + r"\(", line):
                body = []
                for inner in lines[i + 1:]:
                    if re.match(r"^  \}", inner):
                        return body
                    body.append(inner)
        raise TranslationError("kernel body not found")

    OP_RE = re.compile(
        r"^(?:(%[\w.]+)\s*=\s*)?quake\.(\w+)(<adj>)?\s*"
        r"(?:\(([^)]*)\))?\s*"
        r"(?:\[([^\]]*)\])?\s*"
        r"(.*?)\s*(?:name\s+\"[^\"]*\"\s*)?(?:neg\s*\[([^\]]*)\]\s*)?$")

    def op_text(line):
        line = re.sub(r"\s*loc\(.*\)\s*$", "", line)
        return re.split(r"\s:\s", line, maxsplit=1)[0].strip()

    def fmt(x):
        return repr(float(x))

    class Translator:
        def __init__(self, body, locs):
            self.body, self.locs = body, locs
            self.consts, self.vals = {}, {}
            self.nq, self.ncl, self.out = 0, 0, []

        def emit(self, text, line):
            self.out.append((text, line))

        def qubits(self, operand):
            operand = operand.strip()
            if operand not in self.vals:
                raise TranslationError("unsupported qubit value %s" % operand)
            return self.vals[operand]

        def number(self, operand):
            operand = operand.strip()
            if operand in self.consts:
                return self.consts[operand]
            raise TranslationError("gate parameter %s is not a constant" % operand)

        def index(self, text):
            text = text.strip()
            return int(text) if re.fullmatch(r"-?\d+", text) else int(self.number(text))

        def run(self):
            for raw in self.body:
                line = raw.strip()
                if not line or line.startswith("return") or line.startswith("}"):
                    continue
                src = self.locs.line_of(line)
                m = re.match(r"^(%[\w.]+)\s*=\s*arith\.constant\s+([^:]+?)\s*:\s*(\w+)", line)
                if m:
                    v = m.group(2)
                    if v in ("true", "false"):
                        self.consts[m.group(1)] = 1.0 if v == "true" else 0.0
                    else:
                        try:
                            self.consts[m.group(1)] = float.fromhex(v) if v.lower().startswith("0x") else float(v)
                        except ValueError:
                            pass
                    continue
                if line.startswith("cc.") or re.match(r"^%[\w.]+\s*=\s*cc\.", line):
                    if "cc.loop" in line or "cc.if" in line or "cf." in line or "cc.call_callable" in line:
                        raise TranslationError("loops, branches or calls left after inlining (line %d)" % src)
                    continue
                if "func.call" in line or line.startswith("arith.") or re.match(r"^%[\w.]+\s*=\s*(arith|math)\.", line):
                    raise TranslationError("calls or run-time arithmetic left in the kernel (line %d)" % src)
                m = OP_RE.match(op_text(line))
                if not m:
                    if "quake." in line:
                        raise TranslationError("unsupported operation: %s" % line.split(":")[0])
                    continue
                self.op(m, src)
            head = ["OPENQASM 2.0;", 'include "qelib1.inc";', "qreg q[%d];" % max(self.nq, 1)]
            if self.ncl:
                head.append("creg c[%d];" % self.ncl)
            return head + [g for g, _ in self.out], [0] * len(head) + [s for _, s in self.out]

        def op(self, m, src):
            res, name, adj, params, ctrls, targets, neg = m.groups()
            targets = [t for t in split_top(targets) if t]
            if name == "alloca":
                mm = re.search(r"!quake\.veq<(\d+)>", m.string)
                if not mm and "!quake.ref" not in m.string and not m.string.strip().endswith("alloca"):
                    raise TranslationError("qubit allocation with a run-time size")
                n = int(mm.group(1)) if mm else 1
                self.vals[res] = list(range(self.nq, self.nq + n))
                self.nq += n
                return
            if name == "extract_ref":
                mm = re.match(r"(%[\w.]+)\[([^\]]+)\]", targets[0] if targets else "")
                if not mm:
                    raise TranslationError("unsupported extract_ref")
                self.vals[res] = [self.qubits(mm.group(1))[self.index(mm.group(2))]]
                return
            if name in ("relax_size", "concat"):
                qs = []
                for t in targets:
                    qs += self.qubits(t)
                self.vals[res] = qs
                return
            if name == "subveq":
                base = self.qubits(targets[0])
                self.vals[res] = base[self.index(targets[1]):self.index(targets[2]) + 1]
                return
            if name in ("dealloc", "discriminate", "sink", "null_wire", "log_output"):
                return
            if name in ("mz", "mx", "my"):
                for t in targets:
                    for q in self.qubits(t):
                        if name == "mx":
                            self.emit("h q[%d];" % q, src)
                        elif name == "my":
                            self.emit("sdg q[%d];" % q, src)
                            self.emit("h q[%d];" % q, src)
                        self.emit("measure q[%d] -> c[%d];" % (q, self.ncl), src)
                        self.ncl += 1
                return
            if name == "reset":
                for t in targets:
                    for q in self.qubits(t):
                        self.emit("reset q[%d];" % q, src)
                return
            p = [self.number(x) for x in split_top(params)] if params else []
            c, t = [], []
            for x in split_top(ctrls or ""):
                c += self.qubits(x)
            for x in targets:
                t += self.qubits(x)
            negated = []
            if neg:
                flags = [f.strip() == "true" for f in neg.split(",")]
                negated = [q for q, f in zip(c, flags) if f]
            for q in negated:
                self.emit("x q[%d];" % q, src)
            self.gate(name, bool(adj), p, c, t, src)
            for q in negated:
                self.emit("x q[%d];" % q, src)

        def gate(self, name, adj, p, c, t, src):
            q = lambda i: "q[%d]" % i
            k = len(c)
            if name in ("rx", "ry", "rz", "r1") and adj:
                p = [-p[0]]
            if name == "u3" and adj:
                p = [-p[0], -p[2], -p[1]]
            if name in ("s", "t") and adj:
                name += "dg"
            if name == "swap":
                if k == 0:
                    return self.emit("swap %s, %s;" % (q(t[0]), q(t[1])), src)
                if k == 1:
                    return self.emit("cswap %s, %s, %s;" % (q(c[0]), q(t[0]), q(t[1])), src)
                raise TranslationError("swap with %d controls" % k)
            if len(t) != 1:
                if k == 0 and name in ("h", "x", "y", "z", "s", "t", "sdg", "tdg"):
                    for i in t:
                        self.emit("%s %s;" % (name, q(i)), src)
                    return
                raise TranslationError("%s on %d targets" % (name, len(t)))
            tq = q(t[0])
            if k == 0:
                if name in ("h", "x", "y", "z", "s", "t", "sdg", "tdg"):
                    return self.emit("%s %s;" % (name, tq), src)
                if name in ("rx", "ry", "rz"):
                    return self.emit("%s(%s) %s;" % (name, fmt(p[0]), tq), src)
                if name == "r1":
                    return self.emit("u1(%s) %s;" % (fmt(p[0]), tq), src)
                if name == "u3":
                    return self.emit("u3(%s,%s,%s) %s;" % (fmt(p[0]), fmt(p[1]), fmt(p[2]), tq), src)
            elif k == 1:
                cq = q(c[0])
                simple = {"x": "cx", "y": "cy", "z": "cz", "h": "ch"}
                if name in simple:
                    return self.emit("%s %s, %s;" % (simple[name], cq, tq), src)
                phase = {"s": math.pi / 2, "t": math.pi / 4, "sdg": -math.pi / 2, "tdg": -math.pi / 4}
                if name in phase:
                    return self.emit("cu1(%s) %s, %s;" % (fmt(phase[name]), cq, tq), src)
                if name == "rz":
                    return self.emit("crz(%s) %s, %s;" % (fmt(p[0]), cq, tq), src)
                if name == "r1":
                    return self.emit("cu1(%s) %s, %s;" % (fmt(p[0]), cq, tq), src)
                if name == "rx":
                    return self.emit("cu3(%s,%s,%s) %s, %s;" % (fmt(p[0]), fmt(-math.pi / 2), fmt(math.pi / 2), cq, tq), src)
                if name == "ry":
                    return self.emit("cu3(%s,0,0) %s, %s;" % (fmt(p[0]), cq, tq), src)
                if name == "u3":
                    return self.emit("cu3(%s,%s,%s) %s, %s;" % (fmt(p[0]), fmt(p[1]), fmt(p[2]), cq, tq), src)
            elif k == 2:
                a, b = q(c[0]), q(c[1])
                if name == "x":
                    return self.emit("ccx %s, %s, %s;" % (a, b, tq), src)
                if name == "z":
                    self.emit("h %s;" % tq, src)
                    self.emit("ccx %s, %s, %s;" % (a, b, tq), src)
                    return self.emit("h %s;" % tq, src)
            raise TranslationError("%s%s is not supported" % (name, " with %d controls" % k if k else ""))

    try:
        name, kernels = pick_kernel()
        text, symbol = located_quake(name, kernels)
        main_file = kernels[name].location[0]
        qasm, lines = Translator(kernel_body(text, symbol), Locations(text, main_file)).run()
        if not any(lines):
            raise TranslationError("no source lines found for the gates")
        return "// Converted from CUDA-Q kernel '%s' by QSCore\n" % name + "\n".join(qasm) + \
            "\n// qscore-lines: 0," + ",".join(str(n) for n in lines) + "\n"
    except Exception as error:
        sys.stderr.write("QSCore: CUDA-Q source lines not available (%s: %s); converting without lines\n"
                         % (type(error).__name__, error))
        return _qs_fallback(_qs_ns, _qs_hint)

code777 = _qs_cudaq_with_lines(globals(), _QS_KERNEL_HINT, _QS_LINE_SHIFT, _qs_cudaq_to_qasm)
)QSPY";

// Appended last: restores stdout so the executor can print the result
// (also restores the working directory and sys.path, and drops the program's local
// modules from sys.modules for executors that run scripts in their own process)
static const char* const CUDAQ_RESTORE_STDOUT = R"QSPY(_qs_sys.stdout = _qs_saved_stdout
_qs_sys.path[:] = _qs_saved_path
try:
    _qs_os.chdir(_qs_saved_cwd)
except OSError:
    pass
_qs_local = [_qs_os.path.realpath(_qs_d) + _qs_os.sep for _qs_d in (_QS_PROJECT_ROOT, _QS_PROGRAM_DIR) if _qs_d]
for _qs_name in [n for n in list(_qs_sys.modules) if n not in _qs_saved_modules]:
    _qs_file = getattr(_qs_sys.modules.get(_qs_name), "__file__", None) or ""
    if _qs_local and any(_qs_os.path.realpath(_qs_file).startswith(_qs_p) for _qs_p in _qs_local):
        del _qs_sys.modules[_qs_name]
)QSPY";

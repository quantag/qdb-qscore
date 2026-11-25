# Deploying the debugger backend (cryspprod3)

The VS Code extension on the **desktop** uses the debugger backend on `cryspprod3.quantag-it.com` (also reached as `node3.quantag-it.com`). Quantag Studio workspaces (Coder) do not use it: they run their own QSCore and Python executor inside the workspace image (see `backend/docs/auth_and_coder_ide_spec.md` in quantag-studio).

Nothing is deployed automatically: merging into `main` changes only GitHub. Every service below is updated by hand on the server.

## Services

| Service | What it does | Code | Runs as | Folder on the server | Address |
| --- | --- | --- | --- | --- | --- |
| `qscore` | QSCore: DAP server for VS Code, translates programs to OpenQASM, simulates (qpp) | this repo (C++) | `qbit` | `/home/qbit/qdb-qscore` (binary `build/QSCore`) | `78.47.44.63:5555` (DAP), `:5556` (WebSocket) |
| `dapp` | receives the program files from the extension and stores them in `/var/dap/<session>` | `scripts/dapp/app.py` | `admin` | `/home/admin/work/dapp` | `127.0.0.1:8150`, public `https://cryspprod3.quantag-it.com:444/api2/...` |
| `qdb-decom` | Python executor: runs the Python code QSCore sends and returns the OpenQASM | `server2.py` on the server (not in this repo; `scripts/qdb-decom/app.py` is the version used in Studio workspaces) | `qbit` | `/home/qbit/qdb-decom` (venv `my-venv`) | public `https://cryspprod3.quantag-it.com:444/api3/dec` |

How they work together for one debug session:

1. The extension uploads the program and the files it needs to `dapp`, which writes them to `/var/dap/<session>`.
2. VS Code connects to QSCore on port 5555 and starts the session. QSCore reads the program from `/var/dap/<session>` (`source.folder` in `build/QSCore.ini`).
3. For Python, QSCore sends the program wrapped in a bridge (`processors/QiskitBridge.h`, `processors/CudaQBridge.h`) to `qdb-decom`. The executor runs it and returns the OpenQASM with the source line of every instruction.
4. QSCore runs the OpenQASM on qpp step by step and reports the lines and the state to VS Code.

`dapp` and QSCore share `/var/dap`, so they must run on the same machine (or with a shared disk).

## QSCore

Git commands run as `qbit`: the repository belongs to `qbit`, and git refuses it for root ("dubious ownership"). Do not add a `safe.directory` exception.

```bash
# 1. update the code (no local changes expected; untracked build files are fine)
sudo -u qbit git -C /home/qbit/qdb-qscore status -sb | head -5
sudo -u qbit git -C /home/qbit/qdb-qscore pull --ff-only origin main
sudo -u qbit git -C /home/qbit/qdb-qscore log --oneline -1

# 2. build (third_party/ is already there; on a new machine run ./get_deps.sh first)
sudo -u qbit bash -c 'cd /home/qbit/qdb-qscore/build && cmake -DCMAKE_BUILD_TYPE=Release .. && make -j"$(nproc)"'
```

CMake writes the binary to `x64/Release/QSCore`, but the service runs `build/QSCore`:

```bash
cd /home/qbit/qdb-qscore
cp build/QSCore build/QSCore.bak                                  # for rollback
sudo -u qbit install -m 755 x64/Release/QSCore build/QSCore
systemctl restart qscore
```

Check:

```bash
systemctl status qscore | head -5                                 # active (running), new start time
tail -5 /home/qbit/qdb-qscore/build/qs-core.log                   # DAP Server started on [78.47.44.63:5555]
```

- QSCore writes its log to `build/qs-core.log` (overwritten at every start); `journalctl -u qscore` has only its console output.
- From VS Code desktop: Run or Debug on a sample; the Debug Console shows `QSCORE v<version>` (`Version.h`).
- `on_accept ... WebSocket handshake Connection field is missing` in the journal is not an error of a release: something connected to port 5556 without a WebSocket handshake (scanners).

Rollback: `cp build/QSCore.bak build/QSCore && systemctl restart qscore`.

Configuration (`build/QSCore.ini`, kept by the build): `python.exec.endpoint` (the executor), `source.folder` (`/var/dap/`), `log.level`.

## dapp (file upload)

`/home/admin/work/dapp` is not a clone: copy `app.py` from the updated clone of `qbit`.

```bash
sudo -u qbit git -C /home/qbit/qdb-qscore pull --ff-only origin main
cd /home/admin/work/dapp
cp app.py app.py.bak                                              # for rollback
diff app.py /home/qbit/qdb-qscore/scripts/dapp/app.py | head -40  # changes made on the server? keep them in git first
cp /home/qbit/qdb-qscore/scripts/dapp/app.py app.py
chown admin:admin app.py
systemctl restart dapp
journalctl -u dapp -n 20
```

- Do not overwrite `dap-files.properties` on the server: it has the server's folders (`mainFolder=/var/dap`, `imageFolder=/var/dap/images`). The limits `maxFiles` (200), `maxTotalBytes` (10485760) and `sessionTtlHours` (24) are optional there; the code has the same defaults.
- Check: Run Circuit from VS Code desktop, then `journalctl -u dapp -n 30 | grep -E "Session|Uploaded file|rejected"` shows `Session <id>: N file(s), M bytes`.
- Logs: `journalctl -u dapp` and `/home/admin/work/dapp/logs/server-*.log`.
- Local tests (no server): `python3 scripts/dapp/test_dapp_local.py`.

Rollback: `cp app.py.bak app.py && systemctl restart dapp`.

## qdb-decom (Python executor)

The executor runs desktop users' Python programs in its own environment, so every package a program imports must be installed there (there is no per-project venv on the server). Current environment: qiskit 1.3.2 and qiskit-aer.

```bash
PY=/home/qbit/qdb-decom/my-venv/bin/python
$PY -m pip list | grep -i -E "qiskit|numpy|matplotlib|pylatexenc|cudaq"
sudo -u qbit $PY -m pip install <package> "qiskit==1.3.2"         # keep qiskit pinned
systemctl restart qdb-decom
journalctl -u qdb-decom -n 10
```

- `matplotlib` and `pylatexenc` are needed for the circuit image; `cudaq` for CUDA-Q Python programs.
- Studio workspaces use qiskit 2.5.2 and qiskit-aer 0.17.2; programs that run there may behave differently here until the versions are aligned.
- The executor code on the server (`server2.py`) is not in this repository yet; put it under `scripts/qdb-decom/` before changing it.

## Release checklist

1. Merge into `main`; bump `Version.h` for QSCore changes.
2. QSCore changed (`*.cpp`, `*.h`, `processors/`, `qvm/`, `dap/`): section QSCore.
3. `scripts/dapp/` changed: section dapp.
4. New Python packages needed by programs: section qdb-decom.
5. Check from VS Code desktop (Debug Console shows the new QSCore version).
6. Studio workspaces get QSCore with the next workspace image (`--build-arg QSCORE_REF=<commit>`, `backend/docs/release_guide.md` in quantag-studio).

"""Local tests of the upload service (app.py) with the Flask test client.

Runs app.py in a temporary folder with its own dap-files.properties (data folder ./data,
image folder ./data/images as on the server, small limits); nothing is sent to a server.

    python3 test_dapp_local.py
"""
import base64
import importlib.util
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORK = Path(tempfile.mkdtemp(prefix="dapp-test-"))
os.chdir(WORK)
(WORK / "dap-files.properties").write_text("mainFolder=./data\nimageFolder=./data/images\nmaxFiles=5\nmaxTotalBytes=1000\nsessionTtlHours=1\n")

spec = importlib.util.spec_from_file_location("dapp_app", HERE / "app.py")
dapp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dapp)
client = dapp.app.test_client()
DATA = Path(dapp.MAIN_FOLDER).resolve()


def b64(text):
    return base64.b64encode(text.encode()).decode()


def submit(session, files):
    return client.post("/public/submitFiles", json={"sessionId": session, "files": files, "opts": {"mode": "desktop"}})


PASSED, FAILED = [], []


def case(name):
    def wrap(fn):
        try:
            fn()
            PASSED.append(name)
            print("OK  ", name)
        except Exception as error:  # noqa: BLE001
            FAILED.append(name)
            print("FAIL", name, "-", repr(error))
        return fn
    return wrap


@case("files are stored under the session folder, with an empty file")
def _():
    r = submit("s1", [{"path": "pkg/main.py", "source": b64("print(1)\n")},
                      {"path": "pkg/__init__.py", "source": ""}])
    assert r.status_code == 200, r.get_json()
    assert r.get_json()["count"] == 2
    assert (DATA / "s1/pkg/main.py").read_text() == "print(1)\n"
    assert (DATA / "s1/pkg/__init__.py").read_bytes() == b""
    assert (DATA / "s1" / dapp.SESSION_MARKER).is_file()


@case("a second upload replaces the session folder")
def _():
    r = submit("s1", [{"path": "other.py", "source": b64("x = 1\n")}])
    assert r.status_code == 200
    assert not (DATA / "s1/pkg/main.py").exists()
    assert (DATA / "s1/other.py").exists()


@case("missing source names the file, nothing is written")
def _():
    r = submit("s2", [{"path": "a.py", "source": b64("a")}, {"path": "b.py"}])
    body = r.get_json()
    assert r.status_code == 400 and body["path"] == "b.py" and "source" in body["message"], body
    assert not (DATA / "s2").exists()


@case("invalid base64 names the file")
def _():
    r = submit("s3", [{"path": "bad.py", "source": "not base64!!"}])
    body = r.get_json()
    assert r.status_code == 400 and body["path"] == "bad.py" and "base64" in body["message"], body


@case("too many files: 413 with the count and the limit")
def _():
    r = submit("s4", [{"path": f"f{i}.py", "source": ""} for i in range(6)])
    body = r.get_json()
    assert r.status_code == 413 and "6" in body["message"] and "5" in body["message"], body
    assert not (DATA / "s4").exists()


@case("files larger than the limit in total: 413 naming the file that crossed it")
def _():
    r = submit("s5", [{"path": "a.py", "source": b64("a" * 600)}, {"path": "b.py", "source": b64("b" * 600)}])
    body = r.get_json()
    assert r.status_code == 413 and body["path"] == "b.py", body
    assert not (DATA / "s5").exists()


@case("request body over the size limit: 413 JSON")
def _():
    r = submit("s6", [{"path": "big.py", "source": b64("x" * 4000)}])
    assert r.status_code == 413 and r.get_json()["code"] == 1, r.data[:200]


@case("unsafe session ids are rejected and nothing is cleared")
def _():
    (DATA / "keep.txt").write_text("keep")
    for sid in ("", ".", "..", "../x", "a/b", "images"):
        r = submit(sid, [{"path": "a.py", "source": ""}])
        assert r.status_code == 400, (sid, r.status_code, r.get_json())
    assert (DATA / "keep.txt").exists()


@case("path traversal in a file path stays inside the session folder")
def _():
    r = submit("s7", [{"path": "../../etc/passwd", "source": b64("x")}])
    assert r.status_code == 200, r.get_json()
    assert (DATA / "s7/etc/passwd").exists()
    assert not (WORK / "etc").exists()


@case("cleanup removes only old upload sessions")
def _():
    old = DATA / "old-session"
    old.mkdir()
    (old / dapp.SESSION_MARKER).write_text("x")
    past = time.time() - 2 * 3600
    os.utime(old / dapp.SESSION_MARKER, (past, past))
    user = DATA / "user-folder"            # prepareData folder: no marker, never removed
    user.mkdir()
    os.utime(user, (past, past))
    dapp._last_cleanup = 0.0
    r = submit("s8", [{"path": "a.py", "source": ""}])
    assert r.status_code == 200
    assert not old.exists(), "old upload session not removed"
    assert user.exists() and (DATA / "s1").exists() and Path(dapp.IMAGE_FOLDER).exists()


print("%d passed, %d failed" % (len(PASSED), len(FAILED)))
sys.exit(1 if FAILED else 0)

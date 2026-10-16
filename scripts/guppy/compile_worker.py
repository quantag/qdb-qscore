#!/usr/bin/env python3
import sys, json, base64, importlib.util
from pathlib import Path

def main():
    if len(sys.argv) < 4:
        print(json.dumps({"ok": False, "error": "Missing args"}))
        sys.exit(1)

    src_path = Path(sys.argv[1])
    func_names = json.loads(sys.argv[2])
    formats = json.loads(sys.argv[3])

    module_name = f"user_module_worker"
    spec = importlib.util.spec_from_file_location(module_name, src_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"Execution failed: {e}"}))
        sys.exit(1)

    results = {}
    for name in func_names:
        if not hasattr(mod, name):
            print(json.dumps({"ok": False, "error": f"Function '{name}' not found"}))
            sys.exit(1)
        fn = getattr(mod, name)

        try:
            compiled = fn.compile()
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"Compile failed for '{name}': {e}"}))
            sys.exit(1)

        entry = {}
        if "hugr" in formats:
            entry["hugr"] = base64.b64encode(compiled.to_bytes()).decode("ascii")
        if "str" in formats:
            try:
                entry["str"] = compiled.to_str()
            except Exception as e:
                entry["str_error"] = str(e)
        if "json" in formats and hasattr(compiled, "to_json"):
            try:
                entry["json"] = compiled.to_json()
            except Exception as e:
                entry["json_error"] = str(e)

        results[name] = entry

    print(json.dumps({"ok": True, "results": results}))

if __name__ == "__main__":
    main()

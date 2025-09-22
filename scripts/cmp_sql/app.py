# app.py
import base64
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------- Schema parsing ----------

def extract_table_fields_with_types_from_text(sql_content: str) -> Dict[str, List[Tuple[str, str]]]:
    """
    Parse CREATE TABLE definitions and return:
      { table_name: [(column_name, data_type), ...], ... }
    Notes:
      - Focused on PostgreSQL-like syntax
      - Ignores table/column constraints
    """
    tables_fields = defaultdict(list)

    # Match full CREATE TABLE blocks (with optional IF NOT EXISTS)
    create_table_blocks = re.findall(
        r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([^\s(]+)\s*\((.*?)\);',
        sql_content,
        re.DOTALL | re.IGNORECASE
    )

    for table_name, columns_block in create_table_blocks:
        table_name = table_name.strip('"')
        lines = columns_block.strip().splitlines()

        for line in lines:
            line = line.strip().rstrip(',')

            # Skip constraints
            if line.upper().startswith(('CONSTRAINT', 'PRIMARY KEY', 'UNIQUE', 'FOREIGN KEY', 'CHECK')):
                continue

            # Match column name and datatype
            match = re.match(
                r'^"?(?P<column>\w+)"?\s+'
                r'(?P<datatype>[a-zA-Z0-9_\s]+'
                r'(?:\([0-9,\s]+\))?'
                r'(?:\s+without time zone|\s+with time zone)?'
                r'(?:\[\])?)',
                line,
                re.IGNORECASE
            )

            if match:
                column_name = match.group('column')
                data_type = match.group('datatype').strip().lower()
                tables_fields[table_name].append((column_name, data_type))

    return dict(tables_fields)


def compare_sql_schemas(schema1: Dict[str, List[Tuple[str, str]]],
                        schema2: Dict[str, List[Tuple[str, str]]]) -> Dict:
    """
    Compare two schemas (as produced above) and output a structured diff.
    """
    diff = {
        "tables_only_in_db1": [],
        "tables_only_in_db2": [],
        "table_differences": {}
    }

    tables1 = set(schema1.keys())
    tables2 = set(schema2.keys())

    diff["tables_only_in_db1"] = sorted(tables1 - tables2)
    diff["tables_only_in_db2"] = sorted(tables2 - tables1)

    common_tables = tables1 & tables2

    for table in sorted(common_tables):
        fields1 = dict(schema1[table])
        fields2 = dict(schema2[table])

        fields1_keys = set(fields1.keys())
        fields2_keys = set(fields2.keys())

        added = sorted(fields2_keys - fields1_keys)
        removed = sorted(fields1_keys - fields2_keys)
        modified = sorted([
            f for f in (fields1_keys & fields2_keys)
            if fields1[f] != fields2[f]
        ])

        if added or removed or modified:
            diff["table_differences"][table] = {
                "fields_exist_in_db2_only": {f: fields2[f] for f in added},
                "fields_exist_in_db1_only": {f: fields1[f] for f in removed},
                "fields_exist_in_db1_and_db2_but_difference": {
                    f: {
                        "data_type_in_db1": fields1[f],
                        "data_type_in_db2": fields2[f]
                    } for f in modified
                }
            }

    return diff

# ---------- Helpers ----------

def b64_to_text(b64_str: str) -> str:
    try:
        return base64.b64decode(b64_str).decode("utf-8", errors="strict")
    except Exception as e:
        raise ValueError(f"Invalid base64 or non-UTF8 content: {e}")

# ---------- Routes ----------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": 0}), 200

@app.route("/compare", methods=["POST"])
def compare():
    """
    Request JSON:
      {
        "db1_b64": "<base64 of SQL>",
        "db2_b64": "<base64 of SQL>"
      }

    Response JSON: schema diff structure.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    db1_b64 = data.get("db1_b64")
    db2_b64 = data.get("db2_b64")

    if not db1_b64 or not db2_b64:
        return jsonify({"error": "Both db1_b64 and db2_b64 are required"}), 400

    try:
        sql1 = b64_to_text(db1_b64)
        sql2 = b64_to_text(db2_b64)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    # Parse and compare
    schema1 = extract_table_fields_with_types_from_text(sql1)
    schema2 = extract_table_fields_with_types_from_text(sql2)
    diff = compare_sql_schemas(schema1, schema2)

    return jsonify(diff), 200

if __name__ == "__main__":
    # For local dev only. Use a proper WSGI server in production (gunicorn, uWSGI).
    app.run(host="0.0.0.0", port=5035, debug=False)

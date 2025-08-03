import base64
import os
import json
import traceback
import tiktoken
from split import split_openqasm_into_chunks
from app_config import model_limits
from openai import BadRequestError

from flask import Flask, request, jsonify
from openai import OpenAI
from join import join_optimized_chunks
from process import process_qasm_base64
from app_config import api_key, model_name, temperature, max_tokens, model_limits, system_prompt

import re
import logging
import requests

def extract_qasm_only(text: str) -> str:
    # Remove Markdown code block markers if present
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = "\n".join(text.splitlines()[1:-1])  # remove first and last lines

    lines = text.splitlines()

    # Remove leading junk until OPENQASM found
    while lines and not lines[0].strip().lower().startswith("openqasm"):
        lines.pop(0)

    # Collect QASM lines and stop on suspicious non-code
    qasm_lines = []
    for line in lines:
        # Stop if we encounter trailing markdown
        if line.strip().startswith("```"):
            break
        qasm_lines.append(line)

    return "\n".join(qasm_lines).strip()


LOG_FILE = "aiqasm.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="ascii"),
        logging.StreamHandler()  # Keep console logging too if needed
    ]
)
# Set log level for third-party libraries
logging.getLogger("openai").setLevel(logging.INFO)      # Show info, hide debug
logging.getLogger("httpx").setLevel(logging.WARNING)    # Suppress verbose HTTP logs
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = Flask(__name__)
app.logger = logging.getLogger("aiqasm")




# Load model cost information
try:
    with open("model_costs.json", "r") as f:
        MODEL_COSTS = json.load(f)
except FileNotFoundError:
    MODEL_COSTS = {}
    app.logger.warning("model_costs.json not found. Cost calculation disabled.")


SYSTEM_PROMPT = "You are an expert in quantum computing. Optimize the given OpenQASM code for fewer gates and depth, preserving its logic. Return valid OpenQASM code only."
client = OpenAI(api_key=api_key)

@app.route("/optimize", methods=["POST"])
def optimize_qasm():
    try:      
        data = request.json

        if "qasm" not in data:
            app.logger.warning("Missing 'qasm' in request")
            return jsonify({"error": "Missing 'qasm' field"}), 400

        qasm_code = base64.b64decode(data["qasm"]).decode("utf-8")
        # === Token counting ===
        try:
            enc = tiktoken.encoding_for_model(model_name)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")

        input_tokens = len(enc.encode(qasm_code))

        app.logger.info(f"Using temperature={temperature} for optimization.")
#        app.logger.debug(f"Original QASM:\n{qasm_code}")
        model_limit = model_limits.get(model_name, 16000)

        # Compute available token space for input
        max_input_tokens = model_limit - max_tokens

        if input_tokens > max_input_tokens:
            app.logger.warning("QASM input too large for selected model.")
            return jsonify({
                "error": "Input too large for model context window.",
                "input_tokens": input_tokens,
                "max_allowed_input_tokens": max_input_tokens,
                "model_token_limit": model_limit,
                "max_tokens": max_tokens
            }), 400

        app.logger.info(f"Using model: {model_name}")
        app.logger.info(f"QASM input tokens: {input_tokens} / allowed max: {max_input_tokens} (model limit: {model_limit}, max_tokens: {max_tokens})")
        app.logger.info("Calling OpenAI to optimize QASM...")


        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": qasm_code}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        optimized_qasm = response.choices[0].message.content.strip()
        optimized_qasm = extract_qasm_only(optimized_qasm)
        optimized_b64 = base64.b64encode(optimized_qasm.encode("utf-8")).decode("utf-8")

       # Token usage and cost
        usage = response.usage
        input_tokens_used = usage.prompt_tokens
        output_tokens_used = usage.completion_tokens
        total_tokens_used = usage.total_tokens

        cost_info = MODEL_COSTS.get(model_name, {})
        cost_input = cost_info.get("input", 0)
        cost_output = cost_info.get("output", 0)

        total_cost = (input_tokens_used * cost_input + output_tokens_used * cost_output) / 1000

        app.logger.info(f"Used tokens: input={input_tokens_used}, output={output_tokens_used}, total={total_tokens_used}")
        app.logger.info(f"Estimated cost: ${total_cost:.6f}")


        #app.logger.debug(f"Optimized QASM:\n{optimized_qasm}")
        return jsonify({"qasm": optimized_b64,             
                "tokens": {
                  "input": input_tokens_used,
                  "output": output_tokens_used,
                  "total": total_tokens_used
                   },
                "cost_usd": round(total_cost, 6)})

    except BadRequestError as e:
        if "context length" in str(e).lower() or "maximum context length" in str(e).lower():
            app.logger.error("Input too large for selected model context window.")
            app.logger.error(traceback.format_exc())
            return jsonify({
                "error": "Input too large for model. Consider using a smaller .qasm file or switching to a larger-context model like gpt-4o."
            }), 400
        else:
            app.logger.error("Bad request to OpenAI API.")
            app.logger.error(traceback.format_exc())
            return jsonify({"error": f"OpenAI API bad request: {str(e)}"}), 400

    except Exception as e:
        app.logger.error("Exception during optimization:")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500


@app.route("/split", methods=["POST"])
def split_qasm():
    try:
        data = request.json

        if "qasm" not in data:
            return jsonify({"error": "Missing 'qasm' field"}), 400

        qasm_b64 = data["qasm"]
        model_name = data.get("model")

        # Decode input QASM
        qasm_code = base64.b64decode(qasm_b64).decode("utf-8")
        chunks = split_openqasm_into_chunks(qasm_code, model_name)

        return jsonify({
            "chunk_count": len(chunks),
            "chunks": [base64.b64encode(c.encode("utf-8")).decode("ascii") for c in chunks]
        })

    except Exception as e:
        app.logger.error("Exception in /split endpoint:")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/join", methods=["POST"])
def join_qasm_chunks():
    try:
        data = request.json

        if "chunks_b64" not in data or not isinstance(data["chunks_b64"], list):
            return jsonify({"error": "Missing or invalid 'chunks_b64' field"}), 400

        # Decode all chunks
        chunks = []
        for idx, chunk_b64 in enumerate(data["chunks_b64"]):
            try:
                chunk_str = base64.b64decode(chunk_b64).decode("utf-8")
                chunks.append(chunk_str)
            except Exception as e:
                app.logger.error(f"Failed to decode chunk {idx}: {e}")
                return jsonify({"error": f"Invalid base64 encoding in chunk {idx}"}), 400

        app.logger.info(f"Joining {len(chunks)} QASM chunks...")

        joined_qasm = join_optimized_chunks(chunks)
        joined_b64 = base64.b64encode(joined_qasm.encode("utf-8")).decode("ascii")

        return jsonify({
            "joined_qasm_b64": joined_b64,
            "lines": len(joined_qasm.splitlines())
        })

    except Exception as e:
        app.logger.exception("Exception during join endpoint")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

@app.route("/process", methods=["POST"])
def process_qasm_endpoint():
    try:
        data = request.json

        if "qasm_b64" not in data:
            app.logger.warning("Missing 'qasm_b64' in request")
            return jsonify({"error": "Missing 'qasm_b64' field"}), 400

        qasm_b64 = data["qasm_b64"]
        model = data.get("model", "gpt-4o")

        app.logger.info(f"Received process request for model: {model}")
        result = process_qasm_base64(qasm_b64, model)

        return jsonify({
            "mode": result["mode"],
            "temp_dir": result["temp_dir"],
            "optimized_qasm_b64": result["optimized_qasm_b64"]
        })

    except requests.exceptions.RequestException as e:
        app.logger.error("API call failed:")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Request failed: {str(e)}"}), 500

    except Exception as e:
        app.logger.error("Unexpected error during processing:")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/tokens", methods=["POST"])
def count_tokens():
    try:
        data = request.get_json(force=True)

        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON object"}), 400

        qasm_b64 = data.get("qasm_b64")
        model = data.get("model")

        if not qasm_b64 or not model:
            return jsonify({"error": "Missing 'qasm_b64' or 'model'"}), 400

        qasm_code = base64.b64decode(qasm_b64).decode("utf-8")

        enc = tiktoken.encoding_for_model(model)
        token_count = len(enc.encode(qasm_code))
        return jsonify({"tokens": token_count})

    except Exception as e:
        app.logger.exception("Failed to count tokens")
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)  # Set to INFO or WARNING in prod
    app.run(debug=True, port=9999)

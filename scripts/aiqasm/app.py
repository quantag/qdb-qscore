import base64
import os
import json
import traceback
import tiktoken
from split import split_openqasm_into_chunks
from app_config import MODEL_LIMITS
from openai import BadRequestError

from flask import Flask, request, jsonify
from openai import OpenAI

import re
import logging


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

# === Load API key from config.json ===
CONFIG_PATH = "config.json"
if not os.path.exists(CONFIG_PATH):
    print("ERROR: config.json not found. Please create it before starting the server.")
    sys.exit(1)

with open(CONFIG_PATH, "r") as f:
    config = json.load(f)
    api_key = config.get("openai_api_key")
    model_name = config.get("openai_model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.2)
    max_tokens = config.get("max_tokens", 2000)



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
        model_limit = MODEL_LIMITS.get(model_name, 16000)

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


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.DEBUG)  # Set to INFO or WARNING in prod
    app.run(debug=True, port=9999)

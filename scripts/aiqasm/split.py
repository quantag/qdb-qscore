import re
import tiktoken
import logging

from typing import List

from app_config import MODEL_LIMITS


def split_openqasm_into_chunks(qasm_code: str, model_name: str) -> List[str]:
    if model_name not in MODEL_LIMITS:
        raise ValueError(f"Unknown model name: {model_name}")

    max_tokens_per_chunk = MODEL_LIMITS[model_name]
    logging.info(f"For model '{model_name}', maximum chunk size is {max_tokens_per_chunk} tokens.")

    enc = tiktoken.encoding_for_model(model_name)

    # Extract and preserve global headers (OPENQASM, include, qreg/creg)
    global_lines = []
    body_lines = []

    for line in qasm_code.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if re.match(r"^(OPENQASM|include|qreg|creg)", line):
            global_lines.append(line)
        else:
            body_lines.append(line)

    chunks = []
    current_chunk = []
    current_token_count = len(enc.encode("\n".join(global_lines)))

    for line in body_lines:
        line_tokens = len(enc.encode(line))
        if current_token_count + line_tokens > max_tokens_per_chunk:
            chunk = "\n".join(global_lines + current_chunk)
            chunks.append(chunk)
            current_chunk = [line]
            current_token_count = len(enc.encode("\n".join(global_lines))) + line_tokens
        else:
            current_chunk.append(line)
            current_token_count += line_tokens

    if current_chunk:
        chunk = "\n".join(global_lines + current_chunk)
        chunks.append(chunk)

    return chunks
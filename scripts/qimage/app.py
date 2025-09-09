import io
import base64
import tempfile
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify
from qimg5_compression import (
    load_grayscale_image,
    normalize_to_amplitudes,
    perform_qpca,
    reconstruct_image,
    auto_levels,
    compute_mse
)
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

#app = Flask(__name__)

def image_to_base64(img_array):
    img = Image.fromarray(img_array)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

@app.route('/process', methods=['POST'])
def process_image():
    try:
        data = request.get_json()
        img_b64 = data.get("image")
        if not img_b64:
            return jsonify({"error": "Missing 'image' field"}), 400

        image_bytes = base64.b64decode(img_b64)
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            f.write(image_bytes)
            f.flush()
            img_data = load_grayscale_image(f.name)

        amplitudes, shape = normalize_to_amplitudes(img_data)
        eigvals, components = perform_qpca(amplitudes)

        total_energy = np.sum(eigvals)
        cumulative = np.cumsum(eigvals)
        compressed_k = np.searchsorted(cumulative, 0.95 * total_energy) + 1

        recon_full = reconstruct_image(components, eigvals, shape)
        recon_compressed = reconstruct_image(components, eigvals, shape, k=compressed_k)

        mse = compute_mse(img_data, recon_compressed)

        response = {
            "reconstructed": image_to_base64(auto_levels(recon_full.astype(float))),
            "compressed": image_to_base64(auto_levels(recon_compressed.astype(float))),
            "mse": mse,
            "overlays": []
        }

        for i in range(min(6, len(components))):
            comp_img = components[i].reshape(shape)
            scaled = (comp_img - comp_img.min()) / (comp_img.max() - comp_img.min() + 1e-9) * 255
            overlay_b64 = image_to_base64(scaled.astype(np.uint8))
            response["overlays"].append(overlay_b64)

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5030, debug=True)

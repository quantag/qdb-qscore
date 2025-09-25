from flask import Flask, request, jsonify
import pandas as pd
from quantag import QAOASolver
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def filter_assets(assets, selected, budget=4):
    """
    Post-process: if solver selects too many assets,
    keep only the top-N by return/risk ratio.
    """
    if len(selected) > budget:
        scores = {
            a["asset"]: (a["returns"] / (a["risk"] + 1e-6))
            for a in assets
        }
        top_assets = sorted(selected, key=lambda x: scores.get(x, 0), reverse=True)[:budget]
        return top_assets
    return selected

@app.route("/solve", methods=["POST"])
def solve():
    try:
        data = request.get_json()

        # Input options: CSV text or JSON array
        if "csv" in data:
            from io import StringIO
            df = pd.read_csv(StringIO(data["csv"]))
        elif "data" in data:
            df = pd.DataFrame(data["data"])
        else:
            return jsonify({"status": "error", "error": "No data provided"}), 400

        assets = list(df["asset"])
        solver = QAOASolver(backend=data.get("backend", "dwave"))

        # Save temp CSV for solver
        csv_file = "/tmp/portfolio.csv"
        df.to_csv(csv_file, index=False)

        result = solver.solve(csv_file, problem="portfolio")

        # Extract solver output
        if hasattr(result, "first"):
            best_sample = result.first.sample
            energy = result.first.energy
            chosen_assets = [
                assets[i] for i, bit in enumerate(best_sample.values()) if bit == 1
            ]
        else:
            best_sample = result.iloc[0, :-2].to_dict()
            energy = result.iloc[0]["energy"]
            chosen_assets = [
                assets[i] for i, bit in enumerate(best_sample.values()) if bit == 1
            ]

        # Build asset dicts for scoring
        asset_dicts = [
            {"asset": assets[i], "returns": float(df.iloc[i]["returns"]), "risk": float(df.iloc[i]["risk"])}
            for i in range(len(assets))
        ]

        # Apply filter to limit portfolio size (for demo)
        chosen_assets = filter_assets(asset_dicts, chosen_assets, budget=data.get("budget", 4))

        return jsonify({
            "status": "ok",
            "selected_assets": chosen_assets,
            "energy": energy
        })

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5041, debug=True)

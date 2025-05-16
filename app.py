from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import subprocess
import os

app = Flask(__name__)

# === Config Paths ===
CSV_PATH = "CSVs/speed_gear.csv"
CONFIG_PATH = "scan_config.json"
SCANNER_PATH = "speed_scanner.py"

# === Utility ===
def load_csv():
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    return pd.DataFrame()

# === Routes ===
@app.route("/")
def index():
    data = load_csv().to_dict(orient="records")
    return render_template("index.html", table_data=data)

@app.route("/scan", methods=["POST"])
def run_scan():
    config = request.json
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    try:
        result = subprocess.run(
            ["python", SCANNER_PATH, "--config", CONFIG_PATH],
            capture_output=True,
            text=True,
            check=True
        )
        return jsonify({"success": True, "stdout": result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({"success": False, "error": e.stderr})

@app.route("/reload")
def reload_csv():
    df = load_csv()
    return jsonify(df.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import subprocess
import os
import sys

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
    raw = request.json
    
    # --- Sanitize FILTER_TYPE ---
    valid_filter_values = {
        "Haste", "Crit", "Vers", "Mastery", "Speed", "Prismatic",
        "Max-Haste", "Max-Crit", "Max-Vers", "Max-Mastery"
    }
    raw["FILTER_TYPE"] = [
        f for f in raw.get("FILTER_TYPE", []) if f in valid_filter_values
    ]
    
    if not isinstance(raw.get("FILTER_TYPE"), list):
        raw["FILTER_TYPE"] = []

    print("\n📥 Received scan config:")
    print(json.dumps(raw, indent=2))

    # === Convert UI config to full SCAN_PROFILE ===
    try:
        ilvl_min = int(raw.get("min_ilvl") or raw.get("MIN_ILVL") or 0)
        ilvl_max = int(raw.get("max_ilvl") or raw.get("MAX_ILVL") or 1000)
        max_buyout = int(raw.get("max_buyout") or raw.get("MAX_BUYOUT") or 99999999)

        stat_thresholds = raw.get("STAT_DISTRIBUTION_THRESHOLDS") or {
            "Haste": 71 if raw.get("haste") else 0,
            "Crit": 71 if raw.get("crit") else 0,
            "Vers": 71 if raw.get("vers") else 0,
            "Mastery": 71 if raw.get("mastery") else 0,
            "Speed": 71 if raw.get("speed") else 0
        }

        profile = {
            "MIN_ILVL": ilvl_min,
            "MAX_ILVL": ilvl_max,
            "MAX_BUYOUT": max_buyout,
            "FILTER_TYPE": raw.get("FILTER_TYPE", []),
            "STAT_DISTRIBUTION_THRESHOLDS": stat_thresholds,
            "ALLOWED_ARMOR_SLOTS": [s for s in raw.get("slots", []) if s in [
                "Head", "Shoulder", "Chest", "Waist", "Legs", "Feet", "Back", "Wrist", "Hands"]],
            "ALLOWED_WEAPON_SLOTS": [s for s in raw.get("slots", []) if s in [
                "One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Held In Off-hand", "Ranged", "Ranged Right"]],
            "ALLOWED_ACCESSORY_SLOTS": [s for s in raw.get("slots", []) if s in [
                "Finger", "Trinket", "Neck", "Held In Off-hand"]],
            "ALLOWED_ARMOR_TYPES": raw.get("ALLOWED_ARMOR_TYPES") or raw.get("armor_types", []),
            "ALLOWED_WEAPON_TYPES": raw.get("ALLOWED_WEAPON_TYPES") or raw.get("weapon_types", []),
            "slots": raw.get("slots", []),
            "scan_mode": raw.get("scan_mode", "all"),
            "realm": raw.get("realm", None),
        }

        # Write transformed profile
        with open(CONFIG_PATH, "w") as f:
            json.dump(profile, f, indent=2)
            print(f"💾 Saved scan profile to {CONFIG_PATH}")

        # Run scan
        print(f"🚀 Running: {SCANNER_PATH} --config {CONFIG_PATH}\n")
        result = subprocess.run(
            ["python", SCANNER_PATH, "--config", CONFIG_PATH],
            stdout=sys.stdout,
            stderr=sys.stderr,
            text=True,
            encoding="utf-8",
            check=True
        )
        # Load results to check if CSV is empty
        df = pd.read_csv(CSV_PATH)
        if df.empty:
            print("Scan completed but returned no matching results.")
            return jsonify({"success": True, "no_results": True})
        
        # Print scan results
        print(result.stdout)
        if result.stderr:
            print("❌ stderr:", result.stderr)
        print("✅ Scan completed successfully")
        return jsonify({"success": True})

    except Exception as e:
        print(f"❌ Scan failed due to error: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route("/reload")
def reload_csv():
    df = load_csv()
    return jsonify(df.to_dict(orient="records"))

if __name__ == "__main__":
    app.run(debug=True)
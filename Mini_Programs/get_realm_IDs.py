import os
import csv
import requests
from dotenv import load_dotenv

# === Config ===
load_dotenv()
CLIENT_ID = os.getenv("BLIZZARD_CLIENT_ID")
CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")

REGION = "us"
LOCALE = "en_US"
NAMESPACE = "dynamic-us"
TOKEN_URL = f"https://{REGION}.battle.net/oauth/token"
CONNECTED_REALMS_URL = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/index"

REALM_MAP_PATH = "CSVs/realm_map.csv"
CACHE_PATH = "CSVs/loaded_servers.csv"

# === Token Handler ===
def get_token():
    try:
        res = requests.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(CLIENT_ID, CLIENT_SECRET)
        )
        res.raise_for_status()
        token = res.json().get("access_token")
        print("✅ Token acquired.")
        return token
    except Exception as e:
        print(f"❌ Token error: {e}")
        exit(1)

# === Connected Realm Fetcher ===
def get_connected_realms(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "namespace": "dynamic-us",
            "locale": "en_US",
            "access_token": token
        }
        res = requests.get("https://us.api.blizzard.com/data/wow/connected-realm/index", headers=headers, params=params)
        res.raise_for_status()
        connected_realms = res.json().get("connected_realms", [])
        ids = [int(entry["href"].split("/connected-realm/")[-1].split("?")[0]) for entry in connected_realms]
        print(f"✅ Fetched {len(ids)} connected realm IDs.")
        return set(ids)
    except Exception as e:
        print(f"❌ Connected realm fetch failed: {e}")
        exit(1)

# === Load realm_map.csv for ID->Name mapping ===
def load_realm_name_map():
    name_map = {}
    if not os.path.exists(REALM_MAP_PATH):
        print(f"❌ Missing realm_map: {REALM_MAP_PATH}")
        return name_map
    with open(REALM_MAP_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = int(row["connected_realm_id"])
            name_map[rid] = row["name"]
    return name_map

# === Load loaded_servers.csv for existing entries ===
def load_existing_realm_ids():
    if not os.path.exists(CACHE_PATH):
        return set()
    with open(CACHE_PATH, newline='', encoding='utf-8') as f:
        return {int(row["realm_id"]) for row in csv.DictReader(f)}

# === Append missing realms to loaded_servers.csv ===
def append_missing_servers():
    token = get_token()
    all_realms = get_connected_realms(token)
    known_ids = load_existing_realm_ids()
    name_map = load_realm_name_map()

    print(f"\n🔍 Connected Realms Fetched from Blizzard:")
    for rid in sorted(all_realms):
        realm_name = name_map.get(rid, f"Realm-{rid}")
        print(f"🧾 Realm ID: {rid:<6} | Name: {realm_name}")

    print(f"\n📊 Total connected realm IDs fetched: {len(all_realms)}")

    missing = all_realms - known_ids
    print(f"\n📌 {len(missing)} realm(s) are missing from cache and will be added.\n")

    if not missing:
        print("✅ All realms are already listed in loaded_servers.csv.")
        return

    with open(CACHE_PATH, "a", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["realm_id", "realm_name", "last_scanned"])
        if os.stat(CACHE_PATH).st_size == 0:
            writer.writeheader()

        for rid in sorted(missing):
            realm_name = name_map.get(rid, f"Realm-{rid}")
            writer.writerow({
                "realm_id": rid,
                "realm_name": realm_name,
                "last_scanned": "0"
            })
            print(f"➕ Added to cache: Realm ID {rid} ({realm_name})")

    print(f"\n✅ Missing realms appended to {CACHE_PATH}.")

# === Main ===
if __name__ == "__main__":
    append_missing_servers()

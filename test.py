import os
import json
import requests
from dotenv import load_dotenv

# === Setup ===
load_dotenv()
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

REGION = "us"
LOCALE = "en_US"
NAMESPACE_DYNAMIC = f"dynamic-{REGION}"
TOKEN_URL = f"https://{REGION}.battle.net/oauth/token"
CONNECTED_REALM_URL = f"https://{REGION}.api.blizzard.com/data/wow/realm/caelestrasz?namespace={NAMESPACE_DYNAMIC}&locale={LOCALE}"

# === Token Handling ===
def get_token():
    try:
        res = requests.post(TOKEN_URL, data={"grant_type": "client_credentials"}, auth=(CLIENT_ID, CLIENT_SECRET))
        res.raise_for_status()
        token = res.json().get("access_token")
        print("✅ Token acquired.")
        return token
    except Exception as e:
        print(f"❌ Token error: {e}")
        exit(1)

# === Realm ID Resolver ===
def get_realm_id(token):
    try:
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(CONNECTED_REALM_URL, headers=headers)
        res.raise_for_status()
        realm_data = res.json()
        # Extract realm ID from the connected_realm.href URL
        href = realm_data["connected_realm"]["href"]
        realm_id = href.split("/connected-realm/")[-1].split("?")[0]
        print(f"✅ Caelestrasz Realm ID: {realm_id}")
        return realm_id
    except Exception as e:
        print(f"❌ Failed to resolve Caelestrasz realm ID: {e}")
        exit(1)

# === Auction Searcher ===
def fetch_auctions(realm_id, token):
    url = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/{realm_id}/auctions?namespace={NAMESPACE_DYNAMIC}&locale={LOCALE}"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        print(f"✅ Retrieved auction data.")
        return res.json().get("auctions", [])
    except Exception as e:
        print(f"❌ Auction fetch failed: {e}")
        print(f"🔎 URL: {url}")
        exit(1)

# === Auction Metadata Printer ===
def print_auction_metadata(auction):
    print(f"\n📦 Auction ID: {auction.get('id')}")
    print(json.dumps(auction, indent=4))

# === Main Flow ===
def main():
    token = get_token()
    realm_id = get_realm_id(token)

    item_id_input = input("🔍 Enter WoW Item ID to search for: ").strip()
    if not item_id_input.isdigit():
        print("❌ Invalid item ID. Must be a number.")
        return
    item_id = int(item_id_input)

    auctions = fetch_auctions(realm_id, token)
    matches = [a for a in auctions if a.get("item", {}).get("id") == item_id]

    if not matches:
        print(f"❌ No auction listings found for item ID {item_id} on Caelestrasz.")
        return

    print(f"\n✅ Found {len(matches)} auctions for item ID {item_id} on Caelestrasz.")

    for a in matches:
        print_auction_metadata(a)

if __name__ == "__main__":
    main()

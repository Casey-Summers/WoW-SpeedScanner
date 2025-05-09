import os
import json
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv

# === Setup ===
REGION = 'us'
REALM_INDEX_URL = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/index"
AUCTION_URL_TEMPLATE = f"https://{REGION}.api.blizzard.com/data/wow/connected-realm/{{realm_id}}/auctions"
ITEM_URL_TEMPLATE = f"https://{REGION}.api.blizzard.com/data/wow/item/{{item_id}}"
STATIC_NAMESPACE = f"static-{REGION}"
RAW_OUTPUT = True  # Toggle to True to show raw item API response

load_dotenv()
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

# === Get OAuth token ===
def get_token():
    resp = requests.post(
        'https://oauth.battle.net/token',
        data={'grant_type': 'client_credentials'},
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    resp.raise_for_status()
    return resp.json()['access_token']

# === Build realm map ===
def get_realm_map(headers, params):
    response = requests.get(REALM_INDEX_URL, headers=headers, params=params)
    response.raise_for_status()
    realm_urls = [r['href'] for r in response.json()['connected_realms']]

    realm_map = {}
    for url in realm_urls:
        crid = urlparse(url).path.rstrip('/').split('/')[-1]
        cr_data = requests.get(url, headers=headers, params=params).json()
        for realm in cr_data.get('realms', []):
            name = realm['name'].strip().lower()
            slug = realm['slug']
            realm_map[name] = {'id': int(crid), 'slug': slug}
    return realm_map

# === Fetch item metadata ===
def fetch_item_metadata(item_id, headers):
    params = {'namespace': STATIC_NAMESPACE, 'locale': 'en_US'}
    url = ITEM_URL_TEMPLATE.format(item_id=item_id)
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()

    if RAW_OUTPUT:
        print("\n📄 Raw Item API Response:")
        print(json.dumps(data, indent=2))

    name = data.get("name", f"Item {item_id}")
    ilvl = data.get("level")

    inventory = data.get("inventory_type")
    subclass = data.get("item_subclass")

    inventory_id = inventory.get("id") if isinstance(inventory, dict) else None
    inventory_name = inventory.get("name") if isinstance(inventory, dict) else None

    subclass_id = subclass.get("id") if isinstance(subclass, dict) else None
    subclass_name = subclass.get("name") if isinstance(subclass, dict) else None

    print("\n📦 Item Metadata")
    print(f"🧾 Item ID     : {item_id}")
    print(f"📛 Name        : {name}")
    print(f"📏 Item Level  : {ilvl}")
    print(f"🎯 Slot Type   : {inventory_name} (ID: {inventory_id})")
    print(f"⛓️  Armor Type  : {subclass_name} (ID: {subclass_id})")
    print("-" * 60)

# === Main ===
def main():
    item_id_input = input("Enter the WoW item ID to search: ").strip()
    realm_input = "caelestrasz"

    if not item_id_input.isdigit():
        print("❌ Item ID must be a number.")
        return
    item_id = int(item_id_input)

    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    params = {'namespace': f'dynamic-{REGION}', 'locale': 'en_US'}

    print("🔄 Fetching realm info...")
    realm_map = get_realm_map(headers, params)
    if realm_input not in realm_map:
        print(f"❌ Realm '{realm_input}' not found.")
        return
    realm_id = realm_map[realm_input]['id']
    print(f"✅ Using realm '{realm_input.title()}' (ID {realm_id})")

    print("🔄 Fetching auction data...")
    auction_url = AUCTION_URL_TEMPLATE.format(realm_id=realm_id)
    response = requests.get(auction_url, headers=headers, params=params)
    response.raise_for_status()
    auctions = response.json().get('auctions', [])

    found = False
    for auction in auctions:
        if auction.get('item', {}).get('id') == item_id:
            print("\n✅ Found auction. Retrieving item metadata...")
            fetch_item_metadata(item_id, headers)
            found = True
            break

    if not found:
        print("❌ No auctions found for that item ID.")

if __name__ == '__main__':
    main()

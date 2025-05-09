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

load_dotenv()
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

# Known suffix mappings
SUFFIX_MAP = {
    669: 'of the Aurora', 40: 'of the Fireflash', 41: 'of the Feverflare',
    42: 'of the Harmonious', 43: 'of the Peerless', 44: 'of the Quickblade',
    45: 'of the Savant', 46: 'of the Seer', 47: 'of the Soldier',
    48: 'of the Strategist', 1708: 'of the Quickblade', 1709: 'of the Aurora',
    1710: 'of the Fireflash', 1711: 'of the Aurora', 1712: 'of the Harmonious',
    1713: 'of the Peerless'
}

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

# === Main ===
def main():
    item_id_input = input("Enter the WoW item ID to search: ").strip()
    realm_input = input("Enter realm name (e.g. Caelestrasz): ").strip().lower()

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
    print(f"✅ Using realm '{realm_input.title()}' (ID {realm_id})\n")

    print("🔄 Fetching auction data...")
    auction_url = AUCTION_URL_TEMPLATE.format(realm_id=realm_id)
    response = requests.get(auction_url, headers=headers, params=params)
    response.raise_for_status()
    auctions = response.json().get('auctions', [])

    matches = []
    for auction in auctions:
        auction_item = auction.get('item', {})
        if auction_item.get('id') != item_id:
            continue

        bonus_lists = auction.get('bonus_lists', [])
        suffix = ''
        for bonus_id in bonus_lists:
            if bonus_id in SUFFIX_MAP:
                suffix = SUFFIX_MAP[bonus_id]
                break

        auction_data = auction.copy()
        auction_data['suffix_name'] = suffix
        matches.append(auction_data)


    if not matches:
        print("❌ No auctions found for that item ID.")
        return

    print(f"✅ Found {len(matches)} matching auctions for item ID {item_id}:\n")

    for i, auction in enumerate(matches, start=1):
        print(f"🔹 Auction #{i}:")
        print(json.dumps(auction, indent=2))


if __name__ == '__main__':
    main()

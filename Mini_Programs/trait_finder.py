import os
import json
import requests
import random
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

# === Auth ===
def get_token():
    resp = requests.post(
        'https://oauth.battle.net/token',
        data={'grant_type': 'client_credentials'},
        auth=(CLIENT_ID, CLIENT_SECRET)
    )
    resp.raise_for_status()
    return resp.json()['access_token']

# === Main ===
def main():
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    params = {'namespace': f'dynamic-{REGION}', 'locale': 'en_US'}

    # Get all realm URLs
    index_resp = requests.get(REALM_INDEX_URL, headers=headers, params=params)
    index_resp.raise_for_status()
    realm_urls = [r['href'] for r in index_resp.json()['connected_realms']]

    # Choose a random realm and extract numeric ID
    random_realm_url = random.choice(realm_urls)
    path = urlparse(random_realm_url).path
    realm_id = path.rstrip('/').split('/')[-1]
    print(f"Using realm ID: {realm_id}\n")

    # Get auctions from the selected realm
    auction_url = AUCTION_URL_TEMPLATE.format(realm_id=realm_id)
    auc_resp = requests.get(auction_url, headers=headers, params=params)
    auc_resp.raise_for_status()
    auctions = auc_resp.json().get('auctions', [])

    if not auctions:
        print("No auctions found.")
        return

    # Pick one item
    item = auctions[0]
    print("=== Auction Data ===")
    print(json.dumps(item, indent=2))

    # Fetch full item info
    item_id = item['item']['id']
    item_url = ITEM_URL_TEMPLATE.format(item_id=item_id)
    item_resp = requests.get(item_url, headers=headers, params={'namespace': f'static-{REGION}', 'locale': 'en_US'})
    item_resp.raise_for_status()
    print("\n=== Item Info ===")
    print(json.dumps(item_resp.json(), indent=2))

if __name__ == '__main__':
    main()
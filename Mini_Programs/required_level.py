import os
import json
import requests
from dotenv import load_dotenv

# === Blizzard API setup ===
REGION = 'us'
ITEM_URL_TEMPLATE = f"https://{REGION}.api.blizzard.com/data/wow/item/{{item_id}}"

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

# === Fetch item metadata ===
def fetch_item_metadata(item_id, token):
    headers = {'Authorization': f'Bearer {token}'}
    params = {'namespace': f'static-{REGION}', 'locale': 'en_US'}
    url = ITEM_URL_TEMPLATE.format(item_id=item_id)
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# === Main ===
def main():
    item_id_input = input("Enter the WoW item ID to check: ").strip()
    if not item_id_input.isdigit():
        print("❌ Item ID must be numeric.")
        return
    item_id = int(item_id_input)

    print("🔄 Getting token and fetching item metadata...")
    token = get_token()
    metadata = fetch_item_metadata(item_id, token)

    print("\n📦 Raw Metadata:\n")
    print(json.dumps(metadata, indent=2))

    print("\n🔍 Required Level Info:")
    required_level = metadata.get("requirements", {}).get("level", {}).get("value")
    fallback_level = metadata.get("required_level")

    if required_level is not None:
        print(f"✅ Exact Required Level: {required_level}")
    elif fallback_level is not None:
        print(f"⚠️ Fallback Required Level: {fallback_level}")
    else:
        print("❌ Required level not found in metadata.")

if __name__ == '__main__':
    main()

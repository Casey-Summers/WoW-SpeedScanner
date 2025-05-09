"""
speed_scanner.py

Scans World of Warcraft auction houses for items with the 'Speed' stat bonus.
Fetches item and auction data from Blizzard's API, applies bonus adjustments,
and writes matching results to a CSV file.

Usage:
    python speed_scanner.py
"""

import os  # Interact with the operating system (file paths, environment variables)
import time  # Handle timing and delays between API requests
import json  # Parse and write JSON data
import logging  # Log progress and warnings
import requests  # Make HTTP requests to Blizzard and Raidbots APIs
import csv  # Read and write CSV files
from urllib.parse import urlparse  # Parse URLs for realm mapping
from dotenv import load_dotenv  # Load environment variables from a .env file
from tqdm import tqdm  # Display progress bars for realm scanning
import re  # Regular expressions for parsing item level strings

FILTER_TYPE = []
ALLOWED_ARMOR_SLOTS = []
ALLOWED_WEAPON_SLOTS = []
ALLOWED_ACCESSORY_SLOTS = []
ALLOWED_SLOTS = []
ALLOWED_ARMOR_TYPES = []
ALLOWED_WEAPON_TYPES = []
ALLOWED_TYPES = []

# === SCAN PROFILE DEFINITIONS ===
SCAN_PROFILES = {
    "full": {
        # Filters by different armour bonuses
        # E.g. any combination of ["Speed", "Prismatic", "Haste"]
        "FILTER_TYPE": ["Speed"],

        # Defines the allowed item slots for filtering
        # E.g. ["Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet"]
        "ALLOWED_ARMOR_SLOTS": ["Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet"],
        # E.g. ["One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Ranged"]
        "ALLOWED_WEAPON_SLOTS": ["One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Ranged"],
        # E.g. ["Finger", "Trinket", "Held In Off-hand", "Neck"]
        "ALLOWED_ACCESSORY_SLOTS": ["Finger", "Trinket", "Held In Off-hand", "Neck"],

        # Defines the allowed armor types for filtering
        # E.g. ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"]
        "ALLOWED_ARMOR_TYPES": ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        # E.g. ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Wand"]
        "ALLOWED_WEAPON_TYPES": ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Wand"]
    },
    "custom": {
        # Filters by different armour bonuses
        "FILTER_TYPE": ["Speed", "Haste", "Prismatic"],

        # Defines the allowed item slots for filtering
        "ALLOWED_ARMOR_SLOTS": ["Waist", "Legs", "Wrist", "Hands", "Back", "Feet"],
        "ALLOWED_WEAPON_SLOTS": ["One-Hand", "Two-Hand", "Main-Hand", "Off-Hand"],
        "ALLOWED_ACCESSORY_SLOTS": ["Finger", "Trinket", "Held In Off-hand"],

        # Defines the allowed armor types for filtering
        "ALLOWED_ARMOR_TYPES": ["Cloth", "Leather", "Miscellaneous"],
        "ALLOWED_WEAPON_TYPES": ["Dagger", "Mace", "Fist Weapon", "Polearm", "Staff"]
    }
}

# Minimum and maximum item levels to include
MIN_ILVL = 1
MAX_ILVL = 668

# Maximum number of realms to scan
MAX_REALMS = 25

# Toggles full debugging metadata
PRINT_FULL_METADATA = False  # Set to True to print full auction metadata per matching item

# Region to query ('us' or 'eu')
REGION = 'us' 

# IDs for specific bonuses
SPEED_IDS = [42]
PRISMATIC_IDS = [523, 563, 564, 565, 572, 608, 1808, 3475, 3522, 4802, 6514, 6672, 6935, 7576, 7580, 7935, 8289, 8780, 8810, 9413, 9436, 9438, 9516, 10397, 10531, 10589, 10591, 10596, 10597, 10835, 10878, 11307, 12055, 12056]
HASTE_IDS = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 487, 604, 1690, 1691, 1692, 1693, 1694, 1695, 1696, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1704, 1705, 1706, 1707, 1708, 1709, 1710, 1720, 1756, 1757, 1758, 1759, 1760, 1761, 1762, 1763, 1764, 1765, 1766, 1767, 1768, 1769, 1770, 1771, 1772, 1773, 1774, 1775, 1776, 1786, 3349, 3350, 3353, 3355, 3356, 3357, 3364, 3365, 3366, 3370, 3371, 3372, 3373, 3374, 3375, 3376, 3377, 3378, 3403, 3404, 3405, 6358, 6391, 6397, 6398, 6399, 6401, 6405, 7734, 7737, 7740, 7743, 7746, 8021, 8022, 8023, 8024, 8025, 8026, 8027, 8028, 8029, 8030, 8031, 8032, 8033, 8034, 8035, 8036, 8037, 8038, 8039, 8040, 8041, 8042, 8043, 8044, 8045, 8046, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8054, 8055, 8056, 8057, 8058, 8059, 8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8176, 8177, 8182, 8183, 8184, 8185, 9613, 10810, 10816, 10967, 11202, 11315, 12220]

# Filenames for output and caching
CSV_FILENAME = 'CSVs/speed_gear.csv'
REALM_CSV = 'CSVs/realm_map.csv'
LOADED_SERVERS_CSV = 'CSVs/loaded_servers.csv'
TOKEN_CACHE = 'Tokens/token_cache.json'
BONUS_DATA_FILE = 'RaidBots_APIs/bonus_data_cache.json'
BONUS_DATA_URL = 'https://www.raidbots.com/static/data/live/bonuses.json' # Provides bonus ID adjustments (level increases per bonus)

# Human-readable mapping for armor subclass IDs
ARMOR_TYPE_MAP = {
    1: "Cloth",
    2: "Leather",
    3: "Mail",
    4: "Plate"
}

# Human-readable mapping for weapon subclass IDs
WEAPON_TYPE_MAP = {
    0: "Axe",
    1: "Sword",
    2: "Mace",
    3: "Dagger",
    4: "Polearm",
    5: "Staff",
    6: "Fist Weapon",
    7: "Warglaives",
    8: "Bow",
    9: "Gun",
    10: "Crossbow",
    11: "Thrown",
    12: "Wand"
}

# Mapping of inventory_type IDs to human-readable equipment slots
INVENTORY_TYPE_MAP = {
    1: "Head",
    2: "Neck",
    3: "Shoulder",
    4: "Shirt",
    5: "Chest",
    6: "Waist",     
    7: "Legs",
    8: "Feet",
    9: "Wrist",
    10: "Hands",
    11: "Finger",
    12: "Trinket",
    13: "One-Hand",
    14: "Shield",
    15: "Ranged",
    16: "Back",
    17: "Two-Hand",
    18: "Bag",
    19: "Tabard",
    20: "Robe",
    21: "Main-Hand",
    22: "Off-Hand",
    23: "Holdable",
    25: "Thrown",
    26: "Ranged Right",
    28: "Relic"
}

# Build filter presence dictionary
def apply_scan_profile(profile_name):
    """
    Applies the selected scan profile to the global constants used throughout the scan logic.
    """
    profile = SCAN_PROFILES.get(profile_name)
    if not profile:
        raise ValueError(f"Unknown scan profile: {profile_name}")

    globals()["FILTER_TYPE"] = profile["FILTER_TYPE"]
    globals()["ALLOWED_ARMOR_SLOTS"] = profile["ALLOWED_ARMOR_SLOTS"]
    globals()["ALLOWED_WEAPON_SLOTS"] = profile["ALLOWED_WEAPON_SLOTS"]
    globals()["ALLOWED_ACCESSORY_SLOTS"] = profile["ALLOWED_ACCESSORY_SLOTS"]
    globals()["ALLOWED_SLOTS"] = (
        profile["ALLOWED_ARMOR_SLOTS"] +
        profile["ALLOWED_WEAPON_SLOTS"] +
        profile["ALLOWED_ACCESSORY_SLOTS"]
    )
    globals()["ALLOWED_ARMOR_TYPES"] = profile["ALLOWED_ARMOR_TYPES"]
    globals()["ALLOWED_WEAPON_TYPES"] = profile["ALLOWED_WEAPON_TYPES"]
    globals()["ALLOWED_TYPES"] = (
        profile["ALLOWED_ARMOR_TYPES"] +
        profile["ALLOWED_WEAPON_TYPES"]
    )



# Configure global logging format and level
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
# Ensure tqdm lock is acquired to display progress safely
tqdm.get_lock()

# Load Blizzard API credentials from .env file
load_dotenv()
CLIENT_ID = os.getenv('BLIZZARD_CLIENT_ID')
CLIENT_SECRET = os.getenv('BLIZZARD_CLIENT_SECRET')

# Namespaces for Blizzard's dynamic and static API endpoints
REGION_NS = {
    'us': {'dynamic': 'dynamic-us', 'static': 'static-us'},
    'eu': {'dynamic': 'dynamic-eu', 'static': 'static-eu'}
}
# Base URL template for Blizzard API calls
BASE_URL = 'https://{region}.api.blizzard.com'
# In-memory map of realm slugs to their connected realm IDs and names
realm_map = {}

# === BONUS ID SYSTEM ===
# === BONUS ID SYSTEM ===
def fetch_raidbots_data(force_refresh=False):
    """
    Download or load multiple Raidbots JSON data files including bonuses, items, and metadata.

    Args:
        force_refresh (bool): When True, ignores cache and fetches fresh data.

    Returns:
        dict: Mapping of each file key to its loaded JSON content.
    """
    logging.info("🔄 Loading Raidbots datasets...")

    # List of Raidbots .json files to retrieve
    filenames = [
        "metadata",
        "bonuses",
        "equippable-items",
        "equippable-items-full",
        "item-names",
        "talents",
        "instances",
        "enchantments",
        "crafting",
        "item-curves",
        "item-conversions",
        "item-sets",
        "item-limit-categories",
        "level-selector-sequences",
        "bonus-crafted-stats",
        "bonus-effects",
        "bonus-id-base-levels",
        "bonus-id-levels",
        "bonus-level-deltas",
        "bonus-sockets",
        "bonus-upgrade-sets"
    ]

    base_url = "https://www.raidbots.com/static/data/live"
    local_data = {}
    modified = False

    # Check if any files are missing or older than 30 days
    for name in filenames:
        local_path = os.path.join(os.path.dirname(BONUS_DATA_FILE), f"{name}.json")

        # Determine if this file needs refresh
        if not os.path.exists(local_path):
            logging.info(f"🆕 Missing: {name}.json")
            modified = True
        else:
            file_age = time.time() - os.path.getmtime(local_path)
            if file_age > 30 * 86400:  # 30 days
                logging.info(f"♻️  Refreshing {name}.json (older than 30 days)")
                modified = True

    if not force_refresh and not modified:
        try:
            for name in filenames:
                path = os.path.join(os.path.dirname(BONUS_DATA_FILE), f"{name}.json")
                with open(path, 'r', encoding='utf-8') as f:
                    local_data[name] = json.load(f)
            return local_data
        except Exception as e:
            logging.warning(f"⚠️ Failed to load cached Raidbots data: {e}")
            force_refresh = True

    # Fetch and cache all files
    for name in filenames:
        try:
            url = f"{base_url}/{name}.json"
            response = requests.get(url)
            response.raise_for_status()
            local_data[name] = response.json()
            # Save to disk
            path = os.path.join(os.path.dirname(BONUS_DATA_FILE), f"{name}.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(local_data[name], f, indent=2)
            logging.info(f"✅ Downloaded and cached: {name}.json")
        except Exception as e:
            logging.warning(f"⚠️ Failed to fetch {name}.json: {e}")
            local_data[name] = {}

    return local_data



def parse_ilevel_string(ilevel_str, player_level):
    """
    Convert a string like '5 @plvl 1 - 357 @plvl 357' into an estimated ilvl using linear interpolation.
    """
    match = re.match(r"(\d+)\s+@plvl\s+(\d+)\s*-\s*(\d+)\s+@plvl\s+(\d+)", ilevel_str)
    if not match:
        return 0

    ilvl_low, plvl_low, ilvl_high, plvl_high = map(int, match.groups())

    if player_level <= plvl_low:
        return ilvl_low
    elif player_level >= plvl_high:
        return ilvl_high

    # Interpolate linearly between points
    ratio = (player_level - plvl_low) / (plvl_high - plvl_low)
    return round(ilvl_low + ratio * (ilvl_high - ilvl_low))


def infer_ilvl_from_bonus_ids(base_ilvl, bonus_ids, raidbots_data, fallback_data, player_level):
    """
    Calculate an item's adjusted item level using both level bonuses and ilevel scaling curves.
    """
    total_bonus = 0
    highest_scaled_ilvl = 0

    for b in bonus_ids:
        bid = str(b)
        bonus = raidbots_data.get(bid) or fallback_data.get(bid)

        if not bonus:
            continue

        # Handle flat level bonuses
        if 'level' in bonus:
            total_bonus += bonus['level']

        # Handle curve-based ilevel scaling
        elif 'ilevel' in bonus:
            # Map required level to player level used in ilevel scaling
            scaling_plvl = convert_required_level_to_player_level(player_level)
            scaled = parse_ilevel_string(bonus['ilevel'], scaling_plvl)
            highest_scaled_ilvl = max(highest_scaled_ilvl, scaled)

    # Prefer scaled level if found
    if highest_scaled_ilvl > 0:
        return highest_scaled_ilvl

    # Otherwise fallback to additive flat bonuses
    return base_ilvl + total_bonus


# === Utility: Infer player level from observed ilvl using curve ===
def infer_player_level_from_ilvl(observed_ilvl, curve_points):
    """Infers the player level that would result in the observed item level using the given curve."""
    if not curve_points:
        return None, None
    closest = min(curve_points, key=lambda pt: abs(pt["itemLevel"] - observed_ilvl))
    return closest["playerLevel"], closest["itemLevel"]


def convert_required_level_to_player_level(required_level):
    """
    Converts required item level (equip level) to effective player level used for ilevel scaling.
    These mappings are based on in-game scaling rules for legacy content.

    Returns:
        int: Estimated player level to use for interpolation.
    """
    if required_level >= 60:
        return 70
    elif required_level >= 56:
        return 60
    elif required_level >= 51:
        return 50
    elif required_level >= 45:
        return 45
    else:
        return required_level  # fallback



# === AUTHENTICATION AND TOKEN MANAGEMENT ===
def load_cached_token():
    """
    Load a previously saved OAuth token and its expiry time.

    Returns:
        tuple: (access_token (str) or None, expires_at (int timestamp)).
    """
    if not os.path.isfile(TOKEN_CACHE):
        return None, 0
    try:
        with open(TOKEN_CACHE, 'r') as f:
            data = json.load(f)
        return data.get('access_token'), data.get('expires_at', 0)
    except Exception:
        return None, 0


def save_token(token: str, expires_in: int):
    """
    Save a fresh OAuth token to disk with its calculated expiry.

    Args:
        token (str): OAuth access token.
        expires_in (int): Seconds until the token expires.
    """
    expires_at = int(time.time()) + expires_in
    with open(TOKEN_CACHE, 'w', encoding='utf-8') as f:
        json.dump({'access_token': token, 'expires_at': expires_at}, f)
    logging.info("✅ Cached new token (expires in %ds)", expires_in)


def get_token() -> str:
    """
    Retrieve a valid OAuth token, reusing cache or requesting a new one.

    Returns:
        str: A valid OAuth Bearer token.

    Raises:
        HTTPError: If the request to Blizzard's token URL fails.
    """
    token, expires_at = load_cached_token()
    now = int(time.time())
    # Reuse cached token if still valid for at least 60 seconds
    if token and now < (expires_at - 60):
        logging.info("✅ Reusing cached token (valid for %ds)", expires_at - now)
        return token
    # Otherwise request a new token via client_credentials grant
    url = 'https://oauth.battle.net/token'
    data = {'grant_type': 'client_credentials'}
    resp = requests.post(url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
    resp.raise_for_status()
    j = resp.json()
    token = j['access_token']
    expires_in = j.get('expires_in', 86399)
    save_token(token, expires_in)
    return token


def request_with_retry(session, method, url, params=None, retries=3):
    """
    Perform an HTTP request with retry logic for rate limits and token expiry.

    Args:
        session (requests.Session): HTTP session with headers set.
        method (str): HTTP method ('GET', 'POST', etc.).
        url (str): Full request URL.
        params (dict, optional): Query parameters.
        retries (int): Number of retry attempts on failure.

    Returns:
        dict: Parsed JSON response.

    Raises:
        RuntimeError: If unauthorized or retries are exhausted.
    """
    for attempt in range(1, retries + 1):
        resp = session.request(method, url, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            # Handle Blizzard rate limiting
            retry_after = int(resp.headers.get('Retry-After', '1'))
            logging.warning("⚠️ Rate limited; sleeping %ds (attempt %d/%d)", retry_after, attempt, retries)
            time.sleep(retry_after)
            continue
        if resp.status_code == 401:
            # Token may be invalid; clear cache and error
            if os.path.isfile(TOKEN_CACHE):
                os.remove(TOKEN_CACHE)
            raise RuntimeError("Unauthorized: cached token invalid or expired")
        # For other errors, raise HTTPError
        resp.raise_for_status()
    raise RuntimeError(f"Failed {method} {url} after {retries} attempts")

# === REALM MAPPING ===
def load_realm_map_from_csv(filename=REALM_CSV) -> bool:
    """
    Load connected realm IDs and names from a local CSV file.

    Args:
        filename (str): Path to the CSV mapping file.

    Returns:
        bool: True if the file existed and loaded, False otherwise.
    """
    if not os.path.exists(filename):
        return False
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            slug = row['slug'].lower()
            realm_map[slug] = {
                'id': int(row['connected_realm_id']),
                'name': row['name']
            }
    logging.info("📁 Loaded %d realms from %s", len(realm_map), filename)
    return True


def export_realm_map_csv(filename=REALM_CSV):
    """
    Write the in-memory realm map to a CSV for future caching.

    Args:
        filename (str): Output CSV path.
    """
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'slug', 'connected_realm_id'])
        for slug, info in sorted(realm_map.items(), key=lambda kv: kv[1]['name']):
            writer.writerow([info['name'], slug, info['id']])
    logging.info("📁 Exported realm map to %s", filename)



def load_realm_map(session, headers):
    """
    Ensure realm_map is populated, loading from CSV or querying Blizzard API.

    Args:
        session (requests.Session): HTTP session.
        headers (dict): Authorization headers for Blizzard API.
    """
    # Try loading cached CSV first
    if load_realm_map_from_csv():
        return
    # Otherwise, fetch all connected realms via Blizzard's index endpoint
    namespace = f"dynamic-{REGION}"
    idx_url = f"{BASE_URL.format(region=REGION)}/data/wow/connected-realm/index"
    params = {'namespace': namespace, 'locale': 'en_US'}
    idx = request_with_retry(session, 'GET', idx_url, params)
    realm_map.clear()
    # For each connected realm entry, fetch its details
    for entry in idx.get('connected_realms', []):
        href = entry.get('key', {}).get('href') or entry.get('href')
        crid = int(urlparse(href).path.rstrip('/').split('/')[-1])
        cr_url = f"{BASE_URL.format(region=REGION)}/data/wow/connected-realm/{crid}"
        cr = request_with_retry(session, 'GET', cr_url, params)
        for realm in cr.get('realms', []):
            slug = realm['slug'].lower()
            name = realm['name']
            realm_map[slug] = {'id': crid, 'name': name}
    logging.info("✅ Loaded %d realms via connected-realm index", len(realm_map))
    export_realm_map_csv()


def resolve_realm_input(user_input):
    """
    Convert a user-supplied realm ID, slug, or name into a connected realm ID.

    Args:
        user_input (str): Numeric ID, slug text, or display name.

    Returns:
        tuple: (connected_realm_id (int), display_name (str)).

    Raises:
        ValueError: If the input cannot be matched.
    """
    # Default to Caelestrasz if no input provided
    if not user_input:
        for slug, info in realm_map.items():
            if info['id'] == 3721:
                return info['id'], info['name']
        raise ValueError("Default realm Caelestrasz (ID 3721) not found in realm map.")

    # Numeric ID case
    if user_input.isdigit():
        crid = int(user_input)
        for info in realm_map.values():
            if info['id'] == crid:
                return crid, info['name']
        raise ValueError(f"Invalid realm ID: {crid}")

    # Normalize text input to slug format
    clean = user_input.strip().lower().replace(' ', '-')
    if clean in realm_map:
        info = realm_map[clean]
        return info['id'], info['name']

    # Fallback: match on full display name
    for slug, info in realm_map.items():
        if info['name'].lower() == user_input.strip().lower():
            return info['id'], info['name']

    raise ValueError(f"Unknown realm input: {user_input}")


def load_or_init_scan_order(realm_map, filename=LOADED_SERVERS_CSV):
    """
    Load scan order from CSV or initialize if missing. Realms not yet recorded are treated as outdated.

    Args:
        realm_map (dict): Current loaded realm mapping.
        filename (str): Path to the loaded server CSV.

    Returns:
        list of (realm_id, realm_name): Sorted by least recently scanned.
    """
    scan_records = {}

    if os.path.exists(filename):
        try:
            with open(filename, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = int(row['realm_id'])
                    scan_records[rid] = {
                        'realm_name': row['realm_name'],
                        'last_scanned': row.get('last_scanned', '0')
                    }
        except Exception as e:
            logging.warning(f"⚠️ Failed to load scan history: {e}")

    # Add any new realms from realm_map not in cache
    for slug, info in realm_map.items():
        rid = info['id']
        if rid not in scan_records:
            scan_records[rid] = {
                'realm_name': info['name'],
                'last_scanned': '0'
            }

    # Sort by oldest scan date
    sorted_realms = sorted(
        scan_records.items(),
        key=lambda kv: kv[1]['last_scanned']
    )

    return [(rid, data['realm_name']) for rid, data in sorted_realms[:MAX_REALMS]]


def update_single_scan_timestamp(realm_id, realm_name, filename=LOADED_SERVERS_CSV):
    """
    Immediately update the scan timestamp for a single realm.

    Args:
        realm_id (int): Realm ID.
        realm_name (str): Human-readable realm name.
        filename (str): Path to the CSV cache.
    """
    now_str = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime())
    existing = {}

    # Load existing cache
    if os.path.exists(filename):
        try:
            with open(filename, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = int(row['realm_id'])
                    existing[rid] = {
                        'realm_name': row['realm_name'],
                        'last_scanned': row.get('last_scanned', '0')
                    }
        except Exception as e:
            logging.warning(f"⚠️ Could not load existing scan cache: {e}")

    # Update or insert this realm
    existing[realm_id] = {
        'realm_name': realm_name,
        'last_scanned': now_str
    }

    # Write back updated file
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['realm_id', 'realm_name', 'last_scanned'])
            writer.writeheader()
            for rid, data in sorted(existing.items(), key=lambda kv: kv[1]['last_scanned']):
                writer.writerow({
                    'realm_id': rid,
                    'realm_name': data['realm_name'],
                    'last_scanned': data['last_scanned']
                })
    except Exception as e:
        logging.warning(f"❌ Failed to update scan cache for realm {realm_id}: {e}")


# === ITEM AND AUCTION LOGIC ===
def fetch_item_info(session, headers, item_id, cache):
    """
    Retrieve item metadata (level, name, armor type, and slot) from Blizzard API or cache.

    Args:
        session (requests.Session): Active HTTP session.
        headers (dict): Authorization headers.
        item_id (int): Unique Blizzard item ID.
        cache (dict): Local cache mapping IDs to metadata.

    Returns:
        dict: Cached metadata including armor_type and slot_type.
    """
    if item_id in cache:
        return cache[item_id]

    url = f"{BASE_URL.format(region=REGION)}/data/wow/item/{item_id}"
    params = {'namespace': REGION_NS[REGION]['static'], 'locale': 'en_US'}
    data = request_with_retry(session, 'GET', url, params)

    # Item name
    name_field = data.get('name')
    name = name_field if isinstance(name_field, str) else name_field.get('en_US', f"item_{item_id}")
    ilvl = data.get('level', 0)

    # Accurate required level
    required_level_exact = data.get("requirements", {}).get("level", {}).get("value")
    if required_level_exact is None:
        required_level_exact = data.get('required_level', 60)

    # Determine item type based on item class ID
    item_class_id = data.get('item_class', {}).get('id')
    subclass_id = data.get('item_subclass', {}).get('id')

    if item_class_id == 2:  # Weapon
        armor_type = WEAPON_TYPE_MAP.get(subclass_id, 'Miscellaneous')
    elif item_class_id == 4:  # Armor
        armor_type = ARMOR_TYPE_MAP.get(subclass_id, 'Miscellaneous')
    else:
        armor_type = 'Miscellaneous'

    # Slot Type
    inventory_data = data.get('inventory_type', {})
    inv_id = inventory_data.get('id')
    inv_type = inventory_data.get('type', '')
    inv_name = inventory_data.get('name', '')

    # Fallback logic for slot name
    slot_type = INVENTORY_TYPE_MAP.get(inv_id)
    if not slot_type:
        slot_type = inv_name or inv_type or "Other"

    # Store in cache
    cache[item_id] = {
        'ilvl': ilvl,
        'name': name,
        'armor_type': armor_type,
        'slot_type': slot_type,
        'required_level': required_level_exact
    }

    time.sleep(0.1)  # Be gentle with Blizzard
    return cache[item_id]


def get_observed_ilvl(auc, info):
    """
    Determine the most accurate observed item level from an auction listing.
    Priority: item_modifiers (type 9) > auction.item.level > fallback item info.

    Args:
        auc (dict): The full auction entry.
        info (dict): Item metadata from the item endpoint.

    Returns:
        int: Observed item level.
    """
    # Priority 1: modifier override
    for mod in auc.get("item_modifiers", []):
        if mod.get("type") == 9:
            return mod.get("value")

    # Priority 2: explicit item level from auction data
    level = auc.get("item", {}).get("level")
    if level:
        return level

    # Priority 3: fallback to item metadata
    return info.get("ilvl", 0)


def scan_realm_with_bonus_analysis(session, headers, realm_id, realm_name, item_cache, raidbots_data, fallback_data, curve_data):
    """
    Scan auction data for a single connected-realm ID, filtering by required bonuses.

    Args:
        session (requests.Session): HTTP session.
        headers (dict): Authorization headers.
        realm_id (int): Connected realm identifier.
        realm_name (str): Human-readable realm name.
        item_cache (dict): Cache for item metadata.
        raidbots_data (dict): Live bonus-level data.
        fallback_data (dict): Cached bonus-level data.
        curve_data (dict): Preloaded item-curves.json.

    Returns:
        list[dict]: List of auction entries matching Speed stat.
    """
    logging.info(f"🔍 Scanning realm ID {realm_id}: {realm_name}")
    url = f"{BASE_URL.format(region=REGION)}/data/wow/connected-realm/{realm_id}/auctions"
    params = {'namespace': REGION_NS[REGION]['dynamic'], 'locale': 'en_US'}
    data = request_with_retry(session, 'GET', url, params)

    results = []

    # Build dynamic filter checks using the active FILTER_TYPE (applied at runtime)
    BONUS_FILTER_MAP = {
        "Speed": SPEED_IDS,
        "Prismatic": PRISMATIC_IDS,
        "Haste": HASTE_IDS
    }

    try:
        ACTIVE_FILTERS = {
            f: set(BONUS_FILTER_MAP[f]) for f in FILTER_TYPE if f in BONUS_FILTER_MAP
        }
    except NameError:
        raise RuntimeError("FILTER_TYPE is not defined. Make sure apply_scan_profile() is called before scanning.")

    for auc in data.get('auctions', []):
        item = auc['item']
        bonuses = list(set(auc.get('bonus_lists', []) + item.get('bonus_lists', [])))

        # Dynamically check all required filters
        if any(not any(b in bonuses for b in ACTIVE_FILTERS[f]) for f in ACTIVE_FILTERS):
            continue

        info = fetch_item_info(session, headers, item['id'], item_cache)

        observed_ilvl = get_observed_ilvl(auc, info)
        base_ilvl = observed_ilvl  # Use this for curve inference
        inferred_level = None

        # Try to find a bonus entry with curveId
        curve_id = None
        for b in bonuses:
            bonus_data = raidbots_data.get(str(b)) or fallback_data.get(str(b))
            if bonus_data and "curveId" in bonus_data:
                curve_id = bonus_data["curveId"]
                break

        if curve_id:
            points = curve_data.get(str(curve_id), {}).get("points", [])
            inferred_level, corrected_ilvl = infer_player_level_from_ilvl(base_ilvl, points)
            final_ilvl = corrected_ilvl or observed_ilvl
        else:
            # Fallback to bonus-based adjustment
            final_ilvl = infer_ilvl_from_bonus_ids(
                base_ilvl,
                bonuses,
                raidbots_data,
                fallback_data,
                player_level=info.get('required_level', 60)
            ) or observed_ilvl

        if MIN_ILVL <= final_ilvl <= MAX_ILVL:
            result = {
                'realm_id': realm_id,
                'item_id': item['id'],
                'name': info['name'],
                'ilvl': final_ilvl,
                'quantity': auc.get('quantity'),
                'buyout': auc.get('buyout'),
            }

            if PRINT_FULL_METADATA:
                print(f"\n📦 Full Metadata for '{info['name']}'")
                print(f"🧾 Item ID     : {item['id']}")
                print(f"📏 Observed ilvl: {observed_ilvl}")
                print(f"📈 Final ilvl  : {final_ilvl}")
                print(f"🎚️  Required Level: {info.get('required_level', '—')}")
                print(f"⛓️  Armor Type  : {info.get('armor_type', 'Unknown')}")
                print(f"🎯 Slot Type   : {info.get('slot_type', 'Unknown')}")
                print(f"🎫 Bonus IDs   : {bonuses}")
                print(f"🧩 Modifiers   : {auc.get('item_modifiers', [])}")
                print(f"💰 Buyout      : {auc.get('buyout')}")
                print(f"🔢 Quantity    : {auc.get('quantity')}")
                print("-" * 60)

            slot = info['slot_type']
            armor_type = info['armor_type']

            # Identify slot categories
            is_armor_slot = slot in ALLOWED_ARMOR_SLOTS
            is_weapon_slot = slot in ALLOWED_WEAPON_SLOTS
            is_accessory_slot = slot in ALLOWED_ACCESSORY_SLOTS

            # Identify type categories
            is_armor_type = armor_type in ALLOWED_ARMOR_TYPES
            is_weapon_type = armor_type in ALLOWED_WEAPON_TYPES

            # Final validation: only reject if not in allowed slots at all
            if slot not in ALLOWED_SLOTS:
                if PRINT_FULL_METADATA:
                    print(f"⛔ Rejected: Slot '{slot}' not in allowed slot list")
                continue

            # Strict match: armor slot must have armor type
            if is_armor_slot and not is_armor_type:
                if PRINT_FULL_METADATA:
                    print(f"⛔ Rejected due to mismatch: Armor slot '{slot}' with type '{armor_type}'")
                continue

            # Relaxed: weapon slot accepted regardless of armor_type
            if is_weapon_slot and not is_weapon_type:
                if PRINT_FULL_METADATA:
                    print(f"⚠️ Warning: Weapon slot '{slot}' with ambiguous type '{armor_type}' (accepted)")
                # Do not continue — accept

            # Strict accessory logic (optional)
            if is_accessory_slot and armor_type not in ALLOWED_TYPES:
                if PRINT_FULL_METADATA:
                    print(f"⛔ Rejected: Accessory slot '{slot}' with unlisted type '{armor_type}'")
                continue

            # All checks passed, add to results
            if PRINT_FULL_METADATA:
                print(f"✅ Accepted | armor_type: '{info['armor_type']}' in 'ALLOWED_TYPES'\n              "
                      f"slot_type:  '{info['slot_type']}' in 'ALLOWED_SLOTS'")

            results.append(result)

    time.sleep(1)  # Throttle between realm scans
    return results


# === CSV OUTPUT ===
def write_csv(results, filename=CSV_FILENAME):
    """
    Write the final scan results to a CSV file.

    Args:
        results (list[dict]): Auction entries to write.
        filename (str): Output CSV filename.
    """
    realm_names = {}
    if os.path.exists(REALM_CSV):
        with open(REALM_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                realm_names[int(row['connected_realm_id'])] = row['name']

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'realm', 'item_id', 'name', 'ilvl', 'buyout_gold'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'realm': realm_names.get(r['realm_id'], f"Realm-{r['realm_id']}"),
                'item_id': r['item_id'],
                'name': r['name'],
                'ilvl': r['ilvl'],
                'buyout_gold': (int(r['buyout']) // 10000) if r['buyout'] else 0
            })

# === USER INTERFACE ===
def select_scan_profile():
    """Prompts the user to choose between full and custom scan profiles."""
    choice = input(f"{'Items Profile':<12} | Custom(1) or Everything(2): ").strip() or "1"
    if choice == "1":
        return "custom"
    elif choice == "2":
        return "full"
    else:
        print("❌ Invalid choice. Defaulting to 'full' scan profile.")
        return "full"
    

def select_scan_type():
    """Prompts the user to choose between a test scan or a full scan, returning the mode and test realm if applicable."""
    choice = input(f"{'Scan Type':<13} | Single Realm(1) or All Realms(2): ").strip() or "2"
    if choice == "1":
        test_realm = input(f"{'Test realm':<13} | Enter the realm name or ID: ").strip()
        return True, test_realm
    return False, None


# === MAIN EXECUTION ===
def main():
    """
    Main entry point for the script.
    Handles authentication, realm loading, scanning, and output.
    """
    # Prompt scan profile
    profile_name = select_scan_profile()
    apply_scan_profile(profile_name)

    # Prompt user preferences
    test_mode, test_realm = select_scan_type()

    # Obtain a valid OAuth token and prepare HTTP session
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    session = requests.Session()
    session.headers.update(headers)

    # Load realm map (cache or API) and bonus data
    load_realm_map(session, headers)

    # Load full Raidbots dataset
    raidbots_bundle = fetch_raidbots_data()
    raidbots_data = raidbots_bundle.get('bonuses', {})

    # Load fallback bonus data from same directory as full dataset
    fallback_data_path = os.path.join(os.path.dirname(BONUS_DATA_FILE), "bonuses.json")
    with open(fallback_data_path, 'r', encoding='utf-8') as f:
        fallback_data = json.load(f)

    # Load curve data once
    from pathlib import Path
    with open(Path(os.path.dirname(BONUS_DATA_FILE)) / "item-curves.json", 'r', encoding='utf-8') as f:
        curve_data = json.load(f)

    # Build list of realms to scan based on mode
    if test_mode:
        realm_id, display_name = resolve_realm_input(test_realm)
        realms = [(realm_id, display_name)]
    else:
        try:
            realms = load_or_init_scan_order(realm_map)
        except Exception as e:
            logging.warning(f"⚠️ Failed to load scan order. Falling back to default order. Reason: {e}")
            realms = [(info['id'], info['name']) for info in realm_map.values()][:MAX_REALMS]


    # Format the list of filters into a readable string like: "Prismatic, Haste, Speed"
    filter_str = ", ".join(FILTER_TYPE)

    logging.info(
        f"🔍 Scanning {len(realms)} realm(s) for {filter_str} gear (ilvl {MIN_ILVL}-{MAX_ILVL})..."
    )

    # Scan each realm and collect results
    all_results = []
    item_cache = {}

    for rid, display_name in tqdm(realms, desc='Scanning', unit='realm'):
        all_results.extend(
            scan_realm_with_bonus_analysis(
                session, headers, rid, display_name, item_cache, raidbots_data, fallback_data, curve_data
            )
        )
        if not test_mode:
            try:
                update_single_scan_timestamp(rid, display_name)
            except Exception as e:
                logging.warning(f"⚠️ Failed to write scan cache for realm {display_name} ({rid}): {e}")


   # Write to CSV and/or print to console
    if all_results:
        write_csv(all_results)

        # Sort and print output to terminal
        all_results.sort(key=lambda x: x['ilvl'], reverse=True)

        # Print table header (aligned)
        print(f"\n{'Realm':<21} {'Item ID':<10} {'Type':<14} {'Slot':<15} {'Name':<35} {'ilvl':>9} {'Buyout':>10}")
        
        for r in all_results:
            realm_name = next((n for i, n in realms if i == r['realm_id']), f"Realm-{r['realm_id']}")
            item_id = r['item_id']
            name = r['name']
            ilvl = r['ilvl']
            gold = int(r['buyout']) // 10000 if r['buyout'] else 0

            # Fetch additional details for Type and Slot
            item_info = fetch_item_info(session, headers, item_id, item_cache)
            item_type = item_info.get('armor_type', 'Unknown')
            item_slot = item_info.get('slot_type', 'Unknown')

            # Apply spacing BEFORE coloring
            realm_str = f"✅ {realm_name:<19}"  # Include checkmark inside column
            item_id_str = f"{item_id:<11}"
            type_str = f"{item_type:<15}"
            slot_str = f"{item_slot:<16}"
            name_str = f"{name:<35}"
            ilvl_str = f"{ilvl:>8}"
            gold_str = f"{gold:>12,}".replace(",", "'")

            # Apply colors AFTER spacing
            ilvl_str = f"\033[94m{ilvl_str}\033[0m"
            gold_str = f"{gold_str}\033[33mg\033[0m"

            print(f"{realm_str}{item_id_str}{type_str}{slot_str}{name_str}{ilvl_str} {gold_str}")

        print(f"\033[92m\nFound \033[93m{len(all_results)} \033[92mitems matching the filters: \033[94m{', '.join(FILTER_TYPE)}\033[0m\n")
    else:
        logging.info("❌ No matching Speed-stat items found.")

if __name__ == '__main__':
    main()

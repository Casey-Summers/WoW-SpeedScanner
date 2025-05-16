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
from time import perf_counter # Measure elapsed time for performance tracking
import sys # System-specific parameters and functions
from pathlib import Path # Handle file paths in a cross-platform way
import argparse
import json


# === SCAN PROFILE DEFINITIONS ===
SCAN_PROFILES = {
    "full": {
        # Filters by different armour bonuses
        # E.g. any combination of ["Speed", "Prismatic", "{Stat}", "Max-{Stat}"]
        "FILTER_TYPE": ["Speed"],
        
        # Item level filtering (minimum and maximum)
        "MIN_ILVL": 0,
        "MAX_ILVL": 1000,
        
        # Filters by max Buyout Price (in gold) 
        "MAX_BUYOUT": 10000000,

        # Stat distribution thresholds per stat
        # E.g. 0=no threshold, 100=pure stat distribution
        "STAT_DISTRIBUTION_THRESHOLDS": {
            "Haste": 0,
            "Crit": 0,
            "Vers": 0,
            "Mastery": 0
        },

        # Defines the allowed item slots for filtering
        # E.g. ["Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet"]
        "ALLOWED_ARMOR_SLOTS": ["Head", "Chest", "Shoulder", "Waist", "Legs", "Wrist", "Hands", "Back", "Feet"],
        # E.g. ["One-Hand", "Two-Hand", "Main-Hand", "Off-Hand", "Ranged"]
        "ALLOWED_WEAPON_SLOTS": ["One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right"],
        # E.g. ["Finger", "Trinket", "Held In Off-hand", "Neck"]
        "ALLOWED_ACCESSORY_SLOTS": ["Finger", "Trinket", "Held In Off-hand", "Neck"],

        # Defines the allowed armor types for filtering
        # E.g. ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"]
        "ALLOWED_ARMOR_TYPES": ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        # E.g. ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand"]
        "ALLOWED_WEAPON_TYPES": ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"]
    },
    "custom": {
        # Filters by different armour bonuses and stats
        "FILTER_TYPE": ["Speed", "Max-Haste"],
        
        # Item level filtering (minimum and maximum)
        "MIN_ILVL": 320,
        "MAX_ILVL": 357,
        
        # Filters by max Buyout Price (in gold) 
        "MAX_BUYOUT": 10000000,

        # Stat distribution thresholds per stat
        "STAT_DISTRIBUTION_THRESHOLDS": {
            "Haste": 0,
            "Crit": 0,
            "Vers": 0,
            "Mastery": 0
        },

        # Defines the allowed item slots for filtering
        "ALLOWED_ARMOR_SLOTS": ["Waist", "Legs", "Wrist", "Hands", "Back", "Feet"],
        "ALLOWED_WEAPON_SLOTS": ["One-Hand", "Two-Hand", "Main-Hand", "Off-Hand"],
        "ALLOWED_ACCESSORY_SLOTS": ["Finger", "Trinket", "Held In Off-hand"],

        # Defines the allowed armor types for filtering
        "ALLOWED_ARMOR_TYPES": ["Cloth", "Leather", "Miscellaneous"],
        "ALLOWED_WEAPON_TYPES": ["Dagger", "Mace", "Fist Weapon", "Polearm", "Staff", "Off Hand"]
    },
    "profitable": {
        # Filters by different armour bonuses and stats
        "FILTER_TYPE": ["Speed", "Prismatic"],

        # Item level filtering (minimum and maximum)
        "MIN_ILVL": 580,
        "MAX_ILVL": 1000,

        # Filters by max Buyout Price (in gold) 
        "MAX_BUYOUT": 2000,  # e.g. 2000g

        # Stat distribution thresholds per stat
        "STAT_DISTRIBUTION_THRESHOLDS": {
            "Haste": 0,
            "Crit": 0,
            "Vers": 0,
            "Mastery": 0
        },

        # Defines the allowed item slots for filtering
        "ALLOWED_ARMOR_SLOTS": ["Waist", "Legs", "Wrist", "Hands", "Back"],
        "ALLOWED_WEAPON_SLOTS": ["One-Hand", "Two-Hand", "Main-Hand", "Held In Off-hand", "Off-Hand", "Off Hand", "Ranged", "Ranged Right"],
        "ALLOWED_ACCESSORY_SLOTS": ["Finger", "Trinket", "Held In Off-hand"],

        # Defines the allowed armor types for filtering
        "ALLOWED_ARMOR_TYPES": ["Cloth", "Leather", "Mail", "Plate", "Miscellaneous"],
        "ALLOWED_WEAPON_TYPES": ["Dagger", "Sword", "Axe", "Mace", "Fist Weapon", "Polearm", "Staff", "Off-Hand", "Warglaives", "Gun", "Bow", "Crossbow", "Thrown", "Shield", "Wand", "Off Hand", "Ranged Right"]
    }
}

# Maximum number of connected-realms to scan (Max=83)
MAX_REALMS = 83

# Toggles full debugging metadata
PRINT_FULL_METADATA = True  # Set to True to print full auction metadata per matching item
suppress_inline_debug = False  # Global override for suppressing debug prints during formatted output

# Limits the number of requests to Blizzard's API
MAX_REQUESTS_PER_SEC = 90

# Deletes records older than a specified duration in the scan cache
SCAN_EXPIRY_DAYS = 2

# Region to query ('us' or 'eu')
REGION = 'us' 

# IDs for specific bonuses
SPEED_IDS = [42]
PRISMATIC_IDS = [523, 563, 564, 565, 572, 608, 1808, 3475, 3522, 4802, 6514, 6672, 6935, 7576, 7580, 7935, 8289, 8780, 8781, 8782, 8810, 9413, 9436, 9438, 9516, 10397, 10531, 10589, 10591, 10596, 10597, 10835, 10878, 11307, 12055, 12056]
HASTE_IDS = [18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 487, 604, 1690, 1691, 1692, 1693, 1694, 1695, 1696, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1704, 1705, 1706, 1707, 1708, 1709, 1710, 1720, 1756, 1757, 1758, 1759, 1760, 1761, 1762, 1763, 1764, 1765, 1766, 1767, 1768, 1769, 1770, 1771, 1772, 1773, 1774, 1775, 1776, 1786, 3349, 3350, 3353, 3355, 3356, 3357, 3364, 3365, 3366, 3370, 3371, 3372, 3373, 3374, 3375, 3376, 3377, 3378, 3403, 3404, 3405, 3431, 6358, 6391, 6397, 6398, 6399, 6401, 6405, 7734, 7737, 7740, 7743, 7746, 8021, 8022, 8023, 8024, 8025, 8026, 8027, 8028, 8029, 8030, 8031, 8032, 8033, 8034, 8035, 8036, 8037, 8038, 8039, 8040, 8041, 8042, 8043, 8044, 8045, 8046, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8054, 8055, 8056, 8057, 8058, 8059, 8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8176, 8177, 8182, 8183, 8184, 8185, 9501, 9613, 10810, 10816, 10967, 11202, 11315, 12220]
CRIT_IDS = [17, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 486, 489, 603, 606, 1676, 1677, 1678, 1679, 1680, 1681, 1682, 1683, 1684, 1685, 1686, 1687, 1688, 1689, 1690, 1691, 1692, 1693, 1694, 1695, 1696, 1718, 1742, 1743, 1744, 1745, 1746, 1747, 1748, 1749, 1750, 1751, 1752, 1753, 1754, 1755, 1756, 1757, 1758, 1759, 1760, 1761, 1762, 1784, 3343, 3344, 3345, 3346, 3347, 3348, 3349, 3350, 3351, 3352, 3353, 3354, 3361, 3362, 3363, 3370, 3371, 3372, 3401, 3402, 3403, 6357, 6390, 6394, 6395, 6396, 6400, 6404, 7733, 7736, 7739, 7742, 7745, 7985, 7986, 7987, 7988, 7989, 7990, 7991, 7992, 7993, 7994, 7995, 7996, 7997, 7998, 7999, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 8011, 8012, 8013, 8014, 8015, 8016, 8017, 8018, 8019, 8020, 8021, 8022, 8023, 8024, 8025, 8026, 8027, 8028, 8029, 8030, 8031, 8032, 8033, 8034, 8035, 8036, 8037, 8038, 8176, 8177, 8178, 8179, 8180, 8181, 9618, 10809, 10815, 10966, 11201, 11316, 12221]
VERS_IDS = [87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347, 348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359, 360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 490, 491, 492, 607, 1676, 1677, 1678, 1679, 1680, 1681, 1682, 1704, 1705, 1706, 1707, 1708, 1709, 1710, 1711, 1712, 1713, 1714, 1715, 1716, 1717, 1719, 1742, 1743, 1744, 1745, 1746, 1747, 1748, 1770, 1771, 1772, 1773, 1774, 1775, 1776, 1777, 1778, 1779, 1780, 1781, 1782, 1783, 1785, 3343, 3344, 3345, 3358, 3359, 3360, 3361, 3362, 3363, 3364, 3365, 3366, 3367, 3368, 3369, 3376, 3377, 3378, 3401, 3405, 3406, 3618, 6393, 6403, 6407, 7985, 7986, 7987, 7988, 7989, 7990, 7991, 7992, 7993, 7994, 7995, 7996, 7997, 7998, 7999, 8000, 8001, 8002, 8057, 8058, 8059, 8060, 8061, 8062, 8063, 8064, 8065, 8066, 8067, 8068, 8069, 8070, 8071, 8072, 8073, 8074, 8075, 8076, 8077, 8078, 8079, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091, 8092, 8180, 8181, 8184, 8185, 8186, 8187, 10972, 11123, 11124, 11125, 11207, 11317]
MASTERY_IDS = [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 322, 323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 385, 386, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 404, 405, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442, 443, 444, 445, 446, 447, 488, 605, 1683, 1684, 1685, 1686, 1687, 1688, 1689, 1697, 1698, 1699, 1700, 1701, 1702, 1703, 1711, 1712, 1713, 1714, 1715, 1716, 1717, 1721, 1749, 1750, 1751, 1752, 1753, 1754, 1755, 1763, 1764, 1765, 1766, 1767, 1768, 1769, 1777, 1778, 1779, 1780, 1781, 1782, 1783, 1787, 3346, 3347, 3348, 3351, 3352, 3354, 3355, 3356, 3357, 3358, 3359, 3360, 3367, 3368, 3369, 3373, 3374, 3375, 3402, 3404, 3406, 3495, 3496, 3497, 3498, 3499, 3500, 6392, 6402, 6406, 8003, 8004, 8005, 8006, 8007, 8008, 8009, 8010, 8011, 8012, 8013, 8014, 8015, 8016, 8017, 8018, 8019, 8020, 8039, 8040, 8041, 8042, 8043, 8044, 8045, 8046, 8047, 8048, 8049, 8050, 8051, 8052, 8053, 8054, 8055, 8056, 8075, 8076, 8077, 8078, 8079, 8080, 8081, 8082, 8083, 8084, 8085, 8086, 8087, 8088, 8089, 8090, 8091, 8092, 8178, 8179, 8182, 8183, 8186, 8187, 9619, 10813, 10819, 10970, 11205, 11314, 12219]
LEGACY_BONUS_IDS = [6654, 6655, 7968]

# Filenames for output and caching
CSV_FILENAME = 'CSVs/speed_gear.csv'
REALM_CSV = 'CSVs/realm_map.csv'
LOADED_SERVERS_CSV = 'CSVs/loaded_servers.csv'
TOKEN_CACHE = 'Tokens/token_cache.json'
BONUS_DATA_FILE = 'RaidBots_APIs/bonus_data_cache.json'
BONUS_DATA_URL = 'https://www.raidbots.com/static/data/live/bonuses.json' # Provides bonus ID adjustments (level increases per bonus)

# Mapping of bonus IDs to their respective filter types
FILTER_ID_MAP = {
    "Speed": SPEED_IDS,
    "Prismatic": PRISMATIC_IDS,
    "Haste": HASTE_IDS,
    "Crit": CRIT_IDS,
    "Vers": VERS_IDS,
    "Mastery": MASTERY_IDS
}

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

# Global tracking for rate control
throttle_tracker = {
    'start_time': None,
    'request_count': 0
}

debug_stats = {
    'blizzard_requests': 0,
    'item_metadata_hits': 0,
    'item_metadata_misses': 0,
    'auction_calls': 0,
    'realms_scanned': 0,
}

# === Command-line argument parsing ===
parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, help='Path to JSON config file')
args = parser.parse_args()

if args.config:
    with open(args.config, "r") as f:
        config_data = json.load(f)
        # Apply to your constants (FILTER_TYPE, ALLOWED_SLOTS, etc.)
        
# === Handle command-line config ===
parser = argparse.ArgumentParser()
parser.add_argument("--config", type=str, help="Path to scan config JSON")
args = parser.parse_args()

# Default profile to load
profile_name = "custom"

# Load config from file if passed
if args.config and os.path.exists(args.config):
    with open(args.config, "r") as f:
        config = json.load(f)
        # Extract filters from the file
        CUSTOM_PROFILE = {
            "MIN_ILVL": 1,
            "MAX_ILVL": 1000,
            "MAX_BUYOUT": int(config.get("max_buyout", 99999999)),
            "FILTER_TYPE": [],
            "ALLOWED_SLOTS": config.get("slots", []),
            "REQUIRE_PRISMATIC": config.get("prismatic", False),
            "STAT_DISTRIBUTION_THRESHOLDS": {
                "Haste": 71 if config.get("haste") else 0,
                "Crit": 71 if config.get("crit") else 0,
                "Vers": 71 if config.get("vers") else 0,
                "Mastery": 71 if config.get("mastery") else 0,
                "Speed": 71 if config.get("speed") else 0
            }
        }

        # Assign FILTER_TYPE based on enabled stats
        if config.get("haste"): CUSTOM_PROFILE["FILTER_TYPE"].append("Haste")
        if config.get("crit"): CUSTOM_PROFILE["FILTER_TYPE"].append("Crit")
        if config.get("vers"): CUSTOM_PROFILE["FILTER_TYPE"].append("Vers")
        if config.get("mastery"): CUSTOM_PROFILE["FILTER_TYPE"].append("Mastery")
        if config.get("speed"): CUSTOM_PROFILE["FILTER_TYPE"].append("Speed")

        # Inject this into SCAN_PROFILES
        SCAN_PROFILES["custom"] = CUSTOM_PROFILE
        profile_name = "custom"


# === Conditional global logging based on debug flag ===
LOG_LEVEL = logging.DEBUG if PRINT_FULL_METADATA else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(levelname)s] %(message)s',
    stream=sys.stderr
)
logging.getLogger("urllib3").setLevel(LOG_LEVEL)

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


class ScanConfig:
    def __init__(self, profile_data):
        # Ensure the profile has the necessary integer attributes
        if "MIN_ILVL" not in profile_data or "MAX_ILVL" not in profile_data or "STAT_DISTRIBUTION_THRESHOLDS" not in profile_data:
            raise ValueError("Profile is missing one or more required fields: MIN_ILVL, MAX_ILVL, STAT_DISTRIBUTION_THRESHOLDS")

        # Read and assign string-based attributes
        self.filter_type = profile_data["FILTER_TYPE"]
        self.allowed_armor_slots = profile_data["ALLOWED_ARMOR_SLOTS"]
        self.allowed_weapon_slots = profile_data["ALLOWED_WEAPON_SLOTS"]
        self.allowed_accessory_slots = profile_data["ALLOWED_ACCESSORY_SLOTS"]
        self.allowed_slots = (
            self.allowed_armor_slots +
            self.allowed_weapon_slots +
            self.allowed_accessory_slots
        )
        self.allowed_armor_types = profile_data["ALLOWED_ARMOR_TYPES"]
        self.allowed_weapon_types = profile_data["ALLOWED_WEAPON_TYPES"]
        self.allowed_types = self.allowed_armor_types + self.allowed_weapon_types

        # **Directly assign integer values** from the profile data
        try:
            self.MIN_ILVL = int(profile_data["MIN_ILVL"])  # Ensure it is treated as an integer
            self.MAX_ILVL = int(profile_data["MAX_ILVL"])  # Ensure it is treated as an integer
            self.STAT_DISTRIBUTION_THRESHOLDS = profile_data.get("STAT_DISTRIBUTION_THRESHOLDS", {})
        except ValueError as e:
            raise ValueError(f"Invalid integer value in profile data: {e}")
        
        gold_value = profile_data.get("MAX_BUYOUT_GOLD", profile_data.get("MAX_BUYOUT"))
        self.MAX_BUYOUT = int(gold_value) * 10000


def parse_filter_types(filter_list):
    """Separates normal and max-stat filters."""
    normal_filters = []
    max_stat_filters = set()
    for f in filter_list:
        if f.startswith("Max-"):
            max_stat_filters.add(f[4:])
        else:
            normal_filters.append(f)
    return normal_filters, max_stat_filters


def get_scan_config(profile_name):
    profile = SCAN_PROFILES.get(profile_name)
    if not profile:
        raise ValueError(f"Unknown scan profile: {profile_name}")
    # Return the ScanConfig object which is properly initialized
    return ScanConfig(profile)


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

    # Determine if we need to refresh any file
    for name in filenames:
        local_path = os.path.join(os.path.dirname(BONUS_DATA_FILE), f"{name}.json")

        if not os.path.exists(local_path):
            logging.info(f"🆕 Missing: {name}.json")
            modified = True
            break

        file_age = time.time() - os.path.getmtime(local_path)
        if file_age > 30 * 86400:
            logging.info(f"♻️  Refreshing {name}.json (older than 30 days)")
            modified = True
            break

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
    pattern = r"(\d+)\s+@plvl\s+(\d+)\s*-\s*(\d+)\s+@plvl\s+(\d+)"
    match = re.match(pattern, ilevel_str)
    if not match:
        logging.warning(f"⚠️ Unexpected ilevel string format: '{ilevel_str}'")
        return 0

    ilvl_low, plvl_low, ilvl_high, plvl_high = map(int, match.groups())

    if player_level <= plvl_low:
        return ilvl_low
    elif player_level >= plvl_high:
        return ilvl_high

    ratio = (player_level - plvl_low) / (plvl_high - plvl_low)
    return round(ilvl_low + ratio * (ilvl_high - ilvl_low))


def infer_ilvl_from_bonus_ids(base_ilvl, bonus_ids, raidbots_data, fallback_data, player_level, modifiers=None):
    total_bonus = 0
    highest_scaled_ilvl = 0
    effective_player_level = player_level

    # Allow override via modifier 9
    if modifiers:
        for mod in modifiers:
            if mod.get("type") == 9 and isinstance(mod.get("value"), int):
                effective_player_level = mod["value"]

    for b in bonus_ids:
        bid = str(b)
        bonus = raidbots_data.get(bid) or fallback_data.get(bid)
        if not bonus:
            continue
        if 'level' in bonus:
            total_bonus += bonus['level']
        elif 'ilevel' in bonus:
            scaled = parse_ilevel_string(bonus['ilevel'], effective_player_level)
            highest_scaled_ilvl = max(highest_scaled_ilvl, scaled)

    return highest_scaled_ilvl or (base_ilvl + total_bonus)


# === Utility: Infer player level from observed ilvl using curve ===
def infer_player_level_from_ilvl(observed_ilvl, curve_points):
    """Infers the player level that would result in the observed item level using the given curve."""
    if not curve_points:
        return None, None
    closest = min(curve_points, key=lambda pt: abs(pt["itemLevel"] - observed_ilvl))
    return closest["playerLevel"], closest["itemLevel"]


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
    Perform an HTTP request with retry logic and dynamic rate-limiting.

    Throttles global request rate to stay below MAX_REQUESTS_PER_SEC.

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
    # === Throttle to max 3.5 requests/sec ===
    now = time.time()
    if throttle_tracker['start_time'] is None:
        throttle_tracker['start_time'] = now
        throttle_tracker['request_count'] = 0

    throttle_tracker['request_count'] += 1
    debug_stats['blizzard_requests'] += 1
    elapsed = now - throttle_tracker['start_time']
    actual_rps = throttle_tracker['request_count'] / elapsed if elapsed > 0 else 0
    
    if PRINT_FULL_METADATA:
        print(f"[Throttle] Requests: {throttle_tracker['request_count']}, Elapsed: {elapsed:.2f}s, RPS: {actual_rps:.2f}")

    if actual_rps > MAX_REQUESTS_PER_SEC:
        ideal_delay = (throttle_tracker['request_count'] / MAX_REQUESTS_PER_SEC) - elapsed
        if ideal_delay > 0:
            time.sleep(ideal_delay)

    # === Retry logic ===
    for attempt in range(1, retries + 1):
        
        # Prints full metadata for debugging
        if PRINT_FULL_METADATA:
            if "connected-realm" in url and "auctions" in url:
                logging.debug("📡 Auction House request\n")
                debug_stats['auction_calls'] += 1
            elif "item/" in url:
                logging.debug("📦 Item metadata request")
            else:
                logging.debug(f"🔍 Other Blizzard API request: {url}")

        # Get a new token if expired
        resp = session.request(method, url, params=params)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', '1'))
            logging.warning("⚠️ Rate limited; sleeping %ds (attempt %d/%d)", retry_after, attempt, retries)
            time.sleep(retry_after)
            continue
        if resp.status_code == 401:
            if os.path.isfile(TOKEN_CACHE):
                os.remove(TOKEN_CACHE)
            raise RuntimeError("Unauthorized: cached token invalid or expired")
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


def parse_timestamp(ts_str):
    try:
        return time.mktime(time.strptime(ts_str, "%Y-%m-%dT%H:%M:%S"))
    except:
        return 0
        

def load_or_init_scan_order(realm_map, filename=LOADED_SERVERS_CSV):
    """
    Load scan order from CSV or initialize if missing.
    Prioritizes: (1) never scanned, (2) outdated, (3) least recently scanned (until MAX_REALMS).
    """
    now = time.time()
    expiry_threshold = now - (SCAN_EXPIRY_DAYS * 86400)
    all_known = {}

    # Merge realm_map with scan history to ensure all realms are present
    all_known = {}
    scan_cache = {}

    # Load existing scan history if available
    if os.path.exists(filename):
        try:
            with open(filename, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rid = int(row['realm_id'])
                    scan_cache[rid] = {
                        'realm_name': row['realm_name'],
                        'last_scanned': row.get('last_scanned', '0')
                    }
        except Exception as e:
            logging.warning(f"⚠️ Failed to load scan history: {e}")

    # For every realm in realm_map, apply scan history or mark as never scanned
    for slug, info in realm_map.items():
        rid = info['id']
        cached = scan_cache.get(rid, {})
        all_known[rid] = {
            'realm_name': info['name'],
            'last_scanned': cached.get('last_scanned', '0')
        }

    # Rewrite the full merged scan cache
    try:
        # Write back updated file without reordering
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['realm_id', 'realm_name', 'last_scanned'])
            writer.writeheader()
            for rid, data in all_known.items():
                writer.writerow({
                    'realm_id': rid,
                    'realm_name': data['realm_name'],
                    'last_scanned': data['last_scanned']
                })
    except Exception as e:
        logging.warning(f"⚠️ Failed to write updated scan cache: {e}")
        
    # Force preferred realm name for connected realm 3721
    if 3721 in all_known:
        all_known[3721]['realm_name'] = "Caelestrasz"

    # === Prioritize: never scanned > stale > recent (sorted by oldest scan time)
    def sort_priority(entry):
        ts = parse_timestamp(entry[1]['last_scanned'])
        if ts == 0:
            return (0, 0)  # Never scanned
        elif ts < expiry_threshold:
            return (1, ts)  # Outdated scan
        else:
            return (2, ts)  # Recent scan (least recently scanned last)

    sorted_realms = sorted(all_known.items(), key=sort_priority)

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
    Retrieve item metadata (level, name, item type, and slot) from Blizzard API or cache.

    Args:
        session (requests.Session): Active HTTP session.
        headers (dict): Authorization headers.
        item_id (int): Unique Blizzard item ID.
        cache (dict): Local cache mapping IDs to metadata.

    Returns:
        dict: Cached metadata including item_type, item_category, slot_type, and required_level.
    """
    if item_id in cache:
        debug_stats['item_metadata_hits'] += 1
        if PRINT_FULL_METADATA and not globals().get('suppress_inline_debug', False):
            print(f"[DEBUG] 📦 [Cache Hit] Item {item_id}", file=sys.stderr)
        return cache[item_id]

    debug_stats['item_metadata_misses'] += 1

    url = f"{BASE_URL.format(region=REGION)}/data/wow/item/{item_id}"
    params = {'namespace': REGION_NS[REGION]['static'], 'locale': 'en_US'}
    data = request_with_retry(session, 'GET', url, params)

    # Extract item fields
    name_field = data.get('name')
    name = name_field if isinstance(name_field, str) else name_field.get('en_US', f"item_{item_id}")
    ilvl = data.get('level', 0)

    # Required level
    required_level = data.get("requirements", {}).get("level", {}).get("value") or data.get('required_level', 60)

    # Determine item type (e.g., Plate, Bow) and category (Weapon, Armor, etc.)
    subclass_info = data.get("item_subclass", {})
    item_type = subclass_info.get("name", "Unknown")
    item_class_id = data.get("item_class", {}).get("id")

    if item_class_id == 2:
        item_category = "Weapon"
    elif item_class_id == 4:
        item_category = "Armor"
    else:
        item_category = "Misc"

    # Determine inventory slot
    inv_data = data.get('inventory_type', {})
    slot_id = inv_data.get('id')
    slot_type = INVENTORY_TYPE_MAP.get(slot_id) or inv_data.get("name") or inv_data.get("type", "Other")

    # Save to cache
    cache[item_id] = {
        'name': name, 
        'ilvl': ilvl, 
        'required_level': required_level,
        'item_category': item_category,
        'item_type': item_type,
        'slot_type': slot_type,
        'raw_stats': data.get('preview_item', {}).get('stats', [])
    }

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
    
    
def filter_stat_bonuses(bonuses, raidbots_data, fallback_data, scan_config, info=None):
    """
    Filter and process stat bonuses based on per-stat thresholds from scan_config.

    Args:
        bonuses (list): List of bonus IDs associated with the item.
        raidbots_data (dict): Data from Raidbots API.
        fallback_data (dict): Fallback data for stat bonuses.
        scan_config (ScanConfig): The current scan configuration.
        info (dict): Item metadata with raw stats (for fallback).

    Returns:
        tuple: (bool passed, list of stat check lines, reason string)
    """

    # Mapping long stat names to filter keys
    STAT_NAME_MAP = {
        "Critical Strike": "Crit",
        "Versatility": "Vers",
        "Mastery": "Mastery",
        "Haste": "Haste"
    }

    thresholds = scan_config.STAT_DISTRIBUTION_THRESHOLDS or {}
    appended_stats = set()
    stat_check_details = []
    stat_above_threshold = False
    stat_threshold_reason = "(⛔ No stat met required threshold)"

    # Helper to process and track results
    def process_stat(stat_str, short_stat, pct_val):
        if stat_str not in appended_stats:
            appended_stats.add(stat_str)
            threshold = thresholds.get(short_stat, 0)
            if pct_val >= threshold:
                stat_check_details.append(f"{stat_str} → ✅ PASS")
                return True
            else:
                stat_check_details.append(f"{stat_str} → FAIL")
        return False

    # === Check Raidbots bonuses first ===
    all_stat_ids = set(HASTE_IDS + CRIT_IDS + VERS_IDS + MASTERY_IDS)
    for bid in bonuses:
        if bid not in all_stat_ids:
            continue
        bonus = raidbots_data.get(str(bid)) or fallback_data.get(str(bid))
        if not bonus or 'stats' not in bonus:
            continue

        # Clean stats and extract percentages
        stat_entries = [p.strip().split(" [")[0] for p in bonus['stats'].split(",")]
        for stat in stat_entries:
            if "%" not in stat:
                continue
            try:
                pct_val = int(stat.split("%")[0])
                stat_name_full = stat.split("%")[1].strip()
                short_stat = STAT_NAME_MAP.get(stat_name_full, stat_name_full)
                passed = process_stat(stat, short_stat, pct_val)
                if passed and not stat_above_threshold:
                    stat_above_threshold = True
                    stat_threshold_reason = f"(✅ {short_stat} ≥ {pct_val}%)"
            except Exception:
                continue
        if stat_above_threshold:
            break

    # === Fallback to raw_stats if needed ===
    if not stat_above_threshold and info:
        raw_stats = info.get("raw_stats", [])
        secondary_stats = [
            s for s in raw_stats
            if not s.get("is_negated") and s.get("type", {}).get("name") in STAT_NAME_MAP
        ]
        total = sum(s.get("amount", 0) or s.get("value", 0) for s in secondary_stats)

        if total > 0:
            for s in secondary_stats:
                val = s.get("amount", 0) or s.get("value", 0)
                pct = (val / total) * 100
                full_name = s['type']['name']
                short_stat = STAT_NAME_MAP.get(full_name, full_name)
                stat_str = f"{round(pct)}% {full_name}"
                if process_stat(stat_str, short_stat, pct):
                    stat_above_threshold = True
                    stat_threshold_reason = f"(✅ {round(pct)}% {full_name})"
                    break

    return stat_above_threshold, stat_check_details, stat_threshold_reason


def extract_stat_display_strings(item_id, bonuses, raidbots_data, item_cache, color=True):
    """
    Extracts stat display strings (e.g., '71% Haste', '29% Crit') from bonuses or fallback.
    Applies colouring to max or fallback stats if specified.
    """
    stat1, stat2 = "—", "—"
    bonus_found = False

    # === Helper functions ===
    def color_max_stat(s):
        if s.startswith("71% "):
            return f"\033[33mMax {s[4:]}\033[0m"
        if s.startswith("Max "):
            return f"\033[33m{s}\033[0m"
        if s.startswith("100% "):
            return f"\033[33m{s}\033[0m"
        return s

    def grey_text(s):
        return f"\033[90m{s}\033[0m" if color else s

    # === Bonus-based stats ===
    for bid in bonuses:
        bonus = raidbots_data.get(str(bid))
        if not bonus or 'stats' not in bonus:
            continue

        stat_string = bonus['stats']
        if not any(stat_name in stat_string for stat_name in ("Haste", "Crit", "Vers", "Mastery")):
            continue

        parts = [p.strip().split(' [')[0] for p in stat_string.split(',')]
        parts.sort(key=lambda s: 0 if "Haste" in s else 1)

        if len(parts) > 0:
            stat1 = color_max_stat(parts[0]) if color else parts[0]
        if len(parts) > 1:
            stat2 = color_max_stat(parts[1]) if color else parts[1]

        bonus_found = True
        break

    # === Fallback metadata ===
    if not bonus_found:
        item_info = item_cache.get(item_id, {})
        raw_stats = item_info.get("raw_stats", [])
        secondary_stats = []
        for s in raw_stats:
            if s.get("is_negated"):
                continue
            stat_name = s.get("type", {}).get("name", "")
            stat_value = s.get("value") or s.get("amount", 0)
            if stat_name in ("Haste", "Critical Strike", "Versatility", "Mastery") and stat_value > 0:
                secondary_stats.append({"name": stat_name, "amount": stat_value})

        total = sum(s["amount"] for s in secondary_stats)
        if total > 0:
            def short(s):
                return (
                    "Crit" if s == "Critical Strike" else
                    "Vers" if s == "Versatility" else s
                )
            sorted_stats = sorted(
                secondary_stats,
                key=lambda s: (0 if s["name"] == "Haste" else 1, -s["amount"])
            )
            pct_parts = [f"{round(s['amount'] / total * 100)}% {short(s['name'])}" for s in sorted_stats[:2]]
            if len(pct_parts) > 0:
                stat1 = grey_text(pct_parts[0])
            if len(pct_parts) > 1:
                stat2 = grey_text(pct_parts[1])

    return stat1, stat2


def scan_realm_with_bonus_analysis(session, headers, realm_id, realm_name, item_cache, raidbots_data, fallback_data, curve_data, scan_config, active_filters, max_stat_filters):
    logging.info(f"🔍 Scanning realm ID {realm_id}: {realm_name}")
    url = f"{BASE_URL.format(region=REGION)}/data/wow/connected-realm/{realm_id}/auctions"
    params = {'namespace': REGION_NS[REGION]['dynamic'], 'locale': 'en_US'}
    data = request_with_retry(session, 'GET', url, params)

    results = []

    for auc in data.get('auctions', []):
        item = auc.get('item')
        if not item or not isinstance(item, dict):
            continue

        modifiers = auc.get("modifiers") or auc.get("item_modifiers") or auc.get("item", {}).get("modifiers", [])
        if not isinstance(modifiers, list):
            modifiers = []
        mod_str = ", ".join([f"{m['type']}→{m['value']}" for m in modifiers]) if modifiers else "None"

        bonuses = list(set(auc.get('bonus_lists', []) + item.get('bonus_lists', [])))
        if not all(set(bonuses) & active_filters[f] for f in active_filters):
            continue

        if max_stat_filters:
            found_max = False
            for bid in bonuses:
                bonus = raidbots_data.get(str(bid)) or fallback_data.get(str(bid))
                if bonus and 'stats' in bonus:
                    stats_cleaned = [p.strip().split(" [")[0] for p in bonus['stats'].split(",")]
                    for s in stats_cleaned:
                        if s.startswith("71% "):
                            stat_name = s[4:]
                            if stat_name in max_stat_filters:
                                found_max = True
                                break
                if found_max:
                    break
            if not found_max:
                continue

        info = fetch_item_info(session, headers, item['id'], item_cache)

        # In main(), ensure scan_config is passed as the full ScanConfig object
        stat_above_threshold, stat_check_details, stat_threshold_reason = filter_stat_bonuses(bonuses, raidbots_data, fallback_data, scan_config, info)
   
        observed_ilvl = get_observed_ilvl(auc, info)
        base_ilvl = observed_ilvl
        final_ilvl = None
        level_reason = ""

        is_legacy = any(b in LEGACY_BONUS_IDS for b in bonuses)

        if is_legacy:
            try:
                player_level = next((m["value"] for m in modifiers if m["type"] == 9), None)
                if player_level:
                    curve_id = next((str(bonus["curveId"]) for b in bonuses
                                     if (bonus := raidbots_data.get(str(b)) or fallback_data.get(str(b))) and "curveId" in bonus), None)
                    if curve_id:
                        points = curve_data.get(curve_id, {}).get("points", [])
                        for pt in points:
                            if pt["playerLevel"] <= player_level:
                                final_ilvl = pt["itemLevel"]
                            else:
                                break
                        level_reason = f"✅ Legacy curve {curve_id} @ level {player_level}"
                    else:
                        level_reason = "⛔ No curveId in legacy bonus IDs"
                else:
                    level_reason = "⛔ No modifier type 9 (player level)"
            except Exception as e:
                level_reason = f"⛔ Curve logic error: {e}"

            if not final_ilvl:
                final_ilvl = observed_ilvl
                level_reason += " | fallback to observed"
        else:
            curve_id = next((bonus.get("curveId") for b in bonuses
                             if (bonus := raidbots_data.get(str(b)) or fallback_data.get(str(b))) and "curveId" in bonus), None)
            if curve_id:
                points = curve_data.get(str(curve_id), {}).get("points", [])
                _, corrected_ilvl = infer_player_level_from_ilvl(base_ilvl, points)
                final_ilvl = corrected_ilvl or observed_ilvl
                level_reason = f"✅ Retail curve {curve_id} inferred"
            else:
                final_ilvl = infer_ilvl_from_bonus_ids(
                    base_ilvl, bonuses, raidbots_data, fallback_data,
                    player_level=info.get('required_level', 60)
                ) or observed_ilvl
                level_reason = "✅ Fallback bonus-based ilvl"

        stat_match_ids = []
        match_sources = {}
        for bid in bonuses:
            matched = []
            if bid in HASTE_IDS: matched.append("HASTE_IDS")
            if bid in CRIT_IDS: matched.append("CRIT_IDS")
            if bid in VERS_IDS: matched.append("VERS_IDS")
            if bid in MASTERY_IDS: matched.append("MASTERY_IDS")
            if matched:
                stat_match_ids.append(bid)
                match_sources[bid] = matched

        # === Stat1/Stat2 extraction ===
        stat1, stat2 = extract_stat_display_strings(item['id'], bonuses, raidbots_data, item_cache, color=False)

        fallback_reason = (
            f"❌ No usable stat info found for item {item['id']}"
            if stat1.strip() == "—"
            else f"♻️  Stats: {stat1}, {stat2}"
        )

        result = {
            'realm_id': realm_id,
            'item_id': item['id'],
            'name': info['name'],
            'ilvl': final_ilvl,
            'quantity': auc.get('quantity'),
            'buyout': auc.get('buyout'),
            'type': info.get('item_type'),
            'slot': info.get('slot_type'),
            'bonus_lists': bonuses,
            'stat1': stat1,
            'stat2': stat2
        }

        # === Print Full Metadata ===
        if PRINT_FULL_METADATA:
            sys.stderr.flush()
            print(f"📦 Full Metadata for '{info['name']}'")
            print(f"🧾 Item ID       : {item['id']}")
            print(f"📏 Observed ilvl : {observed_ilvl}")
            print(f"📈 Final ilvl    : {final_ilvl} ({level_reason})")
            print(f"🎚️  Required Level: {info.get('required_level', '—')}")
            print(f"⛓️  Item Type     : {info.get('item_type', 'Unknown')}")
            print(f"🎯 Slot Type     : {info.get('slot_type', 'Unknown')}")
            print(f"🎫 Bonus IDs     : {bonuses}")
            if stat_match_ids:
                summary = ', '.join(f"{bid} ({'/'.join(match_sources[bid])})" for bid in stat_match_ids)
                print(f"🧬 Stat Info     : [{', '.join(map(str, stat_match_ids))}] (✅ Bonus ID match: {summary})")
            else:
                print("🧬 Stat Info     : No stat bonus IDs found | Using fallback method")
            print(f"🧪 Stat Check    : {'| '.join(stat_check_details)}")
            print(f"🔧 Modifiers     : {mod_str}")
            print(f"💰 Buyout        : {auc.get('buyout')}")
            print("-" * 60)

        # === Filtering by buyout price ===
        buyout = auc.get('buyout')
        if buyout is not None and buyout > scan_config.MAX_BUYOUT:
            if PRINT_FULL_METADATA:
                g_price = buyout // 10000
                print(f"⛔ Rejected: Buyout {g_price}g exceeds max {scan_config.MAX_BUYOUT // 10000}g\n")
            continue

        # === Filtering by stat distribution ===
        if not stat_above_threshold:
            if PRINT_FULL_METADATA:
                print(f"⛔ Rejected: Stat distribution below threshold {stat_threshold_reason}\n")
            continue

        # === Filtering by slot and type ===
        slot = info['slot_type']
        item_type = info['item_type']

        if not (scan_config.MIN_ILVL <= final_ilvl <= scan_config.MAX_ILVL):
            if PRINT_FULL_METADATA:
                print(f"⛔ Rejected: Item level {final_ilvl} is outside allowed range {scan_config.MIN_ILVL}–{scan_config.MAX_ILVL}\n")
            continue

        if slot not in scan_config.allowed_slots:
            if PRINT_FULL_METADATA:
                print(f"⛔ Rejected: Slot '{slot}' is not in allowed slot list (ALLOWED_ARMOR_SLOTS + ALLOWED_WEAPON_SLOTS + ALLOWED_ACCESSORY_SLOTS)\n")
            continue

        if slot in scan_config.allowed_armor_slots and item_type not in scan_config.allowed_armor_types:
            if PRINT_FULL_METADATA:
                print(f"⛔ Rejected: Armor type '{item_type}' is not in ALLOWED_ARMOR_TYPES\n")
            continue

        if slot in scan_config.allowed_weapon_slots:
            if not (item_type in scan_config.allowed_weapon_types or
                    (item_type == "Miscellaneous" and slot in {"Held In Off-hand", "Off-Hand", "Off Hand", "Holdable"})):
                if PRINT_FULL_METADATA:
                    print(f"⛔ Rejected: Weapon type '{item_type}' is not in ALLOWED_WEAPON_TYPES (or not a valid off-hand type)\n")
                continue

        if slot in scan_config.allowed_accessory_slots and item_type not in scan_config.allowed_types:
            if PRINT_FULL_METADATA:
                print(f"⛔ Rejected: Item type '{item_type}' is not in ALLOWED_ARMOR_TYPES + ALLOWED_WEAPON_TYPES\n")
            continue

        if PRINT_FULL_METADATA:
            print(f"✅ Accepted | item_type: '{item_type}' in allowed list\n              "
                  f"slot_type: '{slot}' in allowed slots\n")

        results.append(result)

    return results


def write_csv(results, filename=CSV_FILENAME):
    """
    Write the final scan results to a CSV file.
    """
    realm_names = {}
    if os.path.exists(REALM_CSV):
        with open(REALM_CSV, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                realm_names[int(row['connected_realm_id'])] = row['name']

    def plain_max_label(s):
        if s.startswith("71% "):
            return f"Max {s[4:]}"
        if s.startswith("100% "):
            return f"Max {s[5:]}"
        return s

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'realm', 'item_id', 'type', 'slot', 'stat1', 'stat2', 'name', 'ilvl', 'buyout_gold'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                'realm': realm_names.get(r['realm_id'], f"Realm-{r['realm_id']}"),
                'item_id': r['item_id'],
                'type': r.get('type', 'Unknown'),
                'slot': r.get('slot', 'Unknown'),
                'stat1': plain_max_label(r.get('stat1', '—')),
                'stat2': plain_max_label(r.get('stat2', '—')),
                'name': r['name'],
                'ilvl': r['ilvl'],
                'buyout_gold': (int(r['buyout']) // 10000) if r['buyout'] else 0
            })


# === USER INTERFACE ===
def select_scan_profile():
    """Prompts the user to choose between full and custom scan profiles."""
    choice = input(f"{'Item Profile':<13} | Custom(1), Everything(2), Profitable(3): ").strip() or "1"
    if choice == "1":
        return "custom"
    elif choice == "2":
        return "full"
    elif choice == "3":
        return "profitable"
    else:
        print("❌ Invalid choice. Defaulting to 'full' scan profile.")
        return "full"
    

def select_scan_type():
    """Prompts the user to choose between a test scan or a full scan, returning the mode and test realm if applicable."""
    choice = input(f"{'Scan Type':<13} | Single Realm(1) or All Realms(2): ").strip() or "2"
    if choice == "1":
        test_realm = input(f"{'Realm Choice':<13} | Enter the realm name or ID: ").strip()
        return True, test_realm
    return False, None


def print_item_row(r, realms, raidbots_data, item_cache, color=True):
    """Prints a formatted row of item data to the console, using bonus stats first, then falling back to base item stats."""
    realm_name = next((n for i, n in realms if i == r['realm_id']), f"Realm-{r['realm_id']}")
    item_id = r['item_id']
    name = r['name']
    ilvl = r['ilvl']
    gold = int(r['buyout']) // 10000 if r['buyout'] else 0
    item_type = r.get('type', 'Unknown')
    item_slot = r.get('slot', 'Unknown')
    bonus_ids = set(r.get('bonus_lists', []))

    # === Stat helpers ===
    def strip_ansi(text):
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    # === Use extracted display function ===
    stat1, stat2 = extract_stat_display_strings(item_id, bonus_ids, raidbots_data, item_cache, color=color)

    # === Align ANSI-colored stat columns ===
    raw1 = strip_ansi(stat1)
    raw2 = strip_ansi(stat2)
    stat1_str = stat1 + ' ' * max(0, 16 - len(raw1))
    stat2_str = stat2 + ' ' * max(0, 16 - len(raw2))

    # === Other fields ===
    realm_str = f"✅ {realm_name:<20}"
    item_id_str = f"{item_id:<11}"
    type_str = f"{item_type:<16}"
    slot_str = f"{item_slot:<17}"
    name_str = f"{name:<36}"
    ilvl_str = f"{ilvl:>8}"
    gold_str = f"{gold:>13,}".replace(",", "'")

    if color:
        ilvl_str = f"\033[94m{ilvl_str}\033[0m"
        gold_str = f"{gold_str}\033[33mg\033[0m"

    print(f"{realm_str}{item_id_str}{type_str}{slot_str}{stat1_str}{stat2_str}{name_str}{ilvl_str} {gold_str}")

# === Helper functions for Main() ===
def prepare_session_and_data():
    """Authenticates, loads realm map, Raidbots, fallback and curve data, and returns session + data packages."""
    token = get_token()
    headers = {'Authorization': f'Bearer {token}'}
    session = requests.Session()
    session.headers.update(headers)

    load_realm_map(session, headers)
    raidbots_bundle = fetch_raidbots_data()
    raidbots_data = raidbots_bundle.get('bonuses', {})

    fallback_data_path = os.path.join(os.path.dirname(BONUS_DATA_FILE), "bonuses.json")
    with open(fallback_data_path, 'r', encoding='utf-8') as f:
        fallback_data = json.load(f)

    with open(Path(os.path.dirname(BONUS_DATA_FILE)) / "item-curves.json", 'r', encoding='utf-8') as f:
        curve_data = json.load(f)

    return session, headers, raidbots_data, fallback_data, curve_data


def determine_realms(test_mode, test_realm):
    """Returns a list of (realm_id, display_name) tuples based on scan type."""
    if test_mode:
        realm_id, display_name = resolve_realm_input(test_realm)
        return [(realm_id, display_name)]
    try:
        return load_or_init_scan_order(realm_map)
    except Exception as e:
        logging.warning(f"⚠️ Failed to load scan order. Falling back to default order. Reason: {e}")
        return [(info['id'], info['name']) for info in realm_map.values()][:MAX_REALMS]


def scan_realms(realms, session, headers, raidbots_data, fallback_data, curve_data, scan_config, active_filters, max_stat_filters, test_mode):
    """Performs the full realm scanning loop and returns all matching results."""
    all_results = []
    item_cache = {}

    for rid, display_name in tqdm(realms, desc='Scanning', unit='realm'):
        all_results.extend(
            scan_realm_with_bonus_analysis(
                session, headers, rid, display_name,
                item_cache, raidbots_data, fallback_data, curve_data,
                scan_config, active_filters, max_stat_filters
            )
        )
        if not test_mode:
            try:
                update_single_scan_timestamp(rid, display_name)
            except Exception as e:
                logging.warning(f"⚠️ Failed to write scan cache for realm {display_name} ({rid}): {e}")
    
    return all_results, item_cache


def display_results(results, realms, raidbots_data, item_cache, filter_str):
    """Writes CSV and prints output if results exist."""
    if results:
        write_csv(results)
        results.sort(key=lambda x: x['ilvl'], reverse=True)

        print(f"\n{'Realm':<22} {'Item ID':<10} {'Type':<15} {'Slot':<16} {'Stat 1':<15} {'Stat 2':<15} {'Name':<36} {'ilvl':>8} {'Buyout':>11}")
        for r in results:
            print_item_row(r, realms, raidbots_data, item_cache)
        print(f"\033[92m\nFound \033[93m{len(results)} \033[92mitems matching the filters: \033[94m{filter_str}\033[0m\n")
    else:
        logging.info("❌ No matching Speed-stat items found.")


def print_scan_summary(start_time, realms_scanned):
    """Prints performance and cache efficiency statistics."""
    total_time = perf_counter() - start_time
    rps_total = debug_stats['blizzard_requests'] / total_time if total_time > 0 else 0
    metadata_total = debug_stats['item_metadata_hits'] + debug_stats['item_metadata_misses']
    cache_hit_rate = debug_stats['item_metadata_hits'] / max(metadata_total, 1)

    if PRINT_FULL_METADATA:
        print("📊 === SCAN SUMMARY ===")
        print(f"⏱️  Time Elapsed          : {total_time:.2f} seconds")
        print(f"🌐 Realms Scanned        : {realms_scanned}")
        print(f"📦 Item Metadata Requests: {metadata_total}")
        print(f"    ├─ Cache Hits        : {debug_stats['item_metadata_hits']}")
        print(f"    └─ Cache Misses      : {debug_stats['item_metadata_misses']}")
        print(f"🎯 Cache Hit Rate        : {cache_hit_rate:.2%}")
        print(f"🔁 Blizzard API Requests : {debug_stats['blizzard_requests']}")
        print(f"    ├─ Auction Scans     : {debug_stats['auction_calls']}")
        print(f"    └─ Metadata Fetches  : {debug_stats['blizzard_requests'] - debug_stats['auction_calls']}")
        print(f"🚀 Effective RPS         : {rps_total:.2f}\n")


# === MAIN EXECUTION ===
def main():
    """
    Main entry point for the script.
    Handles authentication, realm loading, scanning, and output.
    """
    # === Determine scan profile
    if args.config and os.path.exists(args.config):
        with open(args.config, "r") as f:
            config = json.load(f)
            # Custom profile already injected earlier
            profile_name = "custom"
            test_mode = config.get("scan_mode") == "single"
            test_realm = config.get("realm") if test_mode else None
    else:
        profile_name = select_scan_profile()
        test_mode, test_realm = select_scan_type()

    scan_config = get_scan_config(profile_name)

    session, headers, raidbots_data, fallback_data, curve_data = prepare_session_and_data()
    realms = determine_realms(test_mode, test_realm)

    normal_filters, max_stat_filters = parse_filter_types(scan_config.filter_type)
    active_filters = {f: set(FILTER_ID_MAP[f]) for f in normal_filters if f in FILTER_ID_MAP}
    filter_str = ", ".join(scan_config.filter_type)

    logging.info(f"🔍 Scanning {len(realms)} realm(s) for {filter_str} gear (ilvl {scan_config.MIN_ILVL}-{scan_config.MAX_ILVL})...")

    start_time = perf_counter()
    results, item_cache = scan_realms(realms, session, headers, raidbots_data, fallback_data, curve_data, scan_config, active_filters, max_stat_filters, test_mode)
    display_results(results, realms, raidbots_data, item_cache, filter_str)
    print_scan_summary(start_time, len(realms))

        
if __name__ == '__main__':
    main()
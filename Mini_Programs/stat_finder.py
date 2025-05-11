import json

# === CONFIGURATION ===
# Change this to: "Haste", "Crit", "Vers", or "Mastery"
TARGET_STAT_NAME = "Mastery"

# === Stat ID mapping ===
STAT_ID_MAP = {
    "Haste": 36,
    "Crit": 32,
    "Vers": 40,
    "Mastery": 49
}

# Validate and retrieve ID
if TARGET_STAT_NAME not in STAT_ID_MAP:
    raise ValueError(f"❌ Invalid stat: {TARGET_STAT_NAME}. Choose from {list(STAT_ID_MAP)}")
TARGET_STAT_ID = STAT_ID_MAP[TARGET_STAT_NAME]

# === Load bonus data ===
with open("RaidBots_APIs/bonus_data_cache.json", "r", encoding="utf-8") as f:
    bonus_data = json.load(f)

matching_ids = []

print(f"=== BONUS IDS WITH {TARGET_STAT_NAME.upper()} STATS ===\n")
print(f"{'ID':<6} {'Suffix':<30} {'Stat 1':<30} {'Stat 2':<30}")

for bid_str, bonus in bonus_data.items():
    bid = int(bid_str)
    name = bonus.get("name", "—")
    stats = bonus.get("rawStats", [])

    if not isinstance(stats, list) or not stats:
        continue

    has_target_stat = any(
        isinstance(s.get("stat"), int) and s["stat"] == TARGET_STAT_ID and isinstance(s.get("amount"), (int, float))
        for s in stats
    )

    if has_target_stat:
        def stat_display(s):
            label = s.get("name") or f"Stat {s.get('stat', '?')}"
            amt = s.get("amount", "?")
            return f"{label} ({amt})"

        stat1 = stat_display(stats[0]) if len(stats) > 0 else "-"
        stat2 = stat_display(stats[1]) if len(stats) > 1 else "-"
        print(f"{bid:<6} {name:<30} {stat1:<30} {stat2:<30}")
        matching_ids.append(bid)

# === Summary ===
print(f"\n✅ Found {len(matching_ids)} bonus IDs with {TARGET_STAT_NAME}.\n")
print(f"{TARGET_STAT_NAME.upper()}_BONUS_IDS = {{")
for h in sorted(matching_ids):
    print(f"    {h},")
print("}")

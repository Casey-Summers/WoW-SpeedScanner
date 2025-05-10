import json

# Load all bonus data
with open("RaidBots_APIs/bonus_data_cache.json", "r", encoding="utf-8") as f:
    bonus_data = json.load(f)

haste_ids = []

print("=== BONUS IDS WITH HASTE STATS ===\n")
print(f"{'ID':<6} {'Suffix':<25} {'Stat 1':<30} {'Stat 2':<30}")

for bid_str, bonus in bonus_data.items():
    bid = int(bid_str)
    name = bonus.get("name", "—")
    stats = bonus.get("rawStats", [])

    # Skip bonuses without valid stat info
    if not isinstance(stats, list):
        continue

    # Detect haste using stat ID 36 (safe, regardless of label)
    has_haste = any(
        s.get("stat") == 36 and isinstance(s.get("amount"), (int, float))
        for s in stats
    )

    if has_haste:
        stat1 = (
            f"{stats[0].get('name', stats[0].get('stat'))} ({stats[0].get('amount')})"
            if len(stats) > 0 else "-"
        )
        stat2 = (
            f"{stats[1].get('name', stats[1].get('stat'))} ({stats[1].get('amount')})"
            if len(stats) > 1 else "-"
        )
        print(f"{bid:<6} {name:<25} {stat1:<30} {stat2:<30}")
        haste_ids.append(bid)

# Summary
print(f"\n✅ Found {len(haste_ids)} bonus IDs with Haste.")
print("\nHASTE_BONUS_IDS = {")
for h in sorted(haste_ids):
    print(f"    {h},")
print("}")

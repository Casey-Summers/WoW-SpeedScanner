import json

# Load all bonus data
with open("bonus_data_cache.json", "r", encoding="utf-8") as f:
    bonus_data = json.load(f)

socket_ids = []

print("=== BONUS IDS WITH SOCKET FLAG ===\n")
print(f"{'ID':<6} {'Name':<40}")

for bid_str, bonus in bonus_data.items():
    bid = int(bid_str)
    if not isinstance(bonus, dict):
        continue

    if bonus.get("socket") == 1:
        name = bonus.get("name", "—")
        print(f"{bid:<6} {name:<40}")
        socket_ids.append(bid)

# Summary
print(f"\n✅ Found {len(socket_ids)} bonus IDs with socket = 1.\n")
print("SOCKET_BONUS_IDS = {")
for sid in sorted(socket_ids):
    print(f"    {sid},")
print("}")

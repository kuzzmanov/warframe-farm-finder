#!/usr/bin/env python3
"""Build a compact, same-origin search index from WFCD's published drop tables."""
import json, os, urllib.request
from datetime import datetime, timezone

URL = "https://raw.githubusercontent.com/WFCD/warframe-drop-data/main/data/all.json"
os.makedirs("data", exist_ok=True)
request = urllib.request.Request(URL, headers={"User-Agent": "Warframe-Farm-Finder/1.0", "Accept": "application/json"})
with urllib.request.urlopen(request, timeout=120) as response:
    data = json.load(response)

records, seen = [], set()
name_keys = ("itemName", "modName", "item_name", "item", "name", "title")
skip_path_keys = {"missionRewards", "relics", "modLocations", "miscItems", "blueprintLocations", "transientRewards", "rewards", "drops", "items"}
context_labels = {
    "planet": "Planet", "mission": "Mission", "node": "Node", "gameMode": "Mode",
    "enemyName": "Enemy", "place": "Location", "objectiveName": "Objective",
    "bountyLevel": "Bounty", "stage": "Stage", "rotation": "Rotation",
    "syndicate": "Syndicate", "location": "Location", "state": "State",
    "tier": "Tier", "relicName": "Relic"
}

def clean(value):
    if value is None:
        return ""
    return " ".join(str(value).replace("_", " ").split()).strip()

def add(title, details, chance=None, rarity=None, category="DROP DATA"):
    title = clean(title)
    if not title:
        return
    compact = []
    for label, value in details:
        value = clean(value)
        if not value:
            continue
        # Prefer readable source names to raw key/value pairs.
        if label == "Bounty":
            value = value.replace("Level ", "Levels ")
            compact.append(value)
        elif label == "Stage":
            compact.append(value if value.lower().startswith("stage") else "Stage " + value)
        elif label == "Rotation":
            compact.append(value if value.lower().startswith("rotation") else "Rotation " + value)
        elif label in ("Mission", "Node", "Planet", "Enemy", "Location", "Mode", "Objective", "Syndicate", "State", "Tier", "Relic"):
            compact.append(value)
        else:
            compact.append(value)
    # Remove duplicate fragments while preserving source order.
    compact = list(dict.fromkeys(compact))
    try:
        chance_num = float(chance) if chance is not None else None
    except (TypeError, ValueError):
        chance_num = None
    key = (title.casefold(), tuple(x.casefold() for x in compact), chance_num, clean(rarity).casefold())
    if key in seen:
        return
    seen.add(key)
    records.append({
        "title": title, "details": compact, "chance": chance_num,
        "rarity": clean(rarity), "category": category,
        "detail": " · ".join(compact + ([f"Chance {chance_num:g}%"] if chance_num is not None else []) + ([clean(rarity)] if rarity else []))
    })

def walk(obj, path=None, section=None):
    path = list(path or [])
    if isinstance(obj, dict):
        details = []
        for key, value in obj.items():
            if key in context_labels and isinstance(value, (str, int, float)):
                details.append((context_labels[key], value))
        title = next((obj.get(k) for k in name_keys if isinstance(obj.get(k), str) and obj.get(k).strip()), None)
        if title:
            combined = path + details
            chance = obj.get("chance", obj.get("dropChance", obj.get("dropChancePercent")))
            rarity = obj.get("rarity")
            add(title, combined, chance, rarity, "RELIC" if section == "relics" else "DROP DATA")
        tier, relic = obj.get("tier"), obj.get("relicName")
        if isinstance(tier, str) and isinstance(relic, str):
            add(f"{tier} {relic}", path + [("Tier", tier), ("Relic", relic)], category="RELIC")
        for key, value in obj.items():
            if not isinstance(value, (dict, list)):
                continue
            next_path = path + details
            next_section = section
            if key in ("missionRewards", "relics", "modLocations", "miscItems", "blueprintLocations", "transientRewards"):
                next_section = key
            elif key not in skip_path_keys and not key.startswith("_"):
                if key in ("A", "B", "C"):
                    next_path.append(("Rotation", key))
                elif key.isdigit():
                    next_path.append(("Stage", key))
                elif key not in context_labels:
                    next_path.append(("Source", key))
            walk(value, next_path, next_section)
    elif isinstance(obj, list):
        for value in obj:
            walk(value, path, section)

walk(data)
with open("data/search-index.json", "w", encoding="utf-8") as f:
    json.dump({"generatedAt": datetime.now(timezone.utc).isoformat(), "records": records}, f, ensure_ascii=False, separators=(",", ":"))
print(f"Indexed {len(records)} records")

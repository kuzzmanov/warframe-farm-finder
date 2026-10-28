#!/usr/bin/env python3
"""Build a compact, same-origin search index from WFCD's published drop tables."""
import json, os, urllib.request

URL = "https://raw.githubusercontent.com/WFCD/warframe-drop-data/main/data/all.json"
os.makedirs("data", exist_ok=True)
request = urllib.request.Request(URL, headers={"User-Agent": "Warframe-Farm-Finder/1.0", "Accept": "application/json"})
with urllib.request.urlopen(request, timeout=120) as response:
    data = json.load(response)

records = []
seen = set()
context_keys = {
    "planet", "mission", "node", "gameMode", "enemyName", "place",
    "objectiveName", "bountyLevel", "tier", "relicName", "state",
    "rotation", "stage", "syndicate", "location", "modName"
}
name_keys = ("itemName", "modName", "item_name", "item", "name", "title")

def add(title, detail, category="DROP DATA"):
    title = str(title or "").strip()
    detail = " · ".join(str(x).strip() for x in detail if x is not None and str(x).strip())
    if not title:
        return
    key = (title.casefold(), detail.casefold())
    if key in seen:
        return
    seen.add(key)
    records.append({"title": title, "detail": detail or "Open the source for drop details.", "category": category})

def walk(obj, path=None):
    path = path or []
    if isinstance(obj, dict):
        ctx = list(path)
        for k, v in obj.items():
            if k in context_keys and isinstance(v, (str, int, float)):
                ctx.append(f"{k}: {v}")
        title = None
        for k in name_keys:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                title = v.strip()
                break
        if title:
            details = [x for x in ctx if not x.lower().endswith(": " + title.lower())]
            chance = obj.get("chance", obj.get("dropChance"))
            rarity = obj.get("rarity")
            if chance is not None:
                details.append(f"Chance: {chance}%")
            if rarity:
                details.append(f"Rarity: {rarity}")
            add(title, details)
        # Relic names are assembled from separate fields in the source data.
        tier, relic = obj.get("tier"), obj.get("relicName")
        if isinstance(tier, str) and isinstance(relic, str):
            add(f"{tier} {relic}", ctx + [f"Tier: {tier}", f"Relic: {relic}"], "RELIC")
        next_path = path + [f"{k}: {v}" for k, v in obj.items()
                            if k in context_keys and isinstance(v, (str, int, float))]
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                walk(v, next_path + ([f"Section: {k}"] if k in ("missionRewards", "relics", "modLocations", "miscItems", "blueprintLocations", "transientRewards") else []))
    elif isinstance(obj, list):
        for v in obj:
            walk(v, path)

walk(data)
with open("data/search-index.json", "w", encoding="utf-8") as f:
    json.dump({"generatedAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(), "records": records}, f, ensure_ascii=False, separators=(",", ":"))
print(f"Indexed {len(records)} records")

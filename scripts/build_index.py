#!/usr/bin/env python3
"""Build a compact same-origin drop index with optional Warframe Market item thumbnails."""
import json, os, re, urllib.request
from datetime import datetime, timezone

DROP_URL = "https://raw.githubusercontent.com/WFCD/warframe-drop-data/main/data/all.json"
MARKET_URL = "https://api.warframe.market/v2/items"
ASSET_BASE = "https://warframe.market/static/assets/"
os.makedirs("data", exist_ok=True)

def fetch_json(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent":"Warframe-Farm-Finder/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)

data = fetch_json(DROP_URL)
image_by_name = {}
try:
    market = fetch_json(MARKET_URL, timeout=35)
    def find_market_items(obj):
        if isinstance(obj, dict):
            i18n = obj.get("i18n")
            en = i18n.get("en") if isinstance(i18n, dict) else None
            if isinstance(en, dict) and en.get("name"):
                path = en.get("subIcon") or en.get("thumb") or en.get("icon")
                if path:
                    image_by_name[" ".join(en["name"].casefold().split())] = path if str(path).startswith("http") else ASSET_BASE + str(path).lstrip("/")
            for value in obj.values():
                if isinstance(value, (dict, list)):
                    find_market_items(value)
        elif isinstance(obj, list):
            for value in obj:
                find_market_items(value)
    find_market_items(market)
    print(f"Loaded {len(image_by_name)} optional item thumbnails")
except Exception as exc:
    print(f"Optional item thumbnails unavailable: {exc}")

records, seen = [], set()
name_keys = ("itemName", "modName", "item_name", "item", "name", "title")
skip_path_keys = {"missionRewards", "relics", "modLocations", "miscItems", "blueprintLocations", "transientRewards", "rewards", "drops", "items"}
context_labels = {
    "planet":"Planet", "mission":"Mission", "node":"Node", "gameMode":"Mode",
    "enemyName":"Enemy", "place":"Location", "objectiveName":"Objective",
    "bountyLevel":"Bounty", "stage":"Stage", "rotation":"Rotation",
    "syndicate":"Syndicate", "location":"Location", "state":"State",
    "tier":"Tier", "relicName":"Relic"
}
relic_pattern = re.compile(r"\b(Lith|Meso|Neo|Axi|Requiem)\s+([A-Z0-9]+)(?:\s+(Intact|Exceptional|Flawless|Radiant))?\b", re.I)

def clean(value):
    if value is None: return ""
    return " ".join(str(value).replace("_", " ").split()).strip()

def add(title, details, chance=None, rarity=None, category="DROP DATA"):
    title = clean(title)
    if not title: return
    compact = []
    for label, value in details:
        value = clean(value)
        if not value: continue
        if label == "Bounty": value = value.replace("Level ", "Levels ")
        elif label == "Stage" and not value.lower().startswith("stage"): value = "Stage " + value
        elif label == "Rotation" and not value.lower().startswith("rotation"): value = "Rotation " + value
        compact.append(value)
    compact = list(dict.fromkeys(compact))
    try: chance_num = float(chance) if chance is not None else None
    except (TypeError, ValueError): chance_num = None
    relic_name, refinement = None, None
    # WFCD relic entries store tier, relicName, and state as separate fields.
    # Read those structured labels first; then fall back to parsing a combined path fragment.
    detail_map = {label.casefold(): clean(value) for label, value in details}
    tier_value = detail_map.get("tier", "")
    relic_value = detail_map.get("relic", "")
    state_value = detail_map.get("state", "")
    if tier_value and relic_value and state_value.casefold() in {"intact", "exceptional", "flawless", "radiant"}:
        relic_name = f"{tier_value.title()} {relic_value.upper()}"
        refinement = state_value.title()
    else:
        for fragment in compact:
            match = relic_pattern.search(fragment)
            if match:
                relic_name = f"{match.group(1).title()} {match.group(2).upper()}"
                refinement = (match.group(3) or "Intact").title()
                break
    key = (title.casefold(), tuple(x.casefold() for x in compact), chance_num, clean(rarity).casefold())
    if key in seen: return
    seen.add(key)
    image = image_by_name.get(" ".join(title.casefold().split()))
    records.append({
        "title":title, "details":compact, "chance":chance_num, "rarity":clean(rarity),
        "category":category, "relic":relic_name, "refinement":refinement, "image":image,
        "detail":" · ".join(compact + ([f"Chance {chance_num:g}%"] if chance_num is not None else []) + ([clean(rarity)] if rarity else []))
    })

def walk(obj, path=None, section=None):
    path = list(path or [])
    if isinstance(obj, dict):
        # Relic rewards are nested under {tier, relicName, state, rewards}.
        # Index each reward with those labels instead of skipping the relic subtree.
        if (isinstance(obj.get("tier"), str) and isinstance(obj.get("relicName"), str)
                and isinstance(obj.get("state"), str) and isinstance(obj.get("rewards"), list)):
            relic_details = path + [("Tier", obj["tier"]), ("Relic", obj["relicName"]), ("State", obj["state"])]
            for reward in obj["rewards"]:
                if isinstance(reward, dict):
                    reward_title = next((reward.get(k) for k in name_keys if isinstance(reward.get(k), str) and reward.get(k).strip()), None)
                    if reward_title:
                        add(reward_title, relic_details, reward.get("chance", reward.get("dropChance", reward.get("dropChancePercent"))),
                            reward.get("rarity"), "RELIC")
            return
        details = [(context_labels[key], value) for key, value in obj.items()
                   if key in context_labels and isinstance(value, (str, int, float))]
        title = next((obj.get(k) for k in name_keys if isinstance(obj.get(k), str) and obj.get(k).strip()), None)
        if title:
            add(title, path + details, obj.get("chance", obj.get("dropChance", obj.get("dropChancePercent"))),
                obj.get("rarity"), "RELIC" if section == "relics" else "DROP DATA")
        tier, relic = obj.get("tier"), obj.get("relicName")
        if isinstance(tier, str) and isinstance(relic, str):
            add(f"{tier} {relic}", path + [("Tier",tier),("Relic",relic)], category="RELIC")
        for key, value in obj.items():
            if not isinstance(value, (dict, list)): continue
            next_path = path + details
            next_section = key if key in ("missionRewards","relics","modLocations","miscItems","blueprintLocations","transientRewards") else section
            if key not in skip_path_keys and not key.startswith("_"):
                if key in ("A","B","C"): next_path.append(("Rotation",key))
                elif key.isdigit(): next_path.append(("Stage",key))
                elif key not in context_labels: next_path.append(("Source",key))
            walk(value, next_path, next_section)
    elif isinstance(obj, list):
        for value in obj: walk(value, path, section)

walk(data)
with open("data/search-index.json","w",encoding="utf-8") as f:
    json.dump({"generatedAt":datetime.now(timezone.utc).isoformat(),"records":records},f,ensure_ascii=False,separators=(",",":"))
print(f"Indexed {len(records)} drop records")

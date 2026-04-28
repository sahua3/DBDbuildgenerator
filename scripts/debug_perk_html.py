#!/usr/bin/env python3
"""Find the correct wiki category names for all survivor perks."""
import sys, time
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "--quiet"])
    import requests
import urllib3; urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({"User-Agent": "DBDPerkBot/1.0", "Accept": "application/json"})
API = "https://deadbydaylight.fandom.com/api.php"

def api_get(params):
    params["format"] = "json"
    r = SESSION.get(API, params=params, timeout=20)
    return r.json()

# 1. Check what categories Dead Hard belongs to
print("=== Categories that 'Dead Hard' belongs to ===")
data = api_get({"action": "query", "titles": "Dead Hard", "prop": "categories", "cllimit": "50"})
pages = data.get("query", {}).get("pages", {})
for pid, page in pages.items():
    for cat in page.get("categories", []):
        print(f"  {cat['title']}")

# 2. Check what categories Spine Chill (base perk) belongs to
print("\n=== Categories that 'Spine Chill' belongs to ===")
data = api_get({"action": "query", "titles": "Spine Chill", "prop": "categories", "cllimit": "50"})
pages = data.get("query", {}).get("pages", {})
for pid, page in pages.items():
    for cat in page.get("categories", []):
        print(f"  {cat['title']}")

# 3. Search for categories with "perk" in the name
print("\n=== Wiki categories containing 'perk' ===")
data = api_get({"action": "query", "list": "allcategories", "acprefix": "perk", "aclimit": "50"})
for cat in data.get("query", {}).get("allcategories", []):
    print(f"  Category:{cat['*']}  ({cat.get('size',0)} pages)")

print("\n=== Wiki categories containing 'Perk' (capital) ===")
data = api_get({"action": "query", "list": "allcategories", "acprefix": "Perk", "aclimit": "50"})
for cat in data.get("query", {}).get("allcategories", []):
    print(f"  Category:{cat['*']}  ({cat.get('size',0)} pages)")

print("\n=== Wiki categories containing 'Survivor' ===")
data = api_get({"action": "query", "list": "allcategories", "acprefix": "Survivor", "aclimit": "30"})
for cat in data.get("query", {}).get("allcategories", []):
    print(f"  Category:{cat['*']}  ({cat.get('size',0)} pages)")

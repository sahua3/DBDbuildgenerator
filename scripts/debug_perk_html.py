#!/usr/bin/env python3
"""
docker compose run --rm -v $(pwd)/scripts:/scripts backend python /scripts/debug_perk_html.py
"""
import sys, time
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "--quiet"])
    import requests
    from bs4 import BeautifulSoup
import urllib3; urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({"User-Agent": "DBDPerkBot/1.0", "Accept": "application/json"})
API = "https://deadbydaylight.fandom.com/api.php"

def parse_page(title):
    r = SESSION.get(API, params={
        "action": "parse", "page": title,
        "prop": "text", "disablelimitreport": "1", "format": "json"
    }, timeout=20)
    data = r.json()
    if "parse" not in data:
        print(f"  API error: {data.get('error',{}).get('info','unknown')}")
        return None
    return BeautifulSoup(data["parse"]["text"]["*"], "html.parser")

for title in ["Dead_Hard", "Spine_Chill", "Barbecue_&_Chilli"]:
    print(f"\n{'='*60}\nPAGE: {title}\n{'='*60}")
    soup = parse_page(title)
    if not soup:
        continue

    print("\n--- FIRST <p> TEXT ---")
    first_p = soup.find("p")
    if first_p:
        print(repr(first_p.get_text(" ", strip=True)[:300]))

    print("\n--- ALL <p> TAGS (text > 80 chars) ---")
    for i, p in enumerate(soup.find_all("p")):
        t = p.get_text(" ", strip=True)
        if len(t) > 80:
            print(f"  p[{i}]: {repr(t[:200])}")

    print("\n--- ALL <li> TAGS (text > 40 chars) ---")
    for i, li in enumerate(soup.find_all("li")[:15]):
        t = li.get_text(" ", strip=True)
        if len(t) > 40:
            print(f"  li[{i}]: {repr(t[:200])}")

    print("\n--- DIVs with class containing 'flavour'/'quote'/'desc'/'effect' ---")
    for div in soup.find_all(["div","span","p"], class_=True):
        cls = " ".join(div.get("class",[]))
        if any(k in cls.lower() for k in ["flavour","quote","desc","effect","lore","text"]):
            t = div.get_text(" ", strip=True)
            if len(t) > 20:
                print(f"  [{cls}]: {repr(t[:200])}")

    time.sleep(0.5)

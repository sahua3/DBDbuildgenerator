#!/usr/bin/env python3
"""
generate_perks_csv.py

Fetches all survivor perks from the DBD wiki using the MediaWiki API
(action=parse returns rendered HTML — not blocked like direct page requests).

Run inside Docker:
    docker compose run --rm -v $(pwd)/scripts:/scripts backend python /scripts/generate_perks_csv.py
"""

import csv, re, sys, time, json
from pathlib import Path

OUT_PATH = Path(__file__).parent / "perks.csv"

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "beautifulsoup4", "--quiet"])
    import requests
    from bs4 import BeautifulSoup

import urllib3
urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    "User-Agent": "DBDPerkBot/1.0 (https://github.com; educational use)",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
})

API = "https://deadbydaylight.fandom.com/api.php"


def api_get(params: dict, retries=3) -> dict:
    params["format"] = "json"
    for attempt in range(retries):
        try:
            r = SESSION.get(API, params=params, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  API error: {e} (attempt {attempt+1}/{retries})")
            time.sleep(2 ** attempt)
    return {}


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\d+\]", "", text)   # footnotes
    return text.strip()


def normalize_tiers(text: str) -> str:
    """Replace X / Y / Z tier notation with the max (Tier III) value."""
    return re.sub(
        r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(%?)",
        r"\3\4", text
    )


# ── Step 1: get all survivor perk page titles via category API ────────────────

def get_category_members(category: str) -> list[str]:
    titles = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "500",
        "cmnamespace": "0",
    }
    while True:
        data = api_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        titles += [m["title"] for m in members]
        cont = data.get("continue", {}).get("cmcontinue")
        if not cont:
            break
        params["cmcontinue"] = cont
        time.sleep(0.5)
    return titles


# ── Step 2: parse each perk page via action=parse (returns rendered HTML) ─────

def parse_page(title: str) -> "BeautifulSoup | None":
    data = api_get({
        "action": "parse",
        "page": title,
        "prop": "text",
        "disablelimitreport": "1",
    })
    html = data.get("parse", {}).get("text", {}).get("*")
    if not html:
        return None
    return BeautifulSoup(html, "html.parser")


def extract_perk_info(title: str, soup: BeautifulSoup) -> "dict | None":
    """
    Pull name, description, and owner out of a rendered perk page.
    The wiki renders perks with an infobox table that has a Description row
    and a Character row.
    """
    name = title.strip()

    # ── Owner: look for "Character" row in any infobox/table ─────────────────
    owner = ""
    for th in soup.find_all("th"):
        if "character" in th.get_text(strip=True).lower():
            td = th.find_next_sibling("td")
            if td:
                owner_text = clean(td.get_text(" ", strip=True))
                # strip footnotes and parentheticals
                owner_text = re.sub(r"\(.*?\)", "", owner_text).strip()
                if owner_text and len(owner_text) > 1:
                    owner = owner_text
            break

    # Also check "Belongs to" or similar labels
    if not owner:
        for b in soup.find_all(["b", "th", "td"]):
            t = b.get_text(strip=True).lower()
            if t in ("character", "belongs to", "survivor"):
                sib = b.find_next_sibling() or b.parent.find_next_sibling()
                if sib:
                    owner_text = clean(sib.get_text(" ", strip=True))
                    owner_text = re.sub(r"\(.*?\)", "", owner_text).strip()
                    if 2 < len(owner_text) < 60:
                        owner = owner_text
                        break

    # ── Description: find the longest meaningful text block ──────────────────
    desc = ""

    # Priority 1: explicit "Description" row
    for th in soup.find_all("th"):
        if "description" in th.get_text(strip=True).lower():
            td = th.find_next_sibling("td")
            if td:
                text = clean(td.get_text(" ", strip=True))
                text = normalize_tiers(text)
                if len(text) > 40:
                    desc = text
                    break

    # Priority 2: the flavour/mechanical text is usually the longest <td>
    if not desc:
        candidates = []
        for td in soup.find_all("td"):
            text = clean(td.get_text(" ", strip=True))
            text = normalize_tiers(text)
            if (
                len(text) > 60
                and any(kw in text.lower() for kw in [
                    "you ", "your ", "when ", "while ", "after ",
                    "heal", "aura", "generator", "hook", "speed",
                    "injured", "exhausted", "token", "skill check",
                    "status effect", "obsession",
                ])
            ):
                candidates.append(text)
        if candidates:
            desc = max(candidates, key=len)

    # Priority 3: first meaty paragraph
    if not desc:
        for p in soup.find_all("p"):
            text = normalize_tiers(clean(p.get_text(" ", strip=True)))
            if len(text) > 80:
                desc = text
                break

    if not desc or len(desc) < 30:
        return None

    # Final cleanup
    desc = re.sub(r"\b\d{2,3}px\b", "", desc)
    desc = re.sub(r"^\s*\|+\s*", "", desc)
    desc = clean(desc)

    return {"name": name, "description": desc, "owner": owner}


def main():
    print("=" * 60)
    print("DBD Survivor Perk CSV Generator v3 (MediaWiki parse API)")
    print("=" * 60)

    # The wiki has both "Survivor Perks" and "Teachable perks" categories
    # We want all of them
    categories = [
        "Survivor_Perks",
        "Teachable_perks",    # DLC character perks
        "Perks",              # catch-all
    ]

    all_titles: set[str] = set()
    for cat in categories:
        print(f"\nFetching Category:{cat} ...")
        titles = get_category_members(cat)
        print(f"  → {len(titles)} pages")
        all_titles.update(titles)

    # Filter out obvious non-perk pages
    perk_titles = [
        t for t in sorted(all_titles)
        if not any(skip in t for skip in [
            "Killer", "DLC", "Chapter", "Archives", "Tome",
            "Template", "Category", "File", "Talk", "User",
        ])
    ]

    print(f"\nTotal unique candidate perk pages: {len(perk_titles)}")
    print("Fetching and parsing each page (this takes ~3-4 minutes)...\n")

    perks = []
    failed = []

    for i, title in enumerate(perk_titles, 1):
        print(f"  [{i:>3}/{len(perk_titles)}] {title}", end=" ... ", flush=True)
        soup = parse_page(title)
        if not soup:
            print("FETCH FAIL")
            failed.append(title)
            continue

        info = extract_perk_info(title, soup)
        if info:
            perks.append(info)
            print(f"✓  owner: {info['owner'] or '(base)'}")
        else:
            print("✗  no description found")
            failed.append(title)

        # Polite rate limiting
        time.sleep(0.25)

    # Deduplicate by name
    seen: set[str] = set()
    deduped = []
    for p in perks:
        key = p["name"].lower()
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    perks = deduped

    # Sort: base perks first, then alphabetical by owner
    perks.sort(key=lambda p: (0 if not p["owner"] else 1, p.get("owner", ""), p["name"]))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "description", "owner"])
        writer.writeheader()
        writer.writerows(perks)

    print(f"\n{'=' * 60}")
    print(f"✓ Wrote {len(perks)} perks to {OUT_PATH}")
    print(f"  Base perks:       {sum(1 for p in perks if not p['owner'])}")
    print(f"  Character perks:  {sum(1 for p in perks if p['owner'])}")
    print(f"  Unique survivors: {len({p['owner'] for p in perks if p['owner']})}")
    if failed:
        print(f"  Failed pages:     {len(failed)} (check manually)")
    print("=" * 60)
    print("\nNext: docker compose run --rm backend python -m app.workers.perk_loader")


if __name__ == "__main__":
    main()

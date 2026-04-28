#!/usr/bin/env python3
"""
generate_perks_csv.py  v4

Fetches all survivor perks from the DBD wiki using the MediaWiki parse API.

Run inside Docker:
    docker compose run --rm -v $(pwd)/scripts:/scripts backend python /scripts/generate_perks_csv.py
"""

import csv, re, sys, time
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
SESSION.headers.update({"User-Agent": "DBDPerkBot/1.0", "Accept": "application/json"})
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
        time.sleep(0.3)
    return titles


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


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\[\d+\]", "", text)
    return text.strip()


def normalize_tiers(text: str) -> str:
    """X / Y / Z  →  Z (keep Tier III value only)."""
    return re.sub(
        r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*(%?)",
        r"\3\4", text
    )


def extract_perk(title: str, soup: BeautifulSoup) -> "dict | None":
    """
    Parse a rendered perk page.

    Page structure (confirmed from debug output):
      p[0]  = "PERK NAME is a TYPE Perk belonging to OWNER . Prestige..."
           OR "PERK NAME is a TYPE Perk available to all Survivors ."
           OR "PERK NAME is a TYPE Perk available to all Killers ."   ← skip
      p[1]  = main description paragraph
      li[0] = first bullet point of the description
      p[2]  = secondary description line (e.g. "causes Exhausted for X seconds")
    """
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return None

    first_p_text = clean(paragraphs[0].get_text(" ", strip=True))

    # ── Filter out killer perks ───────────────────────────────────────────────
    # "available to all Killers" or "belonging to The <Killer>"
    if "available to all Killers" in first_p_text:
        return None
    # Killer unique perks say "belonging to The X" — killer names start with "The "
    belonging_match = re.search(r"belonging to ([\w\s']+?)(?:\s*\.|\s*Prestige)", first_p_text)
    if belonging_match:
        candidate = belonging_match.group(1).strip()
        if candidate.startswith("The "):
            return None  # killer perk

    # ── Extract owner ─────────────────────────────────────────────────────────
    owner = ""
    # "belonging to David King" → owner = "David King"
    if "belonging to" in first_p_text:
        # Use the <a> tag right after "belonging to" for clean name
        p0 = paragraphs[0]
        full_text = p0.get_text(" ", strip=True)
        idx = full_text.find("belonging to")
        if idx != -1:
            after = full_text[idx + len("belonging to"):].strip()
            # Name ends at " ." or " Prestige"
            name_match = re.match(r"([\w\s'\-\.]+?)(?:\s*\.\s|\s*Prestige)", after)
            if name_match:
                owner = name_match.group(1).strip()
        # Fallback: grab the <a> link that points to a survivor wiki page
        if not owner:
            for a in p0.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if (
                    "/wiki/" in href
                    and "Perk" not in text
                    and "Prestige" not in text
                    and len(text) > 2
                    and not text.startswith("The ")
                ):
                    owner = text
                    break

    # ── Extract description ───────────────────────────────────────────────────
    # Description is in p[1], followed by li[0], then p[2]
    # We skip p[0] (intro) and anything that looks like patch notes / trivia

    desc_parts = []

    # Find the first substantial paragraph after p[0]
    for p in paragraphs[1:]:
        text = clean(p.get_text(" ", strip=True))
        # Stop at patch notes / trivia / developer comments sections
        if any(skip in text.lower() for skip in [
            "patch ", "update ", "version ", "trivia", "developer note",
            "change log", "previously", "used to ", "was changed",
        ]):
            break
        if len(text) > 40:
            desc_parts.append(normalize_tiers(text))
        if len(desc_parts) >= 2:
            break

    # Add bullet point details (li tags before the change log)
    toc_found = False
    for li in soup.find_all("li"):
        text = clean(li.get_text(" ", strip=True))
        # The ToC li items contain "Change Log" etc. — stop there
        if any(skip in text for skip in ["Change Log", "Patch ", "Trivia"]):
            toc_found = True
            break
        if len(text) > 30 and not toc_found:
            desc_parts.append("• " + normalize_tiers(text))
        if len(desc_parts) >= 5:
            break

    if not desc_parts:
        return None

    desc = " ".join(desc_parts)
    desc = clean(desc)

    if len(desc) < 30:
        return None

    return {"name": title, "description": desc, "owner": owner}


def main():
    print("=" * 60)
    print("DBD Survivor Perk CSV Generator v4")
    print("=" * 60)

    # Fetch all perk titles from multiple categories
    all_titles: set[str] = set()
    for cat in ["Survivor_Perks", "Unique_Survivor_Perks"]:
        print(f"\nFetching Category:{cat} ...")
        titles = get_category_members(cat)
        print(f"  → {len(titles)} pages")
        all_titles.update(titles)

    # Filter obvious non-perk pages
    skip_words = [
        "Chapter", "Archives", "Tome", "Template",
        "Category", "File:", "Talk:", "User:", "DLC",
    ]
    perk_titles = sorted([
        t for t in all_titles
        if not any(s in t for s in skip_words)
    ])

    print(f"\nCandidate pages: {len(perk_titles)}")
    print("Parsing pages... (~3 min)\n")

    perks = []
    skipped_killer = 0
    failed = []

    for i, title in enumerate(perk_titles, 1):
        print(f"  [{i:>3}/{len(perk_titles)}] {title:<40}", end=" ", flush=True)
        soup = parse_page(title)
        if not soup:
            print("FAIL")
            failed.append(title)
            time.sleep(0.5)
            continue

        info = extract_perk(title, soup)
        if info is None:
            # Check if it was a killer perk or just unparseable
            p0 = soup.find("p")
            p0_text = p0.get_text(" ", strip=True) if p0 else ""
            if "Killer" in p0_text or (p0 and "The " in p0_text):
                print("killer — skipped")
                skipped_killer += 1
            else:
                print("no desc — skipped")
                failed.append(title)
        else:
            print(f"✓  owner={info['owner'] or '(base)'}")
            perks.append(info)

        time.sleep(0.22)

    # Deduplicate by name
    seen: set[str] = set()
    deduped = []
    for p in perks:
        if p["name"].lower() not in seen:
            seen.add(p["name"].lower())
            deduped.append(p)
    perks = deduped

    # Sort: base perks first, then by owner name
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
    print(f"  Killer perks skipped: {skipped_killer}")
    if failed:
        print(f"  Failed/skipped:   {len(failed)}")
        for f in failed[:10]:
            print(f"    - {f}")
    print("=" * 60)
    print("\nNext: docker compose run --rm backend python -m app.workers.perk_loader")


if __name__ == "__main__":
    main()

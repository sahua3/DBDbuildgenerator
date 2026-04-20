"""
Perk categorization engine.

Uses keyword/phrase matching on perk descriptions to assign categories.
When the AI API key is configured, uses Claude for smarter classification.
Falls back to rule-based matching otherwise.
"""
import re
from typing import Optional
from app.core.config import PERK_CATEGORIES

# ─── Rule-based keyword maps ────────────────────────────────────────────────
# Each category has a list of (pattern, weight) tuples.
# A perk is assigned to a category if any of its patterns match the description.

CATEGORY_RULES: dict[str, list[str]] = {
    "healing": [
        r"\bheal(ing|ed|s)?\b",
        r"\bhealth state\b",
        r"\brecovery\b",
        r"\bmedkit\b",
        r"\bbandage\b",
        r"\binjured\b",
        r"\bdying state\b",
        r"\bbleed(ing)?\b",
    ],
    "stealth": [
        r"\bscreaming?\b",
        r"\bundetectable\b",
        r"\bscratch marks?\b",
        r"\bblood pools?\b",
        r"\bnoise\b",
        r"\bimperceptible\b",
        r"\bsuppressed\b",
        r"\bcrouch(ing)?\b",
        r"\bslow vault\b",
    ],
    "chase": [
        r"\bchase\b",
        r"\bpursued?\b",
        r"\bkiller.{0,20}(within|near|close)\b",
        r"\bvault(ing)?\b",
        r"\bpallet\b",
        r"\bwindow\b",
        r"\bblocker?\b",
        r"\bdodge\b",
        r"\bstun(ned|s)?\b",
    ],
    "gen_speed": [
        r"\bgenerator\b",
        r"\brepair(ing|ed|s)?\b",
        r"\bgen(s)?\b",
        r"\bsabotage\b",
        r"\bskill check\b",
        r"\bgreat skill\b",
    ],
    "information": [
        r"\baura\b",
        r"\bsee(s|ing)?\b.{0,30}\baura\b",
        r"\bnotif(ied|ication)\b",
        r"\bdetect(ed|ion)?\b",
        r"\brevealed?\b",
        r"\btracked?\b",
        r"\bsenses?\b",
        r"\bbonfire\b",
        r"\binstinct\b",
    ],
    "altruism": [
        r"\bunhook(ing|ed|s)?\b",
        r"\brescue\b",
        r"\btake a hit\b",
        r"\bprotect(ive)?\b",
        r"\bteammate\b",
        r"\bally\b",
        r"\bother survivor\b",
        r"\bsurvivor you rescue\b",
    ],
    "escape": [
        r"\bescape(d|s)?\b",
        r"\bexit gate\b",
        r"\bhatch\b",
        r"\bopen the gate\b",
        r"\bend game\b",
    ],
    "anti_hook": [
        r"\bhook(ed|s|ing)?\b",
        r"\bsacrifice\b",
        r"\bstruggle\b",
        r"\bobsession\b",
        r"\bhook stat(e|us)\b",
        r"\bunhook yourself\b",
        r"\bself.unhook\b",
    ],
    "aura_reading": [
        r"\baura\b",
        r"\bsee the killer\b",
        r"\bkiller.{0,10}aura\b",
        r"\bchest(s)?.{0,20}aura\b",
        r"\btotem.{0,20}aura\b",
        r"\bgen(erator)?.{0,20}aura\b",
    ],
    "exhaustion": [
        r"\bexhausted?\b",
        r"\bexhaustion\b",
        r"\bsprint burst\b",
        r"\bdead hard\b",
        r"\blithe\b",
        r"\bing?vigorating\b",
        r"\bboost of speed\b",
        r"\bspeed boost\b",
    ],
    "endurance": [
        r"\bendurance\b",
        r"\bprotected hit\b",
        r"\bnext hit\b",
        r"\bguaranteed\b",
        r"\babs(orb|orbs)\b",
        r"\bshield\b",
        r"\bnot be downed\b",
    ],
    "second_chance": [
        r"\bscream\b",
        r"\binstant\b.{0,20}\bheal\b",
        r"\banti.body\b",
        r"\boff the record\b",
        r"\bno mither\b",
        r"\bup the ante\b",
        r"\bdeliverance\b",
        r"\bbackstab\b",
        r"\bnear death\b",
        r"\bborrowed time\b",
    ],
}


def classify_perk_description(description: str) -> list[str]:
    """
    Rule-based perk classification.
    Returns list of matched category names (can be multiple).
    """
    desc_lower = description.lower()
    matched: list[str] = []

    for category, patterns in CATEGORY_RULES.items():
        for pattern in patterns:
            if re.search(pattern, desc_lower):
                matched.append(category)
                break  # one match per category is enough

    # Default to "second_chance" if nothing matched and description is short
    if not matched:
        matched = ["second_chance"]

    return matched


async def classify_perk_with_ai(
    name: str,
    description: str,
    categories: list[str],
    api_key: Optional[str] = None,
) -> list[str]:
    """
    Use Claude API to classify a perk if an API key is available.
    Falls back to rule-based if not.
    """
    if not api_key:
        return classify_perk_description(description)

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)

    prompt = f"""You are a Dead by Daylight expert. Classify this survivor perk into one or more of these categories:
{', '.join(categories)}

Perk name: {name}
Perk description: {description}

Rules:
- Return ONLY a JSON array of category names from the list above
- A perk can belong to multiple categories (max 3)
- Choose the most relevant categories
- Example: ["healing", "altruism"]

Respond with only the JSON array, nothing else."""

    msg = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    try:
        text = msg.content[0].text.strip()
        result = json.loads(text)
        # Validate all returned categories are in our list
        return [c for c in result if c in categories]
    except Exception:
        return classify_perk_description(description)


async def bulk_classify_perks(
    perks: list[dict],
    use_ai: bool = False,
    api_key: Optional[str] = None,
) -> dict[str, list[str]]:
    """
    Classify a list of perks. Returns {perk_name: [categories]}.
    """
    results = {}
    for perk in perks:
        if use_ai and api_key:
            cats = await classify_perk_with_ai(
                perk["name"], perk["description"], PERK_CATEGORIES, api_key
            )
        else:
            cats = classify_perk_description(perk["description"])
        results[perk["name"]] = cats
    return results

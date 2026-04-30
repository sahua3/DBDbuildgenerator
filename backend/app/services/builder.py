"""
Build generation service.

Two modes:
1. Theme-based: parse a theme string, map to categories, use graph to find synergistic perks
2. Category-based: user specifies how many perks per category, fill slots using weights
"""
import random
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.perk import Perk
from app.services.graph import get_graph, score_build_compatibility
from app.core.config import PERK_CATEGORIES

logger = logging.getLogger(__name__)

# ── Theme → category keyword mapping ─────────────────────────────────────────
THEME_CATEGORY_MAP: dict[str, list[str]] = {
    # Speed / efficiency themes
    "gen rush": ["gen_speed", "information", "aura_reading"],
    "generator": ["gen_speed", "information", "aura_reading"],
    "efficiency": ["gen_speed", "altruism", "healing"],
    "speed": ["gen_speed", "exhaustion", "chase"],

    # Healing / support themes
    "medic": ["healing", "altruism", "second_chance"],
    "support": ["healing", "altruism", "anti_hook"],
    "heal": ["healing", "altruism", "second_chance"],
    "team": ["altruism", "healing", "anti_hook"],

    # Stealth themes
    "stealth": ["stealth", "information", "escape"],
    "ghost": ["stealth", "escape", "second_chance"],
    "hide": ["stealth", "anti_hook", "information"],
    "sneaky": ["stealth", "chase", "escape"],

    # Chase / survivor themes
    "chase": ["chase", "exhaustion", "endurance"],
    "looping": ["chase", "exhaustion", "endurance"],
    "loops": ["chase", "exhaustion", "endurance"],
    "juking": ["chase", "exhaustion", "stealth"],

    # Escape themes
    "escape": ["escape", "exhaustion", "endurance"],
    "hatch": ["escape", "information", "stealth"],
    "end game": ["escape", "endurance", "second_chance"],

    # Aggressive / clutch themes
    "clutch": ["second_chance", "endurance", "anti_hook"],
    "risky": ["second_chance", "endurance", "chase"],
    "aggressive": ["chase", "endurance", "anti_hook"],

    # Information themes
    "information": ["information", "aura_reading", "gen_speed"],
    "aura": ["aura_reading", "information", "stealth"],
    "spy": ["aura_reading", "information", "stealth"],
}

# Fallback: map to balanced build
DEFAULT_THEME_CATEGORIES = ["gen_speed", "healing", "chase", "second_chance"]


def parse_theme_to_categories(theme: str) -> list[str]:
    """
    Convert a freeform theme string into a prioritized list of categories.
    """
    theme_lower = theme.lower()

    # Try to find keyword matches
    matched_categories: list[str] = []
    for keyword, cats in THEME_CATEGORY_MAP.items():
        if keyword in theme_lower:
            matched_categories.extend(cats)

    if not matched_categories:
        return DEFAULT_THEME_CATEGORIES

    # Deduplicate while preserving order and take top 4
    seen = set()
    result = []
    for cat in matched_categories:
        if cat not in seen and cat in PERK_CATEGORIES:
            seen.add(cat)
            result.append(cat)
        if len(result) == 4:
            break

    # Pad to 4 with defaults if needed
    for cat in DEFAULT_THEME_CATEGORIES:
        if len(result) >= 4:
            break
        if cat not in result:
            result.append(cat)

    return result[:4]


async def get_perks_by_category(
    db: AsyncSession,
    category: str,
    owned_survivor_names: Optional[list[str]] = None,
    exclude_ids: Optional[set] = None,
) -> list[Perk]:
    """
    Fetch all perks in a category, optionally filtered by owned survivors.
    """
    stmt = select(Perk).where(Perk.categories.any(category))

    if owned_survivor_names is not None:
        # Include base perks (owner=None) + perks owned by the survivors the user has
        stmt = stmt.where(
            (Perk.owner == None) | (Perk.owner.in_(owned_survivor_names))  # noqa
        )

    perks = (await db.execute(stmt)).scalars().all()

    if exclude_ids:
        perks = [p for p in perks if str(p.id) not in exclude_ids]

    return list(perks)


def weighted_sample(perks: list[Perk], n: int = 1, boost_shrine: bool = True) -> list[Perk]:
    """
    Sample n perks from list, weighted by category_weight + shrine boost.
    """
    if not perks:
        return []
    n = min(n, len(perks))

    weights = []
    for p in perks:
        w = max(p.category_weight, 0.01)
        if boost_shrine and p.in_shrine:
            w *= 1.3  # slight shrine boost
        weights.append(w)

    total = sum(weights)
    probs = [w / total for w in weights]

    chosen_indices = []
    remaining_perks = list(range(len(perks)))
    remaining_probs = list(probs)

    for _ in range(n):
        if not remaining_perks:
            break
        total_p = sum(remaining_probs)
        normalized = [p / total_p for p in remaining_probs]
        idx = random.choices(remaining_perks, weights=normalized, k=1)[0]
        position = remaining_perks.index(idx)
        chosen_indices.append(idx)
        remaining_perks.pop(position)
        remaining_probs.pop(position)

    return [perks[i] for i in chosen_indices]


async def generate_theme_build(
    db: AsyncSession,
    theme: str,
    owned_only: bool = False,
    owned_survivors: Optional[list[str]] = None,
) -> list[Perk]:
    """
    Generate a 4-perk build based on a theme string.
    Uses the co-occurrence graph to prefer perks that work well together.
    """
    categories = parse_theme_to_categories(theme)
    graph = get_graph()

    owned_filter = owned_survivors if owned_only else None
    selected_perks: list[Perk] = []
    selected_ids: set[str] = set()

    # One perk per category slot
    for cat in categories:
        if len(selected_perks) >= 4:
            break

        candidates = await get_perks_by_category(db, cat, owned_filter, selected_ids)
        if not candidates:
            continue

        if graph and selected_perks:
            # Score each candidate by its graph affinity + user feedback affinity
            from app.services.feedback import get_affinity_blend_weight, get_perk_affinity
            affinity_blend = await get_affinity_blend_weight(db)
            scored = []
            for p in candidates:
                graph_affinity = 0.0
                user_affinity = 0.0
                for already in selected_perks:
                    pid, aid = str(p.id), str(already.id)
                    if graph.has_edge(pid, aid):
                        graph_affinity += graph[pid][aid]["weight"]
                    if affinity_blend > 0:
                        user_affinity += await get_perk_affinity(db, pid, aid)
                # Blend: nightlight graph + user behavior + category weight
                nl_weight = 1.0 - affinity_blend
                score = (graph_affinity * nl_weight + user_affinity * affinity_blend) * 0.7 + p.category_weight * 0.3
                scored.append((p, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            # Pick from top-5 with some randomness
            top5 = [p for p, _ in scored[:5]]
            pick = weighted_sample(top5, 1)[0] if top5 else candidates[0]
        else:
            pick_list = weighted_sample(candidates, 1)
            pick = pick_list[0] if pick_list else candidates[0]

        selected_perks.append(pick)
        selected_ids.add(str(pick.id))

    return selected_perks


async def generate_category_build(
    db: AsyncSession,
    category_selections: dict[str, int],
    owned_only: bool = False,
    owned_survivors: Optional[list[str]] = None,
) -> list[Perk]:
    """
    Generate a build with a specified number of perks from each category.
    category_selections: {"healing": 2, "chase": 1, "gen_speed": 1}
    """
    owned_filter = owned_survivors if owned_only else None
    selected_perks: list[Perk] = []
    selected_ids: set[str] = set()
    graph = get_graph()

    for category, count in category_selections.items():
        if count <= 0:
            continue

        candidates = await get_perks_by_category(db, category, owned_filter, selected_ids)
        if not candidates:
            logger.warning(f"No candidates found for category: {category}")
            continue

        if graph and selected_perks:
            from app.services.feedback import get_affinity_blend_weight, get_perk_affinity
            affinity_blend = await get_affinity_blend_weight(db)
            nl_weight = 1.0 - affinity_blend
            scored = []
            for p in candidates:
                graph_affinity = sum(
                    graph[str(p.id)][str(a.id)]["weight"]
                    for a in selected_perks
                    if graph.has_edge(str(p.id), str(a.id))
                )
                user_affinity = 0.0
                if affinity_blend > 0:
                    for a in selected_perks:
                        user_affinity += await get_perk_affinity(db, str(p.id), str(a.id))
                score = (graph_affinity * nl_weight + user_affinity * affinity_blend) * 0.7 + p.category_weight * 0.3
                scored.append((p, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_pool = [p for p, _ in scored[:max(count * 3, 5)]]
            picks = weighted_sample(top_pool, count)
        else:
            picks = weighted_sample(candidates, count)

        for pick in picks:
            selected_perks.append(pick)
            selected_ids.add(str(pick.id))

    return selected_perks[:4]

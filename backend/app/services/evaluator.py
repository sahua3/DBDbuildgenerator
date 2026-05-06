"""
Build evaluation service.

Scores builds on two metrics:
  1. pick_rate_score  - avg normalized Nightlight pick rate across 4 perks
  2. synergy_score    - avg pairwise graph edge weight across all 6 pairs
  3. combined_score   - 0.6 * synergy + 0.4 * pick_rate

Compares four strategies vs random baseline and reports % improvement.
"""
import itertools
import logging
import random
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.perk import Perk
from app.models.edge import PerkEdge

logger = logging.getLogger(__name__)


async def _load_perk_data(db: AsyncSession) -> dict[str, dict]:
    perks = (await db.execute(select(Perk))).scalars().all()
    return {
        str(p.id): {
            "name": p.name,
            "pick_rate": float(p.pick_rate or 0),
            "category_weight": float(p.category_weight or 0),
            "categories": p.categories or [],
        }
        for p in perks
    }


async def _load_edge_map(db: AsyncSession) -> dict[tuple[str, str], float]:
    edges = (await db.execute(select(PerkEdge))).scalars().all()
    edge_map: dict[tuple[str, str], float] = {}
    for e in edges:
        a, b = str(e.perk_a_id), str(e.perk_b_id)
        if a > b:
            a, b = b, a
        edge_map[(a, b)] = float(e.weight or 0)
    return edge_map


def _edge_weight(a: str, b: str, edge_map: dict) -> float:
    key = (a, b) if a < b else (b, a)
    return edge_map.get(key, 0.0)


def score_build(perk_ids: list[str], perk_data: dict, edge_map: dict) -> dict:
    if len(perk_ids) < 2:
        return {"pick_rate_score": 0.0, "synergy_score": 0.0, "combined_score": 0.0}

    pick_rates = [perk_data.get(pid, {}).get("pick_rate", 0.0) for pid in perk_ids]
    pick_rate_score = sum(pick_rates) / len(pick_rates)

    pairs = list(itertools.combinations(perk_ids, 2))
    synergy_score = (
        sum(_edge_weight(a, b, edge_map) for a, b in pairs) / len(pairs)
        if pairs else 0.0
    )

    combined = 0.6 * synergy_score + 0.4 * pick_rate_score
    return {
        "pick_rate_score": round(pick_rate_score, 4),
        "synergy_score": round(synergy_score, 4),
        "combined_score": round(combined, 4),
    }


def _avg(builds: list[dict], key: str) -> float:
    return round(sum(b[key] for b in builds) / len(builds), 4) if builds else 0.0


def _summarize(builds: list[dict]) -> dict:
    return {
        "pick_rate_score": _avg(builds, "pick_rate_score"),
        "synergy_score": _avg(builds, "synergy_score"),
        "combined_score": _avg(builds, "combined_score"),
        "n": len(builds),
    }


def _pct(new: float, base: float) -> float:
    if base == 0:
        return 0.0
    return round((new - base) / base * 100, 1)


async def run_evaluation(db: AsyncSession, n_builds: int = 100) -> dict:
    perk_data = await _load_perk_data(db)
    edge_map = await _load_edge_map(db)
    all_ids = list(perk_data.keys())

    if len(all_ids) < 4:
        return {"error": "Not enough perks in database to evaluate."}

    has_edges = len(edge_map) > 0
    has_pick_rates = any(v["pick_rate"] > 0 for v in perk_data.values())
    logger.info(f"Eval: {len(all_ids)} perks, {len(edge_map)} edges, pick_rates={has_pick_rates}")

    # 1. Random baseline
    random_builds = [
        score_build(random.sample(all_ids, 4), perk_data, edge_map)
        for _ in range(n_builds)
    ]
    random_avg = _summarize(random_builds)

    # 2. Weighted rules (pick_rate only, no graph)
    weights = [max(perk_data[pid]["pick_rate"], 0.01) for pid in all_ids]
    weighted_builds = []
    for _ in range(n_builds):
        chosen: list[str] = []
        pool = list(zip(all_ids, weights))
        for _ in range(4):
            if not pool:
                break
            ids_only, w_only = zip(*pool)
            idx = random.choices(range(len(ids_only)), weights=list(w_only), k=1)[0]
            chosen.append(ids_only[idx])
            pool.pop(idx)
        if len(chosen) == 4:
            weighted_builds.append(score_build(chosen, perk_data, edge_map))
    weighted_avg = _summarize(weighted_builds)

    # 3. Graph-enhanced (greedy neighbor expansion)
    graph_builds = []
    top20 = sorted(all_ids, key=lambda p: perk_data[p]["pick_rate"], reverse=True)[:20]
    for _ in range(n_builds):
        seed = random.choice(top20) if top20 else random.choice(all_ids)
        chosen = [seed]
        remaining = [p for p in all_ids if p != seed]
        for _ in range(3):
            if not remaining:
                break
            sample = random.sample(remaining, min(40, len(remaining)))
            best = max(
                sample,
                key=lambda c: (
                    sum(_edge_weight(c, x, edge_map) for x in chosen) * 0.7
                    + perk_data[c]["pick_rate"] * 0.3
                ),
            )
            chosen.append(best)
            remaining.remove(best)
        if len(chosen) == 4:
            graph_builds.append(score_build(chosen, perk_data, edge_map))
    graph_avg = _summarize(graph_builds)

    # 4. User-saved builds
    from app.models.feedback import BuildEvent
    saved_events = (await db.execute(
        select(BuildEvent).where(BuildEvent.event_type == "saved").limit(200)
    )).scalars().all()
    user_builds = [
        score_build([ev.perk_a, ev.perk_b, ev.perk_c, ev.perk_d], perk_data, edge_map)
        for ev in saved_events
        if all(pid in perk_data for pid in [ev.perk_a, ev.perk_b, ev.perk_c, ev.perk_d])
    ]
    user_avg = _summarize(user_builds)

    base = random_avg["combined_score"]

    return {
        "strategies": {
            "random_baseline": {**random_avg, "label": "Random Baseline"},
            "weighted_rules": {**weighted_avg, "label": "Weighted Rules",
                               "improvement_vs_random": _pct(weighted_avg["combined_score"], base)},
            "graph_enhanced": {**graph_avg, "label": "Graph-Enhanced",
                               "improvement_vs_random": _pct(graph_avg["combined_score"], base)},
            "user_feedback": {**user_avg, "label": "User-Saved Builds",
                              "improvement_vs_random": _pct(user_avg["combined_score"], base),
                              "sample_size": len(user_builds)},
        },
        "data_quality": {
            "has_nightlight_pick_rates": has_pick_rates,
            "has_graph_edges": has_edges,
            "edge_count": len(edge_map),
            "perk_count": len(all_ids),
            "note": "Run a Nightlight sync to populate pick rates and edges." if not has_edges else None,
        },
        "metrics_explained": {
            "pick_rate_score": "Average Nightlight pick rate (0-1). Higher = more meta.",
            "synergy_score": "Average pairwise graph edge weight (0-1). Higher = perks commonly used together.",
            "combined_score": "0.6 x synergy + 0.4 x pick rate. Overall build quality estimate.",
        },
        "total_perks_in_db": len(all_ids),
        "total_saved_builds": len(saved_events),
    }
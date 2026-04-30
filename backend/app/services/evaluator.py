"""
Build evaluation service.

Defines metrics to score build quality and compares:
  - Random baseline
  - Rule-based (category weights only)
  - Graph-enhanced (co-occurrence)
  - Affinity-enhanced (user feedback)

Metrics:
  1. weighted_pick_rate_score  — avg Nightlight pick rate of perks in build
                                 proxy for "is this meta?"
  2. synergy_score             — avg edge weight between all 6 perk pairs
                                 proxy for "do these perks work together?"
  3. combined_score            — 0.6 * synergy + 0.4 * pick_rate
                                 overall build quality estimate

These scores let you say: "Affinity-enhanced builds score X% higher on
combined_score than random baseline" — a concrete resume metric.
"""
import itertools
import logging
import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.perk import Perk
from app.models.edge import PerkEdge
from app.services.graph import get_graph

logger = logging.getLogger(__name__)


# ── Per-build scoring ─────────────────────────────────────────────────────────

def score_build(perk_ids: list[str], perk_data: dict[str, dict]) -> dict:
    """
    Score a 4-perk build.

    perk_data: {perk_id: {"pick_rate": float, "category_weight": float}}
    Returns dict with individual metrics and combined score.
    """
    if len(perk_ids) < 2:
        return {"pick_rate_score": 0.0, "synergy_score": 0.0, "combined_score": 0.0}

    graph = get_graph()

    # Metric 1: average normalized pick rate
    pick_rates = [perk_data.get(pid, {}).get("pick_rate", 0.0) for pid in perk_ids]
    pick_rate_score = sum(pick_rates) / len(pick_rates)

    # Metric 2: average pairwise synergy (graph edge weight)
    synergy_total = 0.0
    pair_count = 0
    for a, b in itertools.combinations(perk_ids, 2):
        if graph and graph.has_edge(a, b):
            synergy_total += graph[a][b]["weight"]
        pair_count += 1
    synergy_score = synergy_total / pair_count if pair_count > 0 else 0.0

    # Combined score
    combined = 0.6 * synergy_score + 0.4 * pick_rate_score

    return {
        "pick_rate_score": round(pick_rate_score, 4),
        "synergy_score": round(synergy_score, 4),
        "combined_score": round(combined, 4),
        "perk_count": len(perk_ids),
    }


# ── Baseline generators ───────────────────────────────────────────────────────

async def _get_all_perk_data(db: AsyncSession) -> dict[str, dict]:
    """Fetch all perks as a flat dict for scoring."""
    perks = (await db.execute(select(Perk))).scalars().all()
    return {
        str(p.id): {
            "name": p.name,
            "pick_rate": p.pick_rate,
            "category_weight": p.category_weight,
            "categories": p.categories or [],
        }
        for p in perks
    }


async def generate_random_baseline(
    db: AsyncSession,
    n_builds: int = 100,
) -> list[dict]:
    """Generate n random 4-perk builds and score them."""
    perk_data = await _get_all_perk_data(db)
    all_ids = list(perk_data.keys())

    if len(all_ids) < 4:
        return []

    builds = []
    for _ in range(n_builds):
        pids = random.sample(all_ids, 4)
        score = score_build(pids, perk_data)
        builds.append({"perk_ids": pids, **score})
    return builds


async def generate_weighted_baseline(
    db: AsyncSession,
    n_builds: int = 100,
) -> list[dict]:
    """
    Generate builds using only category_weight (rule-based, no graph).
    Simulates the pre-graph system.
    """
    perk_data = await _get_all_perk_data(db)
    all_ids = list(perk_data.keys())
    weights = [max(perk_data[pid]["category_weight"], 0.01) for pid in all_ids]

    builds = []
    for _ in range(n_builds):
        # Weighted sample without replacement
        chosen = []
        remaining_ids = list(all_ids)
        remaining_w = list(weights)
        for _ in range(4):
            if not remaining_ids:
                break
            total = sum(remaining_w)
            probs = [w / total for w in remaining_w]
            idx = random.choices(range(len(remaining_ids)), weights=probs, k=1)[0]
            chosen.append(remaining_ids.pop(idx))
            remaining_w.pop(idx)

        if len(chosen) == 4:
            score = score_build(chosen, perk_data)
            builds.append({"perk_ids": chosen, **score})
    return builds


# ── Full evaluation report ────────────────────────────────────────────────────

def _avg_scores(builds: list[dict]) -> dict:
    if not builds:
        return {"pick_rate_score": 0, "synergy_score": 0, "combined_score": 0, "n": 0}
    return {
        "pick_rate_score": round(sum(b["pick_rate_score"] for b in builds) / len(builds), 4),
        "synergy_score": round(sum(b["synergy_score"] for b in builds) / len(builds), 4),
        "combined_score": round(sum(b["combined_score"] for b in builds) / len(builds), 4),
        "n": len(builds),
    }


async def run_evaluation(db: AsyncSession, n_builds: int = 200) -> dict:
    """
    Run a full comparative evaluation across all recommendation strategies.
    Returns a report suitable for the frontend dashboard.
    """
    from app.services.builder import generate_theme_build, generate_category_build
    from app.models.feedback import BuildEvent
    import math

    perk_data = await _get_all_perk_data(db)

    logger.info(f"Running evaluation with {n_builds} builds per strategy...")

    # 1. Random baseline
    random_builds = await generate_random_baseline(db, n_builds)
    random_avg = _avg_scores(random_builds)

    # 2. Weighted (rule-based) baseline
    weighted_builds = await generate_weighted_baseline(db, n_builds)
    weighted_avg = _avg_scores(weighted_builds)

    # 3. Graph-enhanced (current system): generate theme builds with graph
    themes = ["gen rush", "stealth", "healing", "chase", "escape", "clutch",
              "information", "support", "aggressive", "end game"]
    graph_builds = []
    for i in range(min(n_builds, 100)):
        theme = themes[i % len(themes)]
        perks = await generate_theme_build(db, theme)
        if len(perks) == 4:
            pids = [str(p.id) for p in perks]
            score = score_build(pids, perk_data)
            graph_builds.append({"perk_ids": pids, "theme": theme, **score})
    graph_avg = _avg_scores(graph_builds)

    # 4. Feedback from saved builds (if any)
    saved_events = (await db.execute(
        select(BuildEvent).where(BuildEvent.event_type == "saved").limit(200)
    )).scalars().all()

    saved_builds_scored = []
    for ev in saved_events:
        pids = [ev.perk_a, ev.perk_b, ev.perk_c, ev.perk_d]
        if all(pid in perk_data for pid in pids):
            score = score_build(pids, perk_data)
            saved_builds_scored.append({"perk_ids": pids, **score})
    user_avg = _avg_scores(saved_builds_scored)

    # Compute % improvements vs random baseline
    def pct_improvement(new_score: float, base_score: float) -> float:
        if base_score == 0:
            return 0.0
        return round((new_score - base_score) / base_score * 100, 1)

    base = random_avg["combined_score"]

    report = {
        "strategies": {
            "random_baseline": {**random_avg, "label": "Random Baseline"},
            "weighted_rules": {
                **weighted_avg,
                "label": "Weighted Rules",
                "improvement_vs_random": pct_improvement(weighted_avg["combined_score"], base),
            },
            "graph_enhanced": {
                **graph_avg,
                "label": "Graph-Enhanced",
                "improvement_vs_random": pct_improvement(graph_avg["combined_score"], base),
            },
            "user_feedback": {
                **user_avg,
                "label": "User-Saved Builds",
                "improvement_vs_random": pct_improvement(user_avg["combined_score"], base),
                "sample_size": len(saved_builds_scored),
            },
        },
        "metrics_explained": {
            "pick_rate_score": "Average Nightlight pick rate of perks (0-1). Higher = more meta.",
            "synergy_score": "Average pairwise graph edge weight (0-1). Higher = perks commonly used together.",
            "combined_score": "0.6 × synergy + 0.4 × pick_rate. Overall build quality estimate.",
        },
        "total_perks_in_db": len(perk_data),
        "total_saved_builds": len(saved_events),
    }

    logger.info(f"Evaluation complete: {report['strategies']}")
    return report

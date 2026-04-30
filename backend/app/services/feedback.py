"""
Feedback loop service.

Processes build events (saved / rerolled / ignored) to compute perk affinity
scores based on actual user behavior. These scores are blended with the
Nightlight co-occurrence graph to produce increasingly personalized recommendations.

Scoring model:
  - saved build:    each perk pair gets +1.0 signal
  - rerolled build: each perk pair gets -0.5 signal
  - ignored build:  each perk pair gets -0.1 signal (called on next generate)

Affinity score formula:
  raw = Σ(save_signals) - Σ(reroll_signals * 0.5) - Σ(ignore_signals * 0.1)
  normalized = sigmoid(raw / scale) mapped to [0, 1]

The final graph weight used in build generation is:
  combined = nightlight_weight * 0.6 + affinity_score * 0.4

As more saves accumulate, user behavior increasingly dominates recommendations.
"""
import itertools
import logging
import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.feedback import BuildEvent, PerkAffinityScore

logger = logging.getLogger(__name__)

# Signal weights
SIGNAL_WEIGHTS = {
    "saved": 1.0,
    "rerolled": -0.5,
    "ignored": -0.1,
    "generated": 0.0,  # neutral — just a record
}

# How much user affinity blends into the graph (grows with data volume)
BASE_AFFINITY_BLEND = 0.4
MIN_EVENTS_FOR_BLEND = 5  # don't blend until we have at least this many events


def _normalize_pair(a: str, b: str) -> tuple[str, str]:
    """Always store pairs in canonical (smaller, larger) order."""
    return (a, b) if a < b else (b, a)


def _sigmoid_normalize(raw: float, scale: float = 5.0) -> float:
    """Map any real number to (0, 1) via sigmoid, centered at 0."""
    return 1.0 / (1.0 + math.exp(-raw / scale))


async def record_event(
    db: AsyncSession,
    perk_ids: list[str],
    event_type: str,
    generation_mode: Optional[str] = None,
    theme: Optional[str] = None,
) -> None:
    """Record a build interaction event."""
    if len(perk_ids) != 4:
        return
    if event_type not in SIGNAL_WEIGHTS:
        return

    sorted_ids = sorted(perk_ids)
    key = ",".join(sorted_ids)

    db.add(BuildEvent(
        perk_ids_key=key,
        perk_a=sorted_ids[0],
        perk_b=sorted_ids[1],
        perk_c=sorted_ids[2],
        perk_d=sorted_ids[3],
        event_type=event_type,
        generation_mode=generation_mode,
        theme=theme,
    ))
    await db.flush()

    # Recompute affinity scores for all pairs in this build if it's a meaningful event
    if event_type in ("saved", "rerolled"):
        await recompute_affinity_for_perks(db, perk_ids)


async def recompute_affinity_for_perks(
    db: AsyncSession,
    perk_ids: list[str],
) -> None:
    """Recompute affinity scores for all pairs involving any of these perks."""
    for a, b in itertools.combinations(sorted(perk_ids), 2):
        await _update_pair_affinity(db, a, b)


async def _update_pair_affinity(db: AsyncSession, perk_a: str, perk_b: str) -> None:
    """
    Recompute the affinity score for a single perk pair from raw event data.
    """
    pa, pb = _normalize_pair(perk_a, perk_b)

    # Count saves where both perks appear
    save_count = (await db.execute(
        select(func.count(BuildEvent.id)).where(
            BuildEvent.event_type == "saved",
            BuildEvent.perk_ids_key.contains(pa),
            BuildEvent.perk_ids_key.contains(pb),
        )
    )).scalar() or 0

    # Count rerolls where both perks appear
    reroll_count = (await db.execute(
        select(func.count(BuildEvent.id)).where(
            BuildEvent.event_type == "rerolled",
            BuildEvent.perk_ids_key.contains(pa),
            BuildEvent.perk_ids_key.contains(pb),
        )
    )).scalar() or 0

    ignore_count = (await db.execute(
        select(func.count(BuildEvent.id)).where(
            BuildEvent.event_type == "ignored",
            BuildEvent.perk_ids_key.contains(pa),
            BuildEvent.perk_ids_key.contains(pb),
        )
    )).scalar() or 0

    raw = (
        save_count * SIGNAL_WEIGHTS["saved"]
        + reroll_count * SIGNAL_WEIGHTS["rerolled"]
        + ignore_count * SIGNAL_WEIGHTS["ignored"]
    )
    score = _sigmoid_normalize(raw)

    existing = (await db.execute(
        select(PerkAffinityScore).where(
            PerkAffinityScore.perk_a_id == pa,
            PerkAffinityScore.perk_b_id == pb,
        )
    )).scalar_one_or_none()

    if existing:
        existing.save_cooccurrence = save_count
        existing.reroll_cooccurrence = reroll_count
        existing.affinity_score = score
    else:
        db.add(PerkAffinityScore(
            perk_a_id=pa,
            perk_b_id=pb,
            save_cooccurrence=save_count,
            reroll_cooccurrence=reroll_count,
            affinity_score=score,
        ))


async def get_affinity_blend_weight(db: AsyncSession) -> float:
    """
    Returns how much weight to give user affinity scores vs Nightlight data.
    Starts at 0, grows toward BASE_AFFINITY_BLEND as event count increases.
    This prevents the system from over-fitting to sparse early data.
    """
    event_count = (await db.execute(
        select(func.count(BuildEvent.id)).where(
            BuildEvent.event_type.in_(["saved", "rerolled"])
        )
    )).scalar() or 0

    if event_count < MIN_EVENTS_FOR_BLEND:
        return 0.0

    # Ramp up linearly from 0 → BASE_AFFINITY_BLEND over 50 events
    ramp = min(event_count / 50.0, 1.0)
    return BASE_AFFINITY_BLEND * ramp


async def get_perk_affinity(
    db: AsyncSession,
    perk_a_id: str,
    perk_b_id: str,
) -> float:
    """Return the user-behavior affinity score for a perk pair (0.0 if unknown)."""
    pa, pb = _normalize_pair(perk_a_id, perk_b_id)
    row = (await db.execute(
        select(PerkAffinityScore.affinity_score).where(
            PerkAffinityScore.perk_a_id == pa,
            PerkAffinityScore.perk_b_id == pb,
        )
    )).scalar_one_or_none()
    return row or 0.0


async def get_similar_perks(
    db: AsyncSession,
    perk_id: str,
    top_n: int = 10,
) -> list[dict]:
    """
    Collaborative filtering: return top-N perks that users who saved
    builds with perk_id also tended to use.
    Returns [{"perk_id": str, "affinity_score": float, "save_count": int}]
    """
    # Find all saved builds containing this perk
    saved_builds = (await db.execute(
        select(BuildEvent).where(
            BuildEvent.event_type == "saved",
            BuildEvent.perk_ids_key.contains(perk_id),
        )
    )).scalars().all()

    if not saved_builds:
        return []

    # Count co-occurrence with other perks
    co_counts: dict[str, int] = {}
    for build in saved_builds:
        all_ids = [build.perk_a, build.perk_b, build.perk_c, build.perk_d]
        for pid in all_ids:
            if pid != perk_id:
                co_counts[pid] = co_counts.get(pid, 0) + 1

    if not co_counts:
        return []

    max_count = max(co_counts.values())
    results = [
        {
            "perk_id": pid,
            "affinity_score": count / max_count,
            "save_count": count,
        }
        for pid, count in sorted(co_counts.items(), key=lambda x: -x[1])
    ]
    return results[:top_n]


async def mark_ignored_builds(db: AsyncSession, except_key: Optional[str] = None) -> None:
    """
    Mark all recent 'generated' events as 'ignored' if they weren't
    followed by a save. Called when a new build is generated.
    """
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    recent_generated = (await db.execute(
        select(BuildEvent).where(
            BuildEvent.event_type == "generated",
            BuildEvent.created_at >= cutoff,
        )
    )).scalars().all()

    for event in recent_generated:
        if except_key and event.perk_ids_key == except_key:
            continue
        event.event_type = "ignored"

    if recent_generated:
        await db.flush()
        # Recompute affinity for affected builds
        for event in recent_generated[:10]:  # cap to avoid slow recomputes
            pids = [event.perk_a, event.perk_b, event.perk_c, event.perk_d]
            await recompute_affinity_for_perks(db, pids)

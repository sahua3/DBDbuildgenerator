"""
Perk co-occurrence graph.

Nodes = perks (by UUID string).
Edge weight = normalized co-occurrence frequency in top Nightlight builds (0.0 - 1.0).

Used to find perks that "work well together" when generating builds.
"""
import networkx as nx
import numpy as np
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.perk import Perk
from app.models.edge import PerkEdge
import logging

logger = logging.getLogger(__name__)

# Global in-memory graph — rebuilt after each Nightlight scrape
_graph: Optional[nx.Graph] = None


def get_graph() -> Optional[nx.Graph]:
    return _graph


def build_graph(
    perks: list[dict],
    edges: list[dict],
) -> nx.Graph:
    """
    Build NetworkX graph from perk + edge data.

    perks: [{"id": str, "name": str, "categories": [...], "pick_rate": float, ...}]
    edges: [{"perk_a_id": str, "perk_b_id": str, "weight": float}]
    """
    G = nx.Graph()

    for p in perks:
        G.add_node(
            str(p["id"]),
            name=p["name"],
            categories=p.get("categories", []),
            pick_rate=p.get("pick_rate", 0.0),
            category_weight=p.get("category_weight", 0.0),
        )

    for e in edges:
        G.add_edge(str(e["perk_a_id"]), str(e["perk_b_id"]), weight=e["weight"])

    logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    return G


async def load_graph_from_db(db: AsyncSession) -> nx.Graph:
    """Load all perks and edges from DB, build the graph, cache globally."""
    global _graph

    perk_rows = await db.execute(select(Perk))
    perks_data = [
        {
            "id": str(p.id),
            "name": p.name,
            "categories": p.categories or [],
            "pick_rate": p.pick_rate,
            "category_weight": p.category_weight,
        }
        for p in perk_rows.scalars().all()
    ]

    edge_rows = await db.execute(select(PerkEdge))
    edges_data = [
        {
            "perk_a_id": str(e.perk_a_id),
            "perk_b_id": str(e.perk_b_id),
            "weight": e.weight,
        }
        for e in edge_rows.scalars().all()
    ]

    _graph = build_graph(perks_data, edges_data)
    return _graph


def score_build_compatibility(
    perk_ids: list[str],
    graph: nx.Graph,
) -> float:
    """
    Score a potential 4-perk build by summing edge weights between all pairs.
    Higher = perks that commonly appear together.
    """
    total = 0.0
    count = 0
    for i in range(len(perk_ids)):
        for j in range(i + 1, len(perk_ids)):
            a, b = perk_ids[i], perk_ids[j]
            if graph.has_edge(a, b):
                total += graph[a][b]["weight"]
            count += 1
    return total / count if count > 0 else 0.0


def get_perk_neighbors_by_category(
    seed_perk_id: str,
    target_category: str,
    graph: nx.Graph,
    top_n: int = 10,
    exclude_ids: Optional[set] = None,
) -> list[tuple[str, float]]:
    """
    Given a seed perk, find the top-N perks in target_category that co-occur most
    with the seed perk. Returns list of (perk_id, score).
    """
    if seed_perk_id not in graph:
        return []

    exclude_ids = exclude_ids or set()
    candidates = []

    for neighbor_id in graph.neighbors(seed_perk_id):
        if neighbor_id in exclude_ids:
            continue
        node_data = graph.nodes[neighbor_id]
        if target_category in node_data.get("categories", []):
            weight = graph[seed_perk_id][neighbor_id]["weight"]
            # Boost by the neighbor's own pick rate
            combined_score = weight * 0.7 + node_data.get("pick_rate", 0.0) * 0.3
            candidates.append((neighbor_id, combined_score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_n]


def update_edge_weights(
    co_occurrence_counts: dict[tuple[str, str], int],
    graph: nx.Graph,
) -> nx.Graph:
    """
    Given raw co-occurrence counts from scraped builds,
    normalize and update edge weights in graph.
    """
    if not co_occurrence_counts:
        return graph

    max_count = max(co_occurrence_counts.values())

    for (a, b), count in co_occurrence_counts.items():
        weight = count / max_count
        if graph.has_edge(a, b):
            graph[a][b]["weight"] = weight
        else:
            graph.add_edge(a, b, weight=weight)

    return graph

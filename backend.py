# backend.py

from typing import List, Dict
from database_manager import DatabaseManager

db = DatabaseManager()

def get_top_papers(query: str, k: int = 5) -> List[Dict]:
    """
    Simple wrapper: returns top-k papers for a query.
    For now this just does a LIKE search over title/abstract.
    """
    # If query empty, just grab any k recent papers
    if not query:
        rows = db.cursor.execute(
            """
            SELECT arxiv_id, title, abstract, authors, published_date
            FROM papers
            WHERE processed = 1
            ORDER BY fetched_date DESC
            LIMIT ?
            """,
            (k,),
        ).fetchall()
        return [dict(r) for r in rows]

    rows = db.search_papers(query=query, limit=k)
    return rows

def get_knowledge_graph(query: str) -> Dict:
    """
    Stub for graph data. Replace with real Neo4j call later.
    For now, return a tiny fake graph built from top-3 papers.
    """
    papers = get_top_papers(query, k=3)
    nodes = []
    edges = []

    # Paper nodes
    for p in papers:
        nodes.append({
            "id": p["arxiv_id"],
            "label": "paper",
            "title": p["title"],
        })

    # Fake concept nodes, just to demo the graph
    for i, p in enumerate(papers):
        concept_id = f"concept_{i+1}"
        nodes.append({
            "id": concept_id,
            "label": "concept",
            "title": f"Concept {i+1}",
        })
        edges.append({
            "source": p["arxiv_id"],
            "target": concept_id,
            "relation": "MENTIONS",
        })

    return {"nodes": nodes, "edges": edges}

def get_db_stats() -> Dict:
    """Expose DB stats for optional UI display."""
    return db.get_stats()

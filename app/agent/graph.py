"""
Phase 6 (FR-4.5, bonus): the manual-refresh pipeline as an explicit LangGraph
graph - analyze -> retrieve -> evaluate retrieval quality -> refine-if-weak
-> generate. Phase 4 deliberately built this as a plain function chain
(agent/nodes.py) since a graph wasn't needed yet; this refactors that chain's
building blocks into a graph without changing their individual logic.

Scoped to `POST /refresh` only (see run_recommendation_graph). The
first-generation / auto-regenerate-on-threshold paths (GET /recommendations)
deliberately keep using nodes.prepare_candidates + generate_narrative_stream
instead - that split exists specifically to stream the narrative
incrementally (Phase 4 follow-up #3), which a single graph.invoke() call
would block on end-to-end and undo.
"""

import logging

from langgraph.graph import END, START, StateGraph
from sqlmodel import Session
from typing_extensions import TypedDict

from app.agent.nodes import (
    NO_ACTIVITY_NARRATIVE,
    TOP_K,
    BehavioralProfile,
    build_profile,
    generate_narrative,
    retrieve_candidates,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# Qdrant cosine-similarity score below which the top candidate is considered
# a weak match, worth one broader retrieval attempt before generating.
WEAK_SCORE_THRESHOLD = 0.35
MAX_RETRIEVAL_ATTEMPTS = 2
REFINED_TOP_K = TOP_K * 3


class GraphState(TypedDict):
    session: Session
    user: User
    category: str | None
    max_price: float | None
    profile: BehavioralProfile
    candidates: list[dict]
    retrieval_attempts: int
    narrative: str
    product_ids: list[int]


def _analyze(state: GraphState) -> dict:
    return {"profile": build_profile(state["session"], state["user"])}


def _retrieve(state: GraphState) -> dict:
    attempts = state["retrieval_attempts"] + 1
    top_k = TOP_K if attempts == 1 else REFINED_TOP_K
    candidates = retrieve_candidates(
        state["profile"],
        top_k=top_k,
        category=state["category"],
        max_price=state["max_price"],
    )
    return {"candidates": candidates, "retrieval_attempts": attempts}


def _evaluate_retrieval(state: GraphState) -> str:
    """Conditional edge out of _retrieve: 'refine' loops back for one wider
    retrieval attempt if the top match is weak; 'generate' proceeds
    otherwise (including the empty-candidates case - nothing to refine)."""
    candidates = state["candidates"]
    if not candidates:
        return "generate"
    top_score = candidates[0].get("score", 1.0)
    if (
        top_score < WEAK_SCORE_THRESHOLD
        and state["retrieval_attempts"] < MAX_RETRIEVAL_ATTEMPTS
    ):
        return "refine"
    return "generate"


def _generate(state: GraphState) -> dict:
    candidates = state["candidates"]
    if not candidates:
        return {"narrative": NO_ACTIVITY_NARRATIVE, "product_ids": []}
    narrative = generate_narrative(state["profile"], candidates)
    return {"narrative": narrative, "product_ids": [c["id"] for c in candidates]}


def _build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("analyze", _analyze)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("generate", _generate)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_conditional_edges(
        "retrieve", _evaluate_retrieval, {"refine": "retrieve", "generate": "generate"}
    )
    graph.add_edge("generate", END)
    return graph.compile()


_compiled_graph = _build_graph()


def run_recommendation_graph(
    session: Session,
    user: User,
    category: str | None = None,
    max_price: float | None = None,
) -> tuple[str, list[int]]:
    """Runs the full analyze -> retrieve -> evaluate -> refine-if-weak ->
    generate graph. Returns (narrative, product_ids); callers persist as
    needed. Used by the manual refresh button (see prepare_candidates +
    generate_narrative_stream in agent/nodes.py for the streaming
    first-generation path). `category`/`max_price` optionally narrow
    retrieval to matching products (Phase 6 bonus: metadata filtering)."""
    result = _compiled_graph.invoke(
        {
            "session": session,
            "user": user,
            "category": category,
            "max_price": max_price,
            "profile": BehavioralProfile(),
            "candidates": [],
            "retrieval_attempts": 0,
            "narrative": "",
            "product_ids": [],
        }
    )
    logger.info(
        "LangGraph agent run complete for user_id=%s: %d product(s) after %d "
        "retrieval attempt(s)",
        user.id,
        len(result["product_ids"]),
        result["retrieval_attempts"],
    )
    return result["narrative"], result["product_ids"]

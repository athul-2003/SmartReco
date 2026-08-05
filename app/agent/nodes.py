"""
Phase 4 agent pipeline: analyze behavior -> retrieve grounded candidates ->
generate a persuasive narrative. A straight function chain for now - Phase 6
(FR-4.5, bonus) refactors this into an explicit LangGraph graph without
changing the actual logic (analyze -> decide-to-retrieve -> evaluate ->
refine-if-weak -> generate).
"""

from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.models.event import Event, EventType
from app.models.product import Product
from app.models.user import User
from app.services import vector_store
from app.services.embeddings import embed_texts
from app.services.llm_client import get_llm_client

PROFILE_EVENT_LIMIT = 50
TOP_K = 5


@dataclass
class BehavioralProfile:
    category_counts: dict[str, int] = field(default_factory=dict)
    search_queries: list[str] = field(default_factory=list)
    dwell_seconds_by_category: dict[str, int] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        return not (
            self.category_counts
            or self.search_queries
            or self.dwell_seconds_by_category
        )


def build_profile(session: Session, user: User) -> BehavioralProfile:
    """Recent events -> interests/categories/repeated searches (FR-4.1)."""
    events = session.exec(
        select(Event)
        .where(Event.user_id == user.id)
        .order_by(Event.created_at.desc())
        .limit(PROFILE_EVENT_LIMIT)
    ).all()

    product_ids = {e.product_id for e in events if e.product_id is not None}
    categories_by_product: dict[int, str] = {}
    if product_ids:
        products = session.exec(
            select(Product).where(Product.id.in_(product_ids))
        ).all()
        categories_by_product = {p.id: p.category for p in products}

    profile = BehavioralProfile()
    for event in events:
        category = (
            categories_by_product.get(event.product_id) if event.product_id else None
        )

        if event.event_type == EventType.search and event.event_metadata:
            query = event.event_metadata.get("query")
            if query:
                profile.search_queries.append(query)
        elif category and event.event_type in (EventType.view, EventType.click):
            profile.category_counts[category] = (
                profile.category_counts.get(category, 0) + 1
            )
        elif category and event.event_type == EventType.dwell and event.event_metadata:
            seconds = event.event_metadata.get("seconds", 0)
            profile.dwell_seconds_by_category[category] = (
                profile.dwell_seconds_by_category.get(category, 0) + seconds
            )

    return profile


def profile_to_query_text(profile: BehavioralProfile) -> str:
    if profile.is_empty:
        return "A new learner with no browsing history yet."

    parts = []
    if profile.category_counts:
        top = sorted(
            profile.category_counts.items(), key=lambda kv: kv[1], reverse=True
        )
        parts.append("Interested in: " + ", ".join(c for c, _ in top))
    if profile.dwell_seconds_by_category:
        top_dwell = sorted(
            profile.dwell_seconds_by_category.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        parts.append(
            "Spent the most time on: " + ", ".join(c for c, _ in top_dwell[:3])
        )
    if profile.search_queries:
        parts.append("Searched for: " + ", ".join(profile.search_queries[:10]))
    return ". ".join(parts)


def retrieve_candidates(profile: BehavioralProfile, top_k: int = TOP_K) -> list[dict]:
    """Embed the profile as a query, retrieve top-K real products from
    Qdrant (FR-4.2) - never invented, always grounded in the catalog."""
    query_text = profile_to_query_text(profile)
    vector = embed_texts([query_text])[0]
    return vector_store.search(vector, top_k=top_k)


def generate_narrative(profile: BehavioralProfile, candidates: list[dict]) -> str:
    """Mesh chat generation of the persuasive narrative (FR-4.3)."""
    candidate_lines = "\n".join(
        f"- (id={c['id']}) {c['title']} [{c['category']}]" for c in candidates
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You are SmartReco's recommendation assistant. Write a short, "
                "persuasive narrative (2-4 sentences) explaining why the listed "
                "courses fit this learner, based only on their real behavior "
                "given below. Never invent courses or facts not given to you."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Learner behavior: {profile_to_query_text(profile)}\n\n"
                f"Candidate courses:\n{candidate_lines}"
            ),
        },
    ]
    return get_llm_client().chat(messages)


def generate_recommendation(session: Session, user: User) -> tuple[str, list[int]]:
    """Full pipeline: behavioral profile -> Qdrant retrieval -> Mesh
    narrative. Returns (narrative, product_ids); callers persist as needed."""
    profile = build_profile(session, user)
    candidates = retrieve_candidates(profile)

    if not candidates:
        return (
            "Browse a few courses and we'll start tailoring recommendations to you.",
            [],
        )

    narrative = generate_narrative(profile, candidates)
    product_ids = [c["id"] for c in candidates]
    return narrative, product_ids

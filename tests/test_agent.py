from sqlmodel import Session

from app.agent import nodes
from app.models.event import Event, EventType
from app.models.product import Product
from app.models.user import User
from app.services.auth import hash_password


def _make_user(session: Session, email: str = "learner@example.com") -> User:
    user = User(email=email, password_hash=hash_password("hunter22"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_build_profile_empty_for_new_user(session: Session):
    user = _make_user(session)
    profile = nodes.build_profile(session, user)
    assert profile.is_empty


def test_build_profile_aggregates_categories_searches_and_dwell(session: Session):
    user = _make_user(session)
    product = Product(title="Python 101", description="d", category="Dev", price=0)
    session.add(product)
    session.commit()
    session.refresh(product)

    session.add_all(
        [
            Event(user_id=user.id, event_type=EventType.view, product_id=product.id),
            Event(user_id=user.id, event_type=EventType.click, product_id=product.id),
            Event(
                user_id=user.id,
                event_type=EventType.search,
                event_metadata={"query": "python"},
            ),
            Event(
                user_id=user.id,
                event_type=EventType.dwell,
                product_id=product.id,
                event_metadata={"seconds": 30},
            ),
        ]
    )
    session.commit()

    profile = nodes.build_profile(session, user)
    assert profile.category_counts == {"Dev": 2}
    assert profile.search_queries == ["python"]
    assert profile.dwell_seconds_by_category == {"Dev": 30}


def test_profile_to_query_text_empty_profile():
    profile = nodes.BehavioralProfile()
    assert "new learner" in nodes.profile_to_query_text(profile).lower()


def test_profile_to_query_text_includes_all_signals():
    profile = nodes.BehavioralProfile(
        category_counts={"Dev": 3},
        search_queries=["python"],
        dwell_seconds_by_category={"Dev": 60},
    )
    text = nodes.profile_to_query_text(profile)
    assert "Dev" in text
    assert "python" in text


def test_retrieve_candidates_embeds_profile_and_queries_qdrant(monkeypatch):
    monkeypatch.setattr(nodes, "embed_texts", lambda texts: [[0.1, 0.2, 0.3]])
    monkeypatch.setattr(
        nodes.vector_store,
        "search",
        lambda vector, top_k=5: [
            {
                "id": 1,
                "title": "Python 101",
                "category": "Dev",
                "price": 0,
                "score": 0.9,
            }
        ],
    )
    profile = nodes.BehavioralProfile(category_counts={"Dev": 1})
    candidates = nodes.retrieve_candidates(profile)
    assert candidates[0]["id"] == 1

from sqlmodel import Session

from app.agent import graph
from app.models.user import User
from app.services.auth import hash_password


def _make_user(session: Session, email: str = "learner@example.com") -> User:
    user = User(email=email, password_hash=hash_password("hunter22"))
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_run_recommendation_graph_returns_grounded_product_ids(
    session: Session, monkeypatch
):
    user = _make_user(session)
    monkeypatch.setattr(graph, "build_profile", lambda s, u: graph.BehavioralProfile())
    monkeypatch.setattr(
        graph,
        "retrieve_candidates",
        lambda profile, top_k=5, **kw: [
            {"id": 1, "title": "Python 101", "category": "Dev", "score": 0.9},
            {"id": 2, "title": "SQL Basics", "category": "Dev", "score": 0.8},
        ],
    )
    monkeypatch.setattr(
        graph, "generate_narrative", lambda p, c: "Because you like Dev courses."
    )

    narrative, product_ids = graph.run_recommendation_graph(session, user)
    assert narrative == "Because you like Dev courses."
    assert product_ids == [1, 2]


def test_run_recommendation_graph_handles_no_candidates(session: Session, monkeypatch):
    user = _make_user(session)
    monkeypatch.setattr(graph, "build_profile", lambda s, u: graph.BehavioralProfile())
    monkeypatch.setattr(graph, "retrieve_candidates", lambda profile, top_k=5, **kw: [])

    narrative, product_ids = graph.run_recommendation_graph(session, user)
    assert product_ids == []
    assert "browse" in narrative.lower()


def test_run_recommendation_graph_refines_weak_retrieval_once(
    session: Session, monkeypatch
):
    # A weak top match (below WEAK_SCORE_THRESHOLD) should trigger exactly
    # one wider retrieval attempt before generating, not an infinite loop.
    calls: list[int] = []

    def fake_retrieve(profile, top_k=5, **kw):
        calls.append(top_k)
        if len(calls) == 1:
            return [{"id": 1, "title": "Weak match", "category": "Dev", "score": 0.1}]
        return [{"id": 2, "title": "Strong match", "category": "Dev", "score": 0.9}]

    user = _make_user(session)
    monkeypatch.setattr(graph, "build_profile", lambda s, u: graph.BehavioralProfile())
    monkeypatch.setattr(graph, "retrieve_candidates", fake_retrieve)
    monkeypatch.setattr(graph, "generate_narrative", lambda p, c: "Refined pick.")

    narrative, product_ids = graph.run_recommendation_graph(session, user)

    assert calls == [graph.TOP_K, graph.REFINED_TOP_K]
    assert narrative == "Refined pick."
    assert product_ids == [2]


def test_run_recommendation_graph_passes_category_and_max_price_through(
    session: Session, monkeypatch
):
    received = {}

    def fake_retrieve(profile, top_k=5, category=None, max_price=None):
        received["category"] = category
        received["max_price"] = max_price
        return [{"id": 1, "title": "Python 101", "category": "Dev", "score": 0.9}]

    user = _make_user(session)
    monkeypatch.setattr(graph, "build_profile", lambda s, u: graph.BehavioralProfile())
    monkeypatch.setattr(graph, "retrieve_candidates", fake_retrieve)
    monkeypatch.setattr(graph, "generate_narrative", lambda p, c: "n")

    graph.run_recommendation_graph(session, user, category="Dev", max_price=500)

    assert received == {"category": "Dev", "max_price": 500}


def test_run_recommendation_graph_stops_refining_after_max_attempts(
    session: Session, monkeypatch
):
    # Even if every retrieval attempt stays weak, the graph must terminate
    # (not loop forever) and still generate from whatever it has.
    calls: list[int] = []

    def always_weak(profile, top_k=5, **kw):
        calls.append(top_k)
        return [{"id": 99, "title": "Still weak", "category": "Dev", "score": 0.05}]

    user = _make_user(session)
    monkeypatch.setattr(graph, "build_profile", lambda s, u: graph.BehavioralProfile())
    monkeypatch.setattr(graph, "retrieve_candidates", always_weak)
    monkeypatch.setattr(graph, "generate_narrative", lambda p, c: "Best effort.")

    narrative, product_ids = graph.run_recommendation_graph(session, user)

    assert len(calls) == graph.MAX_RETRIEVAL_ATTEMPTS
    assert narrative == "Best effort."
    assert product_ids == [99]

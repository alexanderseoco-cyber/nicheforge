from fastapi.testclient import TestClient

from app.main import app


def test_rank_rent_handoff_routes_are_registered():
    client = TestClient(app)
    collection = client.get("/api/v1/rank-rent/handoffs")
    assert collection.status_code == 200
    assert isinstance(collection.json(), list)

    unknown = client.get("/api/v1/rank-rent/handoffs/does-not-exist")
    assert unknown.status_code == 404

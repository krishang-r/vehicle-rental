import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client


def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"message": "Hello from vehicle-rental Flask app!"}

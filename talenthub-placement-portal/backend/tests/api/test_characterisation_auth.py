"""Characterisation tests (Iteration 0): pin existing auth behaviour we keep. These pass before any change."""
from tests.conftest import login


async def test_login_with_correct_password_returns_token(client):
    r = await client.post("/auth/login", json={"email": "rahul@student.talenthub.edu", "password": "password123"})
    assert r.status_code == 200
    assert r.json()["role"] == "STUDENT"
    assert r.json()["access_token"]


async def test_login_with_wrong_password_is_401(client):
    r = await client.post("/auth/login", json={"email": "rahul@student.talenthub.edu", "password": "wrong"})
    assert r.status_code == 401


async def test_FR1_1_protected_route_without_token_is_401(client):
    r = await client.get("/applications/me")
    assert r.status_code == 401


async def test_FR1_1_student_cannot_call_company_route(client):
    headers = await login(client, "rahul@student.talenthub.edu")
    r = await client.get("/jobs/mine", headers=headers)
    assert r.status_code == 403

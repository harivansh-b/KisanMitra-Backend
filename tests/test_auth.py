from app.core.security import create_test_jwt
from app.utils.enums import UserRole


def test_auth_without_token(client):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_auth_with_invalid_token(client):
    res = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.payload"})
    assert res.status_code == 401


def test_auth_with_valid_token_unregistered_profile(client):
    token = create_test_jwt(auth_user_id="unregistered-user-999", email="newuser@example.com")
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
    assert "not registered" in res.json()["error"]["message"]


def test_register_profile_farmer(client):
    token = create_test_jwt(auth_user_id="new-farmer-id-1", email="newfarmer@example.com")
    payload = {
        "role": "FARMER",
        "name": "Suresh Patel",
        "phone": "9812345678",
        "address": "Village Green",
        "village": "Anand",
        "district": "Anand",
        "state": "Gujarat",
        "pincode": "388001",
        "latitude": 22.5645,
        "longitude": 72.9289,
        "farm_size": 4.0,
    }
    res = client.post(
        "/api/v1/auth/register-profile",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "FARMER"
    assert data["profile"]["name"] == "Suresh Patel"
    assert data["profile"]["farm_size"] == 4.0


def test_auth_me_after_registration(client, farmer_user):
    token = create_test_jwt(auth_user_id=farmer_user.auth_user_id, email=farmer_user.email)
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "FARMER"
    assert data["profile"]["name"] == "Ramesh Kumar"

from app.core.security import create_test_jwt


def test_order_full_workflow(client, farmer_headers, buyer_headers, sample_crop):
    # 1. Farmer creates listing
    listing_res = client.post(
        "/api/v1/listings",
        json={
            "crop_id": sample_crop.id,
            "quantity": 100.0,
            "expected_price": 2600.0,
            "min_price": 2400.0,
        },
        headers=farmer_headers,
    )
    listing_id = listing_res.json()["id"]

    # 2. Buyer creates purchase request
    order_payload = {
        "listing_id": listing_id,
        "quantity": 40.0,
        "agreed_price": 2550.0,
        "delivery_location": "Mumbai Terminal 2",
        "notes": "Urgent delivery required",
    }
    create_res = client.post("/api/v1/orders", json=order_payload, headers=buyer_headers)
    assert create_res.status_code == 201
    order_data = create_res.json()
    order_id = order_data["id"]
    assert order_data["status"] == "PENDING"
    assert order_data["total_amount"] == 40.0 * 2550.0

    # 3. Unauthorized third party cannot view or modify order
    other_token = create_test_jwt(auth_user_id="random-user-id", email="random@example.com")
    # But first register that random user
    client.post(
        "/api/v1/auth/register-profile",
        json={"role": "FARMER", "name": "Third Party Farmer"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    unauthorized_res = client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert unauthorized_res.status_code == 403

    # 4. Seller accepts order
    accept_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "ACCEPTED"},
        headers=farmer_headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # 5. Order confirmed -> triggers transaction record
    confirm_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CONFIRMED"},
        headers=buyer_headers,
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "CONFIRMED"

    # Verify transaction ledger has entry
    txn_res = client.get("/api/v1/transactions", headers=buyer_headers)
    assert txn_res.status_code == 200
    txns = txn_res.json()["items"]
    assert any(t["order_id"] == order_id for t in txns)

    # 6. Mark order completed
    complete_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "COMPLETED"},
        headers=farmer_headers,
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["status"] == "COMPLETED"

    # 7. Invalid transition from terminal state COMPLETED -> Should fail
    tamper_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "CANCELLED"},
        headers=buyer_headers,
    )
    assert tamper_res.status_code == 400


def test_seller_rejects_order(client, farmer_headers, buyer_headers, sample_crop):
    listing_res = client.post(
        "/api/v1/listings",
        json={"crop_id": sample_crop.id, "quantity": 50.0, "expected_price": 3000.0},
        headers=farmer_headers,
    )
    listing_id = listing_res.json()["id"]

    order_res = client.post(
        "/api/v1/orders",
        json={"listing_id": listing_id, "quantity": 10.0},
        headers=buyer_headers,
    )
    order_id = order_res.json()["id"]

    reject_res = client.patch(
        f"/api/v1/orders/{order_id}/status",
        json={"status": "REJECTED"},
        headers=farmer_headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "REJECTED"

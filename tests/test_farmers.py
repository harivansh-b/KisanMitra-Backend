def test_get_farmer_me(client, farmer_headers):
    res = client.get("/api/v1/farmers/me", headers=farmer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Ramesh Kumar"
    assert data["village"] == "Khed"


def test_update_farmer_me(client, farmer_headers):
    update_data = {
        "name": "Ramesh Kumar (Updated)",
        "farm_size": 7.5,
        "village": "Manchar",
    }
    res = client.put("/api/v1/farmers/me", json=update_data, headers=farmer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Ramesh Kumar (Updated)"
    assert data["farm_size"] == 7.5
    assert data["village"] == "Manchar"


def test_farmer_create_listing(client, farmer_headers, sample_crop):
    listing_payload = {
        "crop_id": sample_crop.id,
        "variety": "Sharbati",
        "quantity": 50.0,
        "unit": "QUINTAL",
        "quality_grade": "GRADE_A",
        "expected_price": 2800.0,
        "min_price": 2600.0,
        "location_name": "Pune Mandi",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "description": "High quality organic wheat directly from farm",
    }
    res = client.post("/api/v1/listings", json=listing_payload, headers=farmer_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["quantity"] == 50.0
    assert data["expected_price"] == 2800.0
    assert data["seller_type"] == "FARMER"


def test_prevent_modifying_another_seller_listing(client, farmer_headers, fpo_headers, sample_crop):
    # FPO creates listing
    fpo_listing_payload = {
        "crop_id": sample_crop.id,
        "quantity": 100.0,
        "unit": "QUINTAL",
        "quality_grade": "GRADE_A",
        "expected_price": 2900.0,
        "min_price": 2700.0,
    }
    res = client.post("/api/v1/listings", json=fpo_listing_payload, headers=fpo_headers)
    assert res.status_code == 201
    listing_id = res.json()["id"]

    # Farmer tries to update FPO's listing -> Should be forbidden
    farmer_tamper = {
        "expected_price": 1000.0,
    }
    tamper_res = client.put(f"/api/v1/listings/{listing_id}", json=farmer_tamper, headers=farmer_headers)
    assert tamper_res.status_code == 403

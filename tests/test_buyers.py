def test_get_buyer_me(client, buyer_headers):
    res = client.get("/api/v1/buyers/me", headers=buyer_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["organization_name"] == "AgroFresh Wholesale Pvt Ltd"
    assert data["buyer_type"] == "WHOLESALER"


def test_update_buyer_me(client, buyer_headers):
    update_data = {
        "contact_person": "Anil Sharma (Managing Director)",
        "business_description": "Pan-India Agri Commodities Distributor",
    }
    res = client.put("/api/v1/buyers/me", json=update_data, headers=buyer_headers)
    assert res.status_code == 200
    assert res.json()["contact_person"] == "Anil Sharma (Managing Director)"


def test_buyer_create_requirement(client, buyer_headers, sample_crop):
    req_payload = {
        "crop_id": sample_crop.id,
        "variety": "Sharbati",
        "required_quantity": 200.0,
        "unit": "QUINTAL",
        "quality_grade": "GRADE_A",
        "target_price": 2850.0,
        "delivery_location": "Navi Mumbai Central Warehouse",
        "latitude": 19.0330,
        "longitude": 73.0297,
        "description": "Required for retail packaging",
    }
    res = client.post("/api/v1/requirements", json=req_payload, headers=buyer_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["required_quantity"] == 200.0
    assert data["target_price"] == 2850.0
    assert data["status"] == "ACTIVE"


def test_farmer_cannot_create_requirement(client, farmer_headers, sample_crop):
    req_payload = {
        "crop_id": sample_crop.id,
        "required_quantity": 100.0,
        "unit": "QUINTAL",
        "target_price": 2500.0,
    }
    res = client.post("/api/v1/requirements", json=req_payload, headers=farmer_headers)
    assert res.status_code == 403

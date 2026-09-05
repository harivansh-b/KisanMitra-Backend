def test_marketplace_listing_filters(client, farmer_headers, fpo_headers, sample_crop):
    # Listing 1: Wheat Grade A @ 2500
    client.post(
        "/api/v1/listings",
        json={
            "crop_id": sample_crop.id,
            "variety": "Sharbati",
            "quantity": 50.0,
            "quality_grade": "GRADE_A",
            "expected_price": 2500.0,
        },
        headers=farmer_headers,
    )
    # Listing 2: Wheat Grade B @ 2200
    client.post(
        "/api/v1/listings",
        json={
            "crop_id": sample_crop.id,
            "variety": "Lokwan",
            "quantity": 100.0,
            "quality_grade": "GRADE_B",
            "expected_price": 2200.0,
        },
        headers=fpo_headers,
    )

    # Filter by Grade A
    res_grade = client.get("/api/v1/marketplace/listings?quality_grade=GRADE_A")
    assert res_grade.status_code == 200
    items = res_grade.json()["items"]
    assert all(item["quality_grade"] == "GRADE_A" for item in items)

    # Filter by price range (max_price = 2300)
    res_price = client.get("/api/v1/marketplace/listings?max_price=2300")
    assert res_price.status_code == 200
    items = res_price.json()["items"]
    assert all(item["expected_price"] <= 2300 for item in items)


def test_marketplace_deterministic_matching(client, farmer_headers, buyer_headers, sample_crop):
    # 1. Create a listing
    listing_res = client.post(
        "/api/v1/listings",
        json={
            "crop_id": sample_crop.id,
            "variety": "Sharbati",
            "quantity": 80.0,
            "quality_grade": "GRADE_A",
            "expected_price": 2700.0,
            "min_price": 2500.0,
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=farmer_headers,
    )
    listing_id = listing_res.json()["id"]

    # 2. Create matching requirement (target price 2800 >= listing price 2700)
    req_res = client.post(
        "/api/v1/requirements",
        json={
            "crop_id": sample_crop.id,
            "variety": "Sharbati",
            "required_quantity": 100.0,
            "quality_grade": "GRADE_A",
            "target_price": 2800.0,
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=buyer_headers,
    )
    req_id = req_res.json()["id"]

    # 3. Match listings for buyer requirement
    match_listings_res = client.get(f"/api/v1/marketplace/match-listings-for-requirement/{req_id}")
    assert match_listings_res.status_code == 200
    matched_listings = match_listings_res.json()
    assert any(l["id"] == listing_id for l in matched_listings)

    # 4. Match requirements for seller listing
    match_reqs_res = client.get(f"/api/v1/marketplace/match-requirements-for-listing/{listing_id}")
    assert match_reqs_res.status_code == 200
    matched_reqs = match_reqs_res.json()
    assert any(r["id"] == req_id for r in matched_reqs)

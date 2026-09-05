def test_get_fpo_me(client, fpo_headers):
    res = client.get("/api/v1/fpos/me", headers=fpo_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["organization_name"] == "Sahyadri Farmers Producer Co"
    assert data["registration_number"] == "FPO-MH-2023-001"


def test_update_fpo_me(client, fpo_headers):
    update_data = {
        "contact_person": "Vikas Patil (Director)",
        "description": "Updated FPO description with 500+ members",
    }
    res = client.put("/api/v1/fpos/me", json=update_data, headers=fpo_headers)
    assert res.status_code == 200
    assert res.json()["contact_person"] == "Vikas Patil (Director)"


def test_fpo_add_and_list_members(client, fpo_headers, farmer_user):
    farmer_profile_id = farmer_user.farmer_profile.id
    payload = {
        "farmer_id": farmer_profile_id,
        "membership_role": "MEMBER",
    }
    # Add member
    add_res = client.post("/api/v1/fpos/members", json=payload, headers=fpo_headers)
    assert add_res.status_code == 201
    assert add_res.json()["farmer_id"] == farmer_profile_id

    # List members
    list_res = client.get("/api/v1/fpos/members", headers=fpo_headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert data["total"] >= 1
    assert any(m["farmer_id"] == farmer_profile_id for m in data["items"])

    # Remove member
    del_res = client.delete(f"/api/v1/fpos/members/{farmer_profile_id}", headers=fpo_headers)
    assert del_res.status_code == 204

    # Verify removal
    list_again = client.get("/api/v1/fpos/members", headers=fpo_headers)
    assert not any(m["farmer_id"] == farmer_profile_id for m in list_again.json()["items"])

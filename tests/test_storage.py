import io
from app.core.security import create_test_jwt


def test_storage_document_lifecycle(client, farmer_headers, buyer_headers):
    # 1. Upload document (mock file)
    file_content = b"Mock Aadhaar Card Verification PDF"
    files = {"file": ("aadhaar.pdf", io.BytesIO(file_content), "application/pdf")}
    data = {"bucket": "documents", "owner_type": "FARMER"}

    upload_res = client.post("/api/v1/storage/upload", files=files, data=data, headers=farmer_headers)
    assert upload_res.status_code == 201
    doc_data = upload_res.json()
    doc_id = doc_data["id"]
    assert doc_data["file_name"] == "aadhaar.pdf"
    assert doc_data["content_type"] == "application/pdf"
    assert "url" in doc_data

    # 2. List my documents
    list_res = client.get("/api/v1/storage", headers=farmer_headers)
    assert list_res.status_code == 200
    docs = list_res.json()
    assert any(d["id"] == doc_id for d in docs)

    # 3. Retrieve document by ID
    get_res = client.get(f"/api/v1/storage/{doc_id}", headers=farmer_headers)
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id

    # 4. Another user cannot access or delete the document -> 403 Forbidden
    unauthorized_get = client.get(f"/api/v1/storage/{doc_id}", headers=buyer_headers)
    assert unauthorized_get.status_code == 403

    unauthorized_del = client.delete(f"/api/v1/storage/{doc_id}", headers=buyer_headers)
    assert unauthorized_del.status_code == 403

    # 5. Delete document
    del_res = client.delete(f"/api/v1/storage/{doc_id}", headers=farmer_headers)
    assert del_res.status_code == 204

    # 6. Verify deleted -> 404
    get_after_del = client.get(f"/api/v1/storage/{doc_id}", headers=farmer_headers)
    assert get_after_del.status_code == 404

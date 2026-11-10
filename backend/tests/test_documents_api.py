from io import BytesIO


def upload(client, sample_pdf):
    return client.post(
        "/api/v1/documents",
        data={"file": (BytesIO(sample_pdf), "notice.pdf")},
        content_type="multipart/form-data",
    )


def test_upload_returns_one_time_token_and_verified_analysis(client, sample_pdf):
    response = upload(client, sample_pdf)
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["access_token"]
    assert payload["page_count"] == 1
    assert payload["analysis"]["required_documents"][0]["page_number"] == 1
    assert payload["analysis"]["deadlines"][0]["normalized_date"] == "2026-11-30"


def test_document_read_requires_token(client, sample_pdf):
    payload = upload(client, sample_pdf).get_json()
    document_id = payload["document_id"]
    assert client.get("/api/v1/documents/" + document_id).status_code == 401
    response = client.get(
        "/api/v1/documents/" + document_id,
        headers={"X-Document-Token": payload["access_token"]},
    )
    assert response.status_code == 200
    assert "access_token" not in response.get_json()


def test_question_answer_is_grounded_and_unknown_is_explicit(client, sample_pdf):
    payload = upload(client, sample_pdf).get_json()
    document_id = payload["document_id"]
    headers = {"X-Document-Token": payload["access_token"]}
    supported = client.post(
        "/api/v1/documents/" + document_id + "/questions",
        json={"question": "What documents must I attach?"},
        headers=headers,
    )
    assert supported.status_code == 200
    assert supported.get_json()["found"] is True
    unknown = client.post(
        "/api/v1/documents/" + document_id + "/questions",
        json={"question": "What is the applicant's income?"},
        headers=headers,
    )
    assert unknown.status_code == 200
    assert unknown.get_json()["found"] is False
    assert unknown.get_json()["sources"] == []


def test_delete_removes_workspace(client, sample_pdf):
    payload = upload(client, sample_pdf).get_json()
    document_id = payload["document_id"]
    headers = {"X-Document-Token": payload["access_token"]}
    deleted = client.delete("/api/v1/documents/" + document_id, headers=headers)
    assert deleted.status_code == 200
    assert deleted.get_json()["deleted"] is True
    assert client.get("/api/v1/documents/" + document_id, headers=headers).status_code == 404


def test_upload_rejects_non_pdf(client):
    response = client.post(
        "/api/v1/documents",
        data={"file": (BytesIO(b"not a pdf"), "notice.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "INVALID_PDF"

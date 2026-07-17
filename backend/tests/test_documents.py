from pathlib import Path


def test_upload_document_returns_created_document(client, auth_headers):
    file_content = b"%PDF-1.4\n% Test PDF content\n"

    response = client.post(
        "/documents/upload",
        headers=auth_headers,
        files={
            "file": (
                "test_document.pdf",
                file_content,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["original_filename"] == "test_document.pdf"
    assert data["file_type"] == "pdf"
    assert data["file_size"] == len(file_content)
    assert data["status"] == "uploaded"
    assert data["owner_id"] > 0

    saved_path = Path(data["file_path"])

    assert saved_path.exists()
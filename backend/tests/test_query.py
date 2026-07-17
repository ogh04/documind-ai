class FakeSearchPoint:
    def __init__(self, score, payload):
        self.score = score
        self.payload = payload


def test_query_returns_semantic_search_results(
    client,
    auth_headers,
    monkeypatch,
):
    def fake_embed_query(question):
        assert question == "What datasets are used in this project?"
        return [0.1, 0.2, 0.3]

    def fake_search_similar_chunks(
        query_vector,
        user_id,
        top_k,
        document_id=None,
    ):
        assert query_vector == [0.1, 0.2, 0.3]
        assert user_id == 1
        assert top_k == 3
        assert document_id == 6

        return [
            FakeSearchPoint(
                score=0.91,
                payload={
                    "document_id": 6,
                    "user_id": user_id,
                    "page_number": 2,
                    "chunk_index": 0,
                    "text": "The project uses chest X-ray datasets.",
                    "source_filename": "cxr_deep_learning_report.pdf",
                    "document_chunk_id": 10,
                },
            )
        ]

    monkeypatch.setattr(
        "app.api.query.embed_query",
        fake_embed_query,
    )

    monkeypatch.setattr(
        "app.api.query.search_similar_chunks",
        fake_search_similar_chunks,
    )

    response = client.post(
        "/query",
        headers=auth_headers,
        json={
            "question": "What datasets are used in this project?",
            "document_id": 6,
            "top_k": 3,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "What datasets are used in this project?"
    assert data["top_k"] == 3
    assert data["results_count"] == 1

    result = data["results"][0]

    assert result["score"] == 0.91
    assert result["document_id"] == 6
    assert result["user_id"] == 1
    assert result["page_number"] == 2
    assert result["chunk_index"] == 0
    assert result["text"] == "The project uses chest X-ray datasets."
    assert result["source_filename"] == "cxr_deep_learning_report.pdf"
    assert result["document_chunk_id"] == 10
from src.dev.local_embeddings import embed_text, embed_texts


def test_local_embedder_is_deterministic() -> None:
    first = embed_text("React FastAPI pgvector", 32)
    second = embed_text("React FastAPI pgvector", 32)

    assert first == second
    assert len(first) == 32


def test_local_embedder_vectorizes_multiple_texts() -> None:
    vectors = embed_texts(["alpha beta", "gamma delta"], 16)

    assert len(vectors) == 2
    assert all(len(vector) == 16 for vector in vectors)

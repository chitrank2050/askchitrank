from src.retrieval.search import assess_retrieval_confidence


def test_retrieval_confidence_rejects_low_similarity() -> None:
    assessment = assess_retrieval_confidence(
        "What is his favorite movie?",
        [
            {
                "id": "weak-1",
                "source": "resume",
                "source_id": "resume-1",
                "content": "Technical Skills: React, TypeScript",
                "chunk_index": 0,
                "similarity": 0.32,
            }
        ],
    )

    assert assessment.is_confident is False
    assert assessment.reason == "low_similarity"


def test_retrieval_confidence_allows_strong_semantic_match_without_overlap() -> None:
    assessment = assess_retrieval_confidence(
        "Tell me about his work history",
        [
            {
                "id": "strong-1",
                "source": "linkedin",
                "source_id": "linkedin-profile",
                "content": "Professional Experience: Senior Software Engineer across product teams.",
                "chunk_index": 0,
                "similarity": 0.81,
                "score": 0.86,
                "query_term_matches": 0,
                "query_term_coverage": 0.0,
            }
        ],
    )

    assert assessment.is_confident is True
    assert assessment.reason == "ok"

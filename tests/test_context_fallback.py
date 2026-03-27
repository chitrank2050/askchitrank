from src.chat.context_fallback import build_context_fallback_response


def test_context_fallback_answers_experience_question() -> None:
    response = build_context_fallback_response(
        "How many years of experience does he have?",
        [
            {
                "source": "resume",
                "content": (
                    "Resume Section: Summary\n"
                    "Senior Software Engineer with 8+ years of experience building "
                    "frontend and full-stack products."
                ),
            }
        ],
    )

    assert response == "Chitrank has 8+ years of experience."


def test_context_fallback_answers_project_question() -> None:
    response = build_context_fallback_response(
        "What projects has Chitrank built?",
        [
            {
                "source": "sanity",
                "content": (
                    "Project: Ask Chitrank\nTechnologies: FastAPI, PostgreSQL, pgvector"
                ),
            }
        ],
    )

    assert response is not None
    assert "Ask Chitrank" in response
    assert "FastAPI" in response

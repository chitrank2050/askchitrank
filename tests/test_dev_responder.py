from src.chat.prompt import build_messages
from src.dev.responder import build_seeded_response


def test_seeded_response_mentions_projects_and_technologies() -> None:
    chunks = [
        {
            "source": "sanity",
            "content": (
                "Project: Ask Avery\n"
                "Technologies: FastAPI, PostgreSQL, pgvector\n"
                "Overview: Built a grounded portfolio chatbot."
            ),
        }
    ]

    messages = build_messages(
        question="What projects has Avery built?",
        chunks=chunks,
    )

    response = build_seeded_response(messages)

    assert "Ask Avery" in response
    assert "FastAPI" in response

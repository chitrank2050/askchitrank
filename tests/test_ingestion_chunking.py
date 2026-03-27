from src.core.config import settings
from src.ingestion.chunker import chunk_document, chunk_loaded_document, chunk_text
from src.ingestion.linkedin_loader import (
    _build_profile_documents,
    _build_recommendation_document,
)
from src.ingestion.pipeline import _chunk_resume_by_section
from src.ingestion.sanity_loader import _build_project_documents


def test_chunk_text_preserves_paragraph_boundaries_when_overlap_is_zero() -> None:
    text = "alpha beta gamma\n\ndelta epsilon zeta"

    chunks = chunk_text(text, chunk_size=4, chunk_overlap=0)

    assert chunks == ["alpha beta gamma", "delta epsilon zeta"]


def test_chunk_document_repeats_prefix_on_multi_chunk_documents() -> None:
    prefix = "Project: Atlas\nEvidence Type: project"
    text = (
        f"{prefix}\n\nOverview: one two three four five six seven eight nine ten "
        "eleven twelve"
    )

    chunks = chunk_document(
        text=text,
        source="sanity",
        source_id="atlas#overview",
        chunk_size=8,
        chunk_overlap=1,
        chunk_prefix=prefix,
    )

    assert len(chunks) > 1
    assert all(chunk["content"].startswith(prefix) for chunk in chunks)


def test_build_project_documents_expose_chunk_prefix() -> None:
    documents = _build_project_documents(
        {
            "_id": "project-1",
            "title": "Atlas",
            "role": "Lead Engineer",
            "company": "Acme",
            "overview": "Built the platform.",
            "vision": "Make onboarding faster.",
            "technologies": ["FastAPI", "Postgres"],
            "contribution": ["Designed APIs", "Led delivery"],
            "liveUrl": "https://example.com",
            "githubUrl": "https://github.com/example/repo",
        }
    )

    assert all(document["chunk_prefix"] for document in documents)
    assert documents[0]["chunk_prefix"].startswith("Project: Atlas")


def test_sanity_project_chunks_repeat_prefix_when_split() -> None:
    documents = _build_project_documents(
        {
            "_id": "project-1",
            "title": "Atlas",
            "role": "Lead Engineer",
            "company": "Acme",
            "overview": " ".join(["Built the platform."] * 20),
            "vision": " ".join(["Make onboarding faster."] * 12),
            "technologies": ["FastAPI", "Postgres"],
            "contribution": ["Designed APIs", "Led delivery"],
            "liveUrl": "",
            "githubUrl": "",
        }
    )
    overview_document = next(
        document
        for document in documents
        if document["source_id"].endswith("#overview")
    )

    chunks = chunk_loaded_document(overview_document, chunk_size=40, chunk_overlap=4)

    assert len(chunks) > 1
    assert all(
        chunk["content"].startswith(overview_document["chunk_prefix"])
        for chunk in chunks
    )


def test_linkedin_chunks_repeat_prefix_when_split() -> None:
    profile_document = _build_profile_documents(
        {
            "First Name": "Avery",
            "Last Name": "Quinn",
            "Headline": "Senior Software Engineer",
            "Summary": " ".join(["Built developer-facing products."] * 18),
            "Industry": "Software",
            "Geo Location": "India",
            "Websites": "",
        }
    )[0]
    recommendation_document = _build_recommendation_document(
        {
            "First Name": "Neha",
            "Last Name": "Kapoor",
            "Job Title": "Designer",
            "Company": "Studio",
            "Text": " ".join(["Avery is collaborative and dependable."] * 18),
        },
        index=0,
    )

    profile_chunks = chunk_loaded_document(
        profile_document, chunk_size=40, chunk_overlap=4
    )
    recommendation_chunks = chunk_loaded_document(
        recommendation_document, chunk_size=40, chunk_overlap=4
    )

    assert len(profile_chunks) > 1
    assert len(recommendation_chunks) > 1
    assert all(
        chunk["content"].startswith(profile_document["chunk_prefix"])
        for chunk in profile_chunks
    )
    assert all(
        chunk["content"].startswith(recommendation_document["chunk_prefix"])
        for chunk in recommendation_chunks
    )


def test_resume_section_chunks_repeat_section_prefix(monkeypatch) -> None:
    monkeypatch.setattr(settings, "CHUNK_SIZE", 12)
    monkeypatch.setattr(settings, "CHUNK_OVERLAP", 2)

    text = (
        "Chitrank Agnihotri\nSoftware Engineer\n\n"
        "Professional Experience\n"
        + "Built systems for search and retrieval. " * 20
        + "\n\nTechnical Skills\nPython FastAPI SQLAlchemy"
    )

    chunks = _chunk_resume_by_section(text)
    experience_chunks = [
        chunk
        for chunk in chunks
        if chunk["source_id"] == "resume-professional-experience"
    ]

    assert len(experience_chunks) > 1
    assert all(
        chunk["content"].startswith("Resume Section: Professional Experience")
        for chunk in experience_chunks
    )

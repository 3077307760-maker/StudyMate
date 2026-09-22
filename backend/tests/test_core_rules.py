import pytest

from app.core.errors import AppError
from app.services.document_service import ParsedSegment, chunk_segments, validate_upload


def test_chunking_uses_target_size_and_overlap() -> None:
    text = "第一段。" * 400
    chunks = chunk_segments([ParsedSegment(text=text, page=2, section="测试章节")])
    assert len(chunks) > 2
    assert all(len(chunk.content) <= 1000 for chunk in chunks)
    assert all(chunk.page == 2 for chunk in chunks)
    assert all(chunk.section == "测试章节" for chunk in chunks)
    assert chunks[0].content[-30:] in chunks[1].content


def test_upload_validation_rejects_disguised_file_and_path_names() -> None:
    with pytest.raises(AppError) as fake_pdf:
        validate_upload("notes.pdf", "application/pdf", b"plain text")
    assert fake_pdf.value.code == "UNSUPPORTED_FILE"

    with pytest.raises(AppError) as path_name:
        validate_upload("../notes.md", "text/markdown", b"# notes")
    assert path_name.value.code == "UNSUPPORTED_FILE"

    suffix, name = validate_upload("notes.md", "text/markdown", "课程内容".encode())
    assert suffix == ".md"
    assert name == "notes.md"

def test_quiz_validation_accepts_multiple_slides_from_same_document() -> None:
    from app.schemas import QuizCreate
    from app.services.quiz_service import _validate_generated_quiz

    context = [
        {
            "document_id": "doc-1",
            "page": None,
            "slide": 1,
            "snippet": "outline slide content",
        },
        {
            "document_id": "doc-1",
            "page": None,
            "slide": 2,
            "snippet": "second slide content for citation validation",
        },
    ]
    questions = []
    for index in range(5):
        questions.append(
            {
                "type": "single_choice",
                "stem": f"Question {index + 1}",
                "options": ["A option", "B option", "C option", "D option"],
                "correct_answer": "A",
                "explanation": "Explanation",
                "knowledge_tags": ["tag"],
                "citations": [
                    {
                        "document_id": "doc-1",
                        "page": None,
                        "slide": 2,
                        "snippet": "second slide content for citation validation",
                    }
                ],
            }
        )
    payload = QuizCreate(
        document_ids=["doc-1"],
        question_count=5,
        question_types=["single_choice"],
    )
    _validate_generated_quiz({"questions": questions}, payload, context)

def test_ai_provider_supports_chat_only_with_local_embedding(monkeypatch) -> None:
    from app.ai.providers import AiProvider
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_provider", "local")
    provider = AiProvider()
    assert provider.chat_enabled is True
    assert provider.embedding_client is None
    assert len(provider.embed(["alpha beta"])[0]) == 256

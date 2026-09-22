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

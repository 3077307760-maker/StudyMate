from fastapi.testclient import TestClient

from tests.conftest import create_course, register, upload_markdown

CONTENT = """# 操作系统第 3 章

## 进程

进程是程序的一次执行过程，是系统进行资源分配和调度的基本单位。进程拥有独立的地址空间。

## 线程

线程是进程中的一个执行单元，是处理器调度和分派的基本单位。同一进程内的线程共享进程资源。
"""


def prepare_course(client: TestClient) -> tuple[dict[str, str], dict, dict]:
    headers = register(client, "owner@example.com", "Owner")
    course = create_course(client, headers)
    document = upload_markdown(client, headers, course["id"], CONTENT)
    assert document["status"] in {"pending", "ready"}
    status = client.get(f"/api/documents/{document['id']}", headers=headers)
    assert status.status_code == 200
    assert status.json()["status"] == "ready"
    assert status.json()["chunk_count"] >= 1
    return headers, course, status.json()


def test_document_validation_duplicate_and_chat_stream(client: TestClient) -> None:
    headers, course, document = prepare_course(client)
    duplicate = client.post(
        f"/api/courses/{course['id']}/documents",
        files={"file": ("duplicate.md", CONTENT.encode("utf-8"), "text/markdown")},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["details"]["document_id"] == document["id"]

    fake_pdf = client.post(
        f"/api/courses/{course['id']}/documents",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
        headers=headers,
    )
    assert fake_pdf.status_code == 415
    assert fake_pdf.json()["code"] == "UNSUPPORTED_FILE"

    conversation = client.post(
        f"/api/courses/{course['id']}/conversations",
        json={"title": "新会话"},
        headers=headers,
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"question": "进程和线程有什么区别？"},
        headers=headers,
    )
    assert response.status_code == 200
    stream = response.text
    assert "event: retrieval" in stream
    assert "event: citation" in stream
    assert "event: token" in stream
    assert "event: done" in stream
    assert "进程" in stream
    assert "INSUFFICIENT_CONTEXT" not in stream

    history = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
    assert history.status_code == 200
    messages = history.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[1]["citations_json"]
    assert len(messages[1]["citations_json"]) >= 1


def test_insufficient_context_does_not_generate_an_answer(client: TestClient) -> None:
    headers, course, _ = prepare_course(client)
    conversation = client.post(
        f"/api/courses/{course['id']}/conversations",
        json={"title": "资料外问题"},
        headers=headers,
    ).json()
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages",
        json={"question": "量子纠缠的贝尔不等式如何推导？"},
        headers=headers,
    )
    assert response.status_code == 200
    stream = response.text
    assert "INSUFFICIENT_CONTEXT" in stream
    assert "event: done" in stream

    history = client.get(f"/api/conversations/{conversation['id']}/messages", headers=headers)
    assert history.json()[1]["model_name"] == "none"

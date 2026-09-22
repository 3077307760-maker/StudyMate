from fastapi.testclient import TestClient

from tests.conftest import create_course, register, upload_markdown
from tests.test_documents_chat import CONTENT, prepare_course


def test_generate_submit_and_master_wrong_item(client: TestClient) -> None:
    headers, course, document = prepare_course(client)
    generated = client.post(
        f"/api/courses/{course['id']}/quizzes",
        json={
            "document_ids": [document["id"]],
            "question_count": 5,
            "question_types": ["single_choice", "short_answer"],
            "chapter": "进程与线程",
        },
        headers=headers,
    )
    assert generated.status_code == 201, generated.text
    quiz = generated.json()
    assert quiz["status"] == "ready"
    assert len(quiz["questions"]) == 5
    assert quiz["questions"][0]["options"] is not None

    wrong_answers = [
        {"question_id": question["id"], "answer": "B"} for question in quiz["questions"]
    ]
    failed = client.post(
        f"/api/quizzes/{quiz['id']}/submit",
        json={"answers": wrong_answers},
        headers=headers,
    )
    assert failed.status_code == 200
    assert failed.json()["score"] == 0

    wrong_book = client.get(f"/api/courses/{course['id']}/wrong-items", headers=headers)
    assert wrong_book.status_code == 200
    items = wrong_book.json()
    assert len(items) == 5
    assert all(item["wrong_count"] == 1 for item in items)
    single_choice = next(item for item in items if item["question"]["options"] is not None)

    for _ in range(2):
        corrected = client.post(
            f"/api/quizzes/{quiz['id']}/submit",
            json={"answers": [{"question_id": single_choice["question_id"], "answer": "A"}]},
            headers=headers,
        )
        assert corrected.status_code == 200

    updated = client.get(f"/api/courses/{course['id']}/wrong-items", headers=headers).json()
    mastered = next(item for item in updated if item["id"] == single_choice["id"])
    assert mastered["mastered"] is True
    assert mastered["consecutive_correct"] == 2

    review = client.get(f"/api/courses/{course['id']}/review-plan", headers=headers)
    assert review.status_code == 200
    plan = review.json()
    assert plan["total"] == 4
    assert all(task["completed"] is False for task in plan["tasks"])


def test_ten_question_quiz_is_supported(client: TestClient) -> None:
    headers = register(client, "owner@example.com", "Owner")
    course = create_course(client, headers)
    document = upload_markdown(client, headers, course["id"], CONTENT)
    response = client.post(
        f"/api/courses/{course['id']}/quizzes",
        json={
            "document_ids": [document["id"]],
            "question_count": 10,
            "question_types": ["single_choice"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert len(response.json()["questions"]) == 10

from fastapi.testclient import TestClient

from tests.conftest import create_course, register


def test_register_login_me_and_request_id(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "password123", "display_name": "Owner"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["request_id"].startswith("req_")
    assert response.headers["X-Request-ID"] == payload["request_id"]

    duplicate = client.post(
        "/api/auth/register",
        json={"email": "owner@example.com", "password": "password123", "display_name": "Owner"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "EMAIL_EXISTS"

    login = client.post(
        "/api/auth/login",
        json={"email": "owner@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    me = client.get("/api/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["display_name"] == "Owner"


def test_auth_and_course_permissions(client: TestClient) -> None:
    owner = register(client, "owner@example.com", "Owner")
    member = register(client, "member@example.com", "Member")
    outsider = register(client, "outsider@example.com", "Outsider")
    course = create_course(client, owner, "操作系统")

    joined = client.post(
        "/api/courses/join",
        json={"invite_code": course["invite_code"].lower()},
        headers=member,
    )
    assert joined.status_code == 200
    assert joined.json()["role"] == "member"

    forbidden = client.get(f"/api/courses/{course['id']}/documents", headers=outsider)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "FORBIDDEN"

    upload_as_member = client.post(
        f"/api/courses/{course['id']}/documents",
        files={"file": ("notes.md", b"content", "text/markdown")},
        headers=member,
    )
    assert upload_as_member.status_code == 403

    no_token = client.get("/api/me")
    assert no_token.status_code == 401
    assert no_token.json()["code"] == "AUTH_REQUIRED"

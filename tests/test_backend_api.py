from fastapi.testclient import TestClient

from backend.app import create_app


def _client(tmp_path):
    app = create_app(
        db_path=tmp_path / "backend.sqlite3",
        admin_usernames=["admin"],
    )
    return TestClient(app)


def _register(client, username="teacher_1", password="safe-password-123"):
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": password,
            "display_name": "Test Teacher",
            "email": f"{username}@example.org",
            "privacy_acknowledged": True,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data


def _review_payload():
    return {
        "essay_id": "TEST-BACKEND-001",
        "essay_text": (
            "Social media helps teenagers communicate with friends. "
            "However, it also make some students compare their lives with others too much."
        ),
        "assignment_prompt": "Write an opinion essay about social media.",
        "student_level": "upper-intermediate",
        "include_stress_tests": True,
    }


def test_backend_health_and_private_routes(tmp_path):
    client = _client(tmp_path)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["authentication"] == "enabled"
    assert "db_path" not in response.json()
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/teacher/decisions").status_code == 401
    assert client.get("/api/audit/logs").status_code == 401


def test_register_login_profile_and_password_change(tmp_path):
    client = _client(tmp_path)
    headers, registration = _register(client)

    assert registration["user"]["username"] == "teacher_1"
    assert registration["user"]["display_name"] == "Test Teacher"
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    duplicate = client.post(
        "/api/auth/register",
        json={
            "username": "teacher_1",
            "password": "another-password-123",
            "privacy_acknowledged": True,
        },
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        "/api/account/profile",
        headers=headers,
        json={"display_name": "Updated Teacher", "email": "updated@example.org"},
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["display_name"] == "Updated Teacher"

    changed = client.post(
        "/api/account/password",
        headers=headers,
        json={
            "current_password": "safe-password-123",
            "new_password": "new-safe-password-456",
        },
    )
    assert changed.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401

    old_login = client.post(
        "/api/auth/login",
        json={"username": "teacher_1", "password": "safe-password-123"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/auth/login",
        json={"username": "teacher_1", "password": "new-safe-password-456"},
    )
    assert new_login.status_code == 200


def test_single_review_persists_private_session_and_report(tmp_path):
    client = _client(tmp_path)
    headers, _ = _register(client)
    response = client.post("/api/review/single", headers=headers, json=_review_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"].startswith("rev-")
    assert data["summary"]["feedback_items"] == len(data["feedback_items"])
    assert all(item["session_id"] == data["session_id"] for item in data["feedback_items"])

    session = client.get(f"/api/sessions/{data['session_id']}", headers=headers)
    assert session.status_code == 200
    assert session.json()["essay_id"] == "TEST-BACKEND-001"

    report = client.get(f"/api/export/report/{data['session_id']}", headers=headers)
    assert report.status_code == 200
    assert "ConsensusScope ESL Writing Feedback Review Report" in report.text

    summary = client.get("/api/account/summary", headers=headers).json()["summary"]
    assert summary["review_sessions"] == 1
    assert summary["feedback_items"] == len(data["feedback_items"])


def test_user_cannot_read_another_users_review(tmp_path):
    client = _client(tmp_path)
    owner_headers, _ = _register(client, username="owner")
    other_headers, _ = _register(client, username="other")
    review = client.post(
        "/api/review/single",
        headers=owner_headers,
        json=_review_payload(),
    ).json()

    assert client.get(
        f"/api/sessions/{review['session_id']}",
        headers=other_headers,
    ).status_code == 404
    assert client.get("/api/sessions", headers=other_headers).json()["sessions"] == []
    assert client.delete(
        f"/api/sessions/{review['session_id']}",
        headers=other_headers,
    ).status_code == 404


def test_user_can_delete_own_review_and_related_records(tmp_path):
    client = _client(tmp_path)
    headers, _ = _register(client)
    review = client.post(
        "/api/review/single",
        headers=headers,
        json=_review_payload(),
    ).json()
    feedback_item_id = review["feedback_items"][0]["feedback_item_id"]
    decision = client.post(
        "/api/teacher/decision",
        headers=headers,
        json={
            "session_id": review["session_id"],
            "feedback_item_id": feedback_item_id,
            "teacher_action": "accept",
        },
    )
    assert decision.status_code == 200

    deleted = client.delete(
        f"/api/sessions/{review['session_id']}",
        headers=headers,
    )
    assert deleted.status_code == 200
    assert client.get(
        f"/api/sessions/{review['session_id']}",
        headers=headers,
    ).status_code == 404
    assert client.get(
        "/api/teacher/decisions",
        headers=headers,
        params={"session_id": review["session_id"]},
    ).json()["decisions"] == []
    assert client.get(
        "/api/audit/logs",
        headers=headers,
        params={"session_id": review["session_id"]},
    ).json()["logs"] == []
    summary = client.get("/api/account/summary", headers=headers).json()["summary"]
    assert summary["review_sessions"] == 0
    assert summary["feedback_items"] == 0
    assert summary["auto_accepted"] == 0
    assert summary["review_routed"] == 0
    assert summary["teacher_decisions"] == 0


def test_teacher_decision_validation_and_save(tmp_path):
    client = _client(tmp_path)
    headers, _ = _register(client)
    review = client.post(
        "/api/review/single",
        headers=headers,
        json=_review_payload(),
    ).json()
    feedback_item_id = review["feedback_items"][0]["feedback_item_id"]

    missing_edit = client.post(
        "/api/teacher/decision",
        headers=headers,
        json={
            "session_id": review["session_id"],
            "feedback_item_id": feedback_item_id,
            "teacher_action": "edit",
        },
    )
    assert missing_edit.status_code == 400

    saved = client.post(
        "/api/teacher/decision",
        headers=headers,
        json={
            "session_id": review["session_id"],
            "feedback_item_id": feedback_item_id,
            "teacher_action": "accept",
            "teacher_reason": "The local grammar correction is appropriate.",
            "teacher_id": "attempted_impersonation",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["decision"]["teacher_action"] == "accept"
    assert saved.json()["decision"]["teacher_id"] == "teacher_1"

    decisions = client.get(
        "/api/teacher/decisions",
        headers=headers,
        params={"session_id": review["session_id"]},
    )
    assert decisions.status_code == 200
    assert len(decisions.json()["decisions"]) == 1


def test_batch_review_creates_sessions(tmp_path):
    client = _client(tmp_path)
    headers, _ = _register(client)
    payload = {
        "include_stress_tests": False,
        "essays": [
            _review_payload(),
            {
                **_review_payload(),
                "essay_id": "TEST-BACKEND-002",
                "essay_text": "Online learning is convenient, but students need more feedback from teachers.",
            },
        ],
    }

    response = client.post("/api/review/batch", headers=headers, json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"].startswith("batch-")
    assert len(data["sessions"]) == 2
    assert data["feedback_items"]
    assert data["comparison"]
    assert data["report"]


def test_product_feedback_and_admin_inbox(tmp_path):
    client = _client(tmp_path)
    user_headers, _ = _register(client, username="teacher")
    admin_headers, admin = _register(client, username="admin")
    assert admin["user"]["is_admin"] is True

    submitted = client.post(
        "/api/feedback",
        headers=user_headers,
        json={
            "category": "usability",
            "rating": 4,
            "message": "The teacher queue would benefit from a compact filter.",
            "page": "Teacher Queue",
            "allow_contact": True,
        },
    )
    assert submitted.status_code == 201

    mine = client.get("/api/feedback/mine", headers=user_headers)
    assert len(mine.json()["feedback"]) == 1
    assert client.get("/api/admin/feedback", headers=user_headers).status_code == 403

    inbox = client.get("/api/admin/feedback", headers=admin_headers)
    assert inbox.status_code == 200
    assert inbox.json()["feedback"][0]["username"] == "teacher"

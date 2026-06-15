from fastapi.testclient import TestClient

from backend.app import create_app


def _client(tmp_path):
    app = create_app(db_path=tmp_path / "backend.sqlite3")
    return TestClient(app)


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


def test_backend_health(tmp_path):
    client = _client(tmp_path)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_single_review_persists_session_and_report(tmp_path):
    client = _client(tmp_path)
    response = client.post("/api/review/single", json=_review_payload())

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"].startswith("rev-")
    assert data["summary"]["feedback_items"] == len(data["feedback_items"])

    session = client.get(f"/api/sessions/{data['session_id']}")
    assert session.status_code == 200
    assert session.json()["essay_id"] == "TEST-BACKEND-001"

    report = client.get(f"/api/export/report/{data['session_id']}")
    assert report.status_code == 200
    assert "ConsensusScope ESL Writing Feedback Review Report" in report.text


def test_teacher_decision_validation_and_save(tmp_path):
    client = _client(tmp_path)
    review = client.post("/api/review/single", json=_review_payload()).json()
    feedback_item_id = review["feedback_items"][0]["feedback_item_id"]

    missing_edit = client.post(
        "/api/teacher/decision",
        json={
            "session_id": review["session_id"],
            "feedback_item_id": feedback_item_id,
            "teacher_action": "edit",
            "teacher_id": "teacher_1",
        },
    )
    assert missing_edit.status_code == 400

    saved = client.post(
        "/api/teacher/decision",
        json={
            "session_id": review["session_id"],
            "feedback_item_id": feedback_item_id,
            "teacher_action": "accept",
            "teacher_reason": "The local grammar correction is appropriate.",
            "teacher_id": "teacher_1",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["decision"]["teacher_action"] == "accept"

    decisions = client.get("/api/teacher/decisions", params={"session_id": review["session_id"]})
    assert decisions.status_code == 200
    assert len(decisions.json()["decisions"]) == 1


def test_batch_review_creates_sessions(tmp_path):
    client = _client(tmp_path)
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

    response = client.post("/api/review/batch", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["batch_id"].startswith("batch-")
    assert len(data["sessions"]) == 2
    assert data["feedback_items"]


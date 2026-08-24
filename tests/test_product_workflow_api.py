import time

from fastapi.testclient import TestClient

from backend.app import create_app


def _client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "product.sqlite3"))


def _register(client, username="teacher"):
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "safe-password-123",
            "display_name": "Test Teacher",
            "email": f"{username}@example.org",
            "privacy_acknowledged": True,
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_course_assignment(client, headers):
    course_response = client.post(
        "/api/courses",
        headers=headers,
        json={"name": "Academic Writing", "term": "Autumn 2026"},
    )
    assert course_response.status_code == 201, course_response.text
    course = course_response.json()["course"]
    assignment_response = client.post(
        "/api/assignments",
        headers=headers,
        json={
            "course_id": course["course_id"],
            "title": "Online Learning Essay",
            "prompt": "Write an opinion essay about online learning.",
            "student_level": "upper-intermediate",
        },
    )
    assert assignment_response.status_code == 201, assignment_response.text
    return course, assignment_response.json()["assignment"]


def _wait_for_job(client, headers, job_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = client.get(f"/api/review/jobs/{job_id}", headers=headers).json()["job"]
        if job["status"] in {"completed", "failed"}:
            return job
        time.sleep(0.02)
    raise AssertionError(f"review job {job_id} did not finish")


def test_course_assignment_essay_and_async_review_workflow(tmp_path):
    client = _client(tmp_path)
    headers = _register(client)
    course, assignment = _create_course_assignment(client, headers)

    essay_response = client.post(
        "/api/essays",
        headers=headers,
        json={
            "assignment_id": assignment["assignment_id"],
            "external_id": "ANON-001",
            "essay_text": (
                "Online learning give students more flexibility. "
                "However, teachers should provide clear feedback."
            ),
        },
    )
    assert essay_response.status_code == 201, essay_response.text
    essay = essay_response.json()["essay"]

    job_response = client.post(
        "/api/review/jobs",
        headers=headers,
        json={
            "assignment_id": assignment["assignment_id"],
            "essay_record_id": essay["essay_record_id"],
            "essay_id": essay["external_id"],
            "essay_text": essay["essay_text"],
            "assignment_prompt": assignment["prompt"],
            "student_level": essay["student_level"],
            "generation_mode": "local",
        },
    )
    assert job_response.status_code == 202, job_response.text
    job_id = job_response.json()["job"]["job_id"]
    job = _wait_for_job(client, headers, job_id)
    assert job["status"] == "completed"
    assert job["session_id"].startswith("rev-")
    assert job["assignment_id"] == assignment["assignment_id"]
    assert job["essay_record_id"] == essay["essay_record_id"]

    session = client.get(f"/api/sessions/{job['session_id']}", headers=headers).json()
    assert session["generation_mode"] == "local"
    assert session["assignment_id"] == assignment["assignment_id"]
    assert session["essay_record_id"] == essay["essay_record_id"]

    summary = client.get("/api/account/summary", headers=headers).json()["summary"]
    assert summary["courses"] == 1
    assert summary["assignments"] == 1
    assert summary["essays"] == 1
    assert summary["active_jobs"] == 0

    assert client.get("/api/courses", headers=headers).json()["courses"][0]["course_id"] == course["course_id"]
    assert client.get("/api/assignments", headers=headers).json()["assignments"][0]["assignment_id"] == assignment["assignment_id"]
    essay_list = client.get("/api/essays", headers=headers).json()["essays"]
    assert essay_list[0]["essay_record_id"] == essay["essay_record_id"]
    assert "essay_text" not in essay_list[0]
    essay_list_with_text = client.get(
        "/api/essays",
        headers=headers,
        params={"assignment_id": assignment["assignment_id"], "include_text": True},
    ).json()["essays"]
    assert essay_list_with_text[0]["essay_text"] == essay["essay_text"]


def test_private_workspace_records_are_isolated(tmp_path):
    client = _client(tmp_path)
    owner_headers = _register(client, "owner")
    other_headers = _register(client, "other")
    course, assignment = _create_course_assignment(client, owner_headers)

    assert client.get("/api/courses", headers=other_headers).json()["courses"] == []
    assert client.get(
        "/api/assignments",
        headers=other_headers,
        params={"course_id": course["course_id"]},
    ).json()["assignments"] == []
    foreign_assignment = client.post(
        "/api/essays",
        headers=other_headers,
        json={
            "assignment_id": assignment["assignment_id"],
            "external_id": "ANON-002",
            "essay_text": "Online learning offers flexibility but also requires self discipline.",
        },
    )
    assert foreign_assignment.status_code == 404


def test_pii_check_blocks_identifiable_student_text(tmp_path):
    client = _client(tmp_path)
    headers = _register(client)
    _, assignment = _create_course_assignment(client, headers)
    text = "Student email: learner@example.org. I prefer online learning."

    check = client.post("/api/privacy/check", headers=headers, json={"text": text})
    assert check.status_code == 200
    assert check.json()["safe_to_submit"] is False
    assert any(item["type"] == "email" for item in check.json()["findings"])

    upload = client.post(
        "/api/essays",
        headers=headers,
        json={
            "assignment_id": assignment["assignment_id"],
            "external_id": "ANON-003",
            "essay_text": text,
        },
    )
    assert upload.status_code == 400

    ordinary_classroom_language = client.post(
        "/api/privacy/check",
        headers=headers,
        json={"text": "The class is useful because students can discuss difficult ideas."},
    )
    assert ordinary_classroom_language.json()["safe_to_submit"] is True


def test_student_report_contains_only_teacher_released_feedback(tmp_path):
    client = _client(tmp_path)
    headers = _register(client)
    review = client.post(
        "/api/review/single",
        headers=headers,
        json={
            "essay_id": "ANON-REPORT-001",
            "essay_text": "Online learning give students flexibility, but it also create isolation.",
            "assignment_prompt": "Write about online learning.",
            "student_level": "intermediate",
            "include_stress_tests": True,
        },
    ).json()
    items = review["feedback_items"]
    accepted = items[0]
    edited = items[1]
    rejected = items[2]

    for item, action, correction in (
        (accepted, "accept", None),
        (edited, "edit", "Use a clearer transition between these ideas."),
        (rejected, "reject", None),
    ):
        response = client.post(
            "/api/teacher/decision",
            headers=headers,
            json={
                "session_id": review["session_id"],
                "feedback_item_id": item["feedback_item_id"],
                "teacher_action": action,
                "teacher_corrected_feedback": correction,
                "teacher_reason": "Reviewed by the teacher.",
            },
        )
        assert response.status_code == 200, response.text

    report = client.get(
        f"/api/export/student-report/{review['session_id']}",
        headers=headers,
    )
    assert report.status_code == 200
    assert accepted["ai_suggestion"] in report.text
    assert "Use a clearer transition between these ideas." in report.text
    assert rejected["ai_suggestion"] not in report.text


def test_account_export_and_delete_are_complete(tmp_path):
    client = _client(tmp_path)
    headers = _register(client)
    _create_course_assignment(client, headers)

    exported = client.get("/api/account/export", headers=headers)
    assert exported.status_code == 200
    account_data = exported.json()["account_data"]
    assert account_data["user"]["username"] == "teacher"
    assert "password_hash" not in account_data["user"]
    assert len(account_data["courses"]) == 1
    assert len(account_data["assignments"]) == 1

    wrong_confirmation = client.request(
        "DELETE",
        "/api/account",
        headers=headers,
        json={"password": "safe-password-123", "confirmation": "NO"},
    )
    assert wrong_confirmation.status_code == 422
    deleted = client.request(
        "DELETE",
        "/api/account",
        headers=headers,
        json={"password": "safe-password-123", "confirmation": "DELETE"},
    )
    assert deleted.status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401

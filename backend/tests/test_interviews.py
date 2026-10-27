"""面试会话端点测试。"""

from __future__ import annotations

import uuid

from app.models.prediction import PredictedQuestion, Prediction
from app.models.user import User


def _login(client, user: dict) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


def _make_prediction(db_session, owner_id) -> Prediction:
    """插入一份包含两道题的押题记录。"""
    prediction = Prediction(
        owner_id=owner_id,
        resume_id=uuid.uuid4(),  # 仅作为关联标记，测试不涉及简历外键校验
        target_role="Python 后端工程师",
        years_of_experience="3-5年",
        job_description="负责后端开发",
        status="completed",
        model_name="deepseek-chat",
        prompt_version="prediction-v1",
        generated_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        questions=[
            PredictedQuestion(
                position=1,
                question="什么是 FastAPI 的依赖注入？",
                difficulty="medium",
                reference_answer="要点：Depends 机制。",
                evidence=[{"source": "resume", "ref": "简历", "excerpt": "FastAPI"}],
            ),
            PredictedQuestion(
                position=2,
                question="如何设计一个高并发接口？",
                difficulty="hard",
                reference_answer="要点：缓存、限流、异步。",
                evidence=[{"source": "job_description", "ref": "岗位描述", "excerpt": "高并发"}],
            ),
        ],
    )
    db_session.add(prediction)
    db_session.commit()
    return prediction


def _start(client, prediction_id: str) -> dict:
    response = client.post("/api/v1/interviews", json={"prediction_id": prediction_id})
    assert response.status_code == 201, response.text
    return response.json()


class TestStartInterview:
    def test_requires_auth(self, client) -> None:
        assert (
            client.post("/api/v1/interviews", json={"prediction_id": str(uuid.uuid4())}).status_code
            == 401
        )

    def test_start_success_with_first_question(
        self, client, db_session, registered_user
    ) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        result = _start(client, str(prediction.id))

        assert result["interview"]["status"] == "ongoing"
        assert result["interview"]["total_questions"] == 2
        assert result["interview"]["current_position"] == 1
        assert len(result["questions"]) == 2
        # 首条面试官消息即第一题
        assert result["interview"]["messages"][0]["role"] == "interviewer"
        assert result["interview"]["messages"][0]["content"].startswith("什么是")

    def test_start_with_unknown_prediction_returns_404(
        self, client, registered_user
    ) -> None:
        _login(client, registered_user)
        response = client.post("/api/v1/interviews", json={"prediction_id": str(uuid.uuid4())})
        assert response.status_code == 404

    def test_start_with_others_prediction_returns_404(
        self, client, db_session, registered_user
    ) -> None:
        _login(client, registered_user)
        other = User(email="other-x@example.com", password_hash="x", email_verified=False)
        db_session.add(other)
        db_session.commit()
        prediction = _make_prediction(db_session, other.id)

        response = client.post("/api/v1/interviews", json={"prediction_id": str(prediction.id)})
        assert response.status_code == 404

    def test_duplicate_ongoing_rejected(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        _start(client, str(prediction.id))

        response = client.post("/api/v1/interviews", json={"prediction_id": str(prediction.id)})
        assert response.status_code == 409
        assert response.json()["code"] == "INTERVIEW_ALREADY_ONGOING"


class TestAnswerFlow:
    def test_answer_advances_and_completes(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]

        first = client.post(
            f"/api/v1/interviews/{interview_id}/answer", json={"content": "Depends 装饰器实现"}
        ).json()
        assert first["finished"] is False
        assert first["interview"]["current_position"] == 2
        # 第二题面试官消息已写入
        roles = [(m["role"], m["position"]) for m in first["interview"]["messages"]]
        assert ("answerer", 1) in roles
        assert ("interviewer", 2) in roles

        final = client.post(
            f"/api/v1/interviews/{interview_id}/answer", json={"content": "缓存与限流"}
        ).json()
        assert final["finished"] is True
        assert final["interview"]["status"] == "completed"
        assert final["interview"]["finished_at"] is not None

    def test_blank_answer_rejected(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))

        response = client.post(
            f"/api/v1/interviews/{started['interview']['id']}/answer", json={"content": "   "}
        )
        assert response.status_code == 422

    def test_answer_after_completion_rejected(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]
        client.post(f"/api/v1/interviews/{interview_id}/answer", json={"content": "回答一"})
        client.post(f"/api/v1/interviews/{interview_id}/answer", json={"content": "回答二"})

        response = client.post(
            f"/api/v1/interviews/{interview_id}/answer", json={"content": "再来一次"}
        )
        assert response.status_code == 409
        assert response.json()["code"] == "INTERVIEW_NOT_ONGOING"


class TestSkipFlow:
    def test_skip_marks_and_advances(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]

        result = client.post(f"/api/v1/interviews/{interview_id}/skip").json()
        assert result["finished"] is False
        assert result["interview"]["current_position"] == 2
        skipped_msgs = [m for m in result["interview"]["messages"] if m["skipped"]]
        assert len(skipped_msgs) == 1
        assert skipped_msgs[0]["position"] == 1
        assert skipped_msgs[0]["content"] is None

    def test_skip_last_question_completes(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]
        client.post(f"/api/v1/interviews/{interview_id}/answer", json={"content": "第一题回答"})

        result = client.post(f"/api/v1/interviews/{interview_id}/skip").json()
        assert result["finished"] is True
        assert result["interview"]["status"] == "completed"


class TestListAndAbandon:
    def test_list_only_own_interviews(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        _start(client, str(prediction.id))

        items = client.get("/api/v1/interviews").json()
        assert len(items) == 1
        assert items[0]["answered_count"] == 0

    def test_abandon_then_answer_rejected(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]

        assert (
            client.post(f"/api/v1/interviews/{interview_id}/abandon").status_code == 204
        )
        response = client.post(
            f"/api/v1/interviews/{interview_id}/answer", json={"content": "晚了"}
        )
        assert response.status_code == 409

        # 放弃后可重新发起
        restart = client.post(
            "/api/v1/interviews", json={"prediction_id": str(prediction.id)}
        )
        assert restart.status_code == 201

    def test_others_interview_not_visible(self, client, db_session, registered_user) -> None:
        _login(client, registered_user)
        prediction = _make_prediction(db_session, uuid.UUID(registered_user["id"]))
        started = _start(client, str(prediction.id))
        interview_id = started["interview"]["id"]

        other_email = f"other-{uuid.uuid4().hex[:6]}@example.com"
        client.post("/api/v1/auth/register", json={"email": other_email, "password": "Passw0rd1"})
        _login(client, {"email": other_email, "password": "Passw0rd1"})

        assert client.get(f"/api/v1/interviews/{interview_id}").status_code == 404
        assert client.get("/api/v1/interviews").json() == []

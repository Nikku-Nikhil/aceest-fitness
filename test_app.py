"""
test_app.py  –  ACEest Fitness & Gym
======================================
Tests map directly to the business logic from the tkinter desktop app
(Aceestver 1.0 → 3.2.4), now running as a Flask REST API.

Run:  pytest -v --cov=app --cov-report=term-missing
"""

import json
import pytest
from app import app, init_db, calculate_bmi, calculate_calories, generate_ai_program, PROGRAMS, WORKOUT_TYPES


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Redirect DB to a temp file so each test gets a clean slate."""
    import app as app_module
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(app_module, "DB_NAME", db_path)
    with app.app_context():
        init_db()
    yield


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def saved_client(client):
    """Convenience: POST a client and return the response JSON."""
    payload = {
        "name": "Ravi Sharma",
        "age": 28,
        "height": 175.0,
        "weight": 72.0,
        "program": "Fat Loss (FL) – 3 day",
    }
    res = client.post("/clients",
                      data=json.dumps(payload),
                      content_type="application/json")
    assert res.status_code == 201
    return res.get_json()


# ─────────────────────────────────────────────
# Unit tests – pure Python helpers
# ─────────────────────────────────────────────

class TestCalculateCalories:
    """From your ACEestApp.save_client() calorie calculation: weight × factor."""

    def test_fat_loss_3day(self):
        # 72 kg × factor 22 = 1584
        assert calculate_calories(72.0, "Fat Loss (FL) – 3 day") == 1584

    def test_muscle_gain_ppl(self):
        # 80 kg × factor 35 = 2800
        assert calculate_calories(80.0, "Muscle Gain (MG) – PPL") == 2800

    def test_beginner(self):
        assert calculate_calories(65.0, "Beginner (BG)") == int(65 * 26)

    def test_fat_loss_5day(self):
        assert calculate_calories(70.0, "Fat Loss (FL) – 5 day") == int(70 * 24)

    def test_invalid_program_raises(self):
        with pytest.raises(ValueError, match="Unknown program"):
            calculate_calories(70.0, "Zumba")

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError):
            calculate_calories(0, "Beginner (BG)")


class TestCalculateBMI:
    """From your show_bmi_info() method in versions 3.x."""

    def test_normal_bmi(self):
        result = calculate_bmi(72, 175)
        assert result["bmi"] == 23.5
        assert result["category"] == "Normal"

    def test_underweight(self):
        result = calculate_bmi(45, 170)
        assert result["category"] == "Underweight"

    def test_overweight(self):
        result = calculate_bmi(85, 170)
        assert result["category"] == "Overweight"

    def test_obese(self):
        result = calculate_bmi(120, 170)
        assert result["category"] == "Obese"

    def test_risk_note_present(self):
        result = calculate_bmi(72, 175)
        assert "risk_note" in result

    def test_invalid_height_raises(self):
        with pytest.raises(ValueError):
            calculate_bmi(70, 0)

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError):
            calculate_bmi(-5, 170)


class TestGenerateAIProgram:
    """From your generate_ai_program() in version 3.2.4 / ACEestFull."""

    def test_beginner_has_3_days(self):
        plan = generate_ai_program("Beginner (BG)", "beginner")
        days = {row["day"] for row in plan}
        assert len(days) == 3

    def test_intermediate_has_4_days(self):
        plan = generate_ai_program("Fat Loss (FL) – 3 day", "intermediate")
        days = {row["day"] for row in plan}
        assert len(days) == 4

    def test_advanced_has_5_days(self):
        plan = generate_ai_program("Muscle Gain (MG) – PPL", "advanced")
        days = {row["day"] for row in plan}
        assert len(days) == 5

    def test_plan_contains_required_keys(self):
        plan = generate_ai_program("Beginner (BG)", "beginner")
        for row in plan:
            assert {"day", "exercise", "sets", "reps"}.issubset(row.keys())

    def test_invalid_experience_raises(self):
        with pytest.raises(ValueError, match="Experience must be"):
            generate_ai_program("Beginner (BG)", "expert")

    def test_deterministic_with_seed(self):
        p1 = generate_ai_program("Beginner (BG)", "beginner", seed=99)
        p2 = generate_ai_program("Beginner (BG)", "beginner", seed=99)
        assert p1 == p2


# ─────────────────────────────────────────────
# Integration tests – HTTP endpoints
# ─────────────────────────────────────────────

class TestHomeAndHealth:
    def test_home_200(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.get_json()["gym"] == "ACEest Fitness & Gym"

    def test_health_200(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.get_json()["status"] == "healthy"


class TestPrograms:
    def test_list_programs_returns_all_4(self, client):
        res = client.get("/programs")
        assert res.status_code == 200
        data = res.get_json()
        assert len(data["programs"]) == 4

    def test_all_programs_have_factor_and_desc(self, client):
        res = client.get("/programs")
        for prog in res.get_json()["programs"]:
            assert "factor" in prog
            assert "desc" in prog


class TestClientEndpoints:
    """Mirrors save_client / load_client from your tkinter app."""

    def test_save_client_success(self, client):
        payload = {"name": "Priya Mehta", "age": 25, "weight": 60.0,
                   "height": 162.0, "program": "Beginner (BG)"}
        res = client.post("/clients", data=json.dumps(payload),
                          content_type="application/json")
        assert res.status_code == 201
        data = res.get_json()
        assert data["name"] == "Priya Mehta"
        assert data["calories"] == int(60.0 * 26)

    def test_save_client_missing_name_returns_400(self, client):
        res = client.post("/clients",
                          data=json.dumps({"program": "Beginner (BG)"}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_save_client_invalid_program_returns_400(self, client):
        res = client.post("/clients",
                          data=json.dumps({"name": "X", "program": "Zumba"}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_get_all_clients(self, client, saved_client):
        res = client.get("/clients")
        assert res.status_code == 200
        assert res.get_json()["count"] == 1

    def test_get_client_by_name(self, client, saved_client):
        res = client.get("/clients/Ravi Sharma")
        assert res.status_code == 200
        assert res.get_json()["name"] == "Ravi Sharma"

    def test_get_nonexistent_client_404(self, client):
        res = client.get("/clients/Ghost User")
        assert res.status_code == 404

    def test_calories_calculated_on_save(self, client, saved_client):
        # 72 kg × factor 22 (Fat Loss 3 day) = 1584
        assert saved_client["calories"] == 1584


class TestProgressEndpoints:
    """Mirrors save_progress() from your tkinter app."""

    def test_save_progress_success(self, client, saved_client):
        res = client.post("/clients/Ravi Sharma/progress",
                          data=json.dumps({"adherence": 85}),
                          content_type="application/json")
        assert res.status_code == 201
        data = res.get_json()
        assert data["adherence"] == 85

    def test_save_progress_missing_adherence_400(self, client, saved_client):
        res = client.post("/clients/Ravi Sharma/progress",
                          data=json.dumps({}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_save_progress_invalid_adherence_400(self, client, saved_client):
        res = client.post("/clients/Ravi Sharma/progress",
                          data=json.dumps({"adherence": 150}),
                          content_type="application/json")
        assert res.status_code == 400

    def test_get_progress_history(self, client, saved_client):
        client.post("/clients/Ravi Sharma/progress",
                    data=json.dumps({"adherence": 70}), content_type="application/json")
        client.post("/clients/Ravi Sharma/progress",
                    data=json.dumps({"adherence": 90}), content_type="application/json")
        res = client.get("/clients/Ravi Sharma/progress")
        assert res.status_code == 200
        data = res.get_json()
        assert data["weeks_logged"] == 2
        assert data["average_adherence"] == 80.0

    def test_progress_for_missing_client_404(self, client):
        res = client.post("/clients/Nobody/progress",
                          data=json.dumps({"adherence": 50}),
                          content_type="application/json")
        assert res.status_code == 404


class TestWorkoutEndpoints:
    """Mirrors add_workout / log_workout from your tkinter app."""

    def test_log_workout_success(self, client, saved_client):
        payload = {
            "date": "2026-04-01",
            "workout_type": "Strength",
            "duration_min": 60,
            "notes": "Squat PR today",
            "exercises": [{"name": "Squat", "sets": 5, "reps": 5, "weight": 100}],
        }
        res = client.post("/clients/Ravi Sharma/workouts",
                          data=json.dumps(payload), content_type="application/json")
        assert res.status_code == 201
        assert res.get_json()["type"] == "Strength"

    def test_log_workout_invalid_type_400(self, client, saved_client):
        payload = {"workout_type": "Zumba", "duration_min": 30}
        res = client.post("/clients/Ravi Sharma/workouts",
                          data=json.dumps(payload), content_type="application/json")
        assert res.status_code == 400

    def test_get_workouts_list(self, client, saved_client):
        client.post("/clients/Ravi Sharma/workouts",
                    data=json.dumps({"workout_type": "Conditioning", "duration_min": 45}),
                    content_type="application/json")
        res = client.get("/clients/Ravi Sharma/workouts")
        assert res.status_code == 200
        assert res.get_json()["count"] == 1

    def test_workout_for_missing_client_404(self, client):
        res = client.post("/clients/Nobody/workouts",
                          data=json.dumps({"workout_type": "Strength"}),
                          content_type="application/json")
        assert res.status_code == 404


class TestBMIEndpoint:
    """Mirrors show_bmi_info from your tkinter app (version 3.x)."""

    def test_bmi_valid(self, client):
        res = client.get("/bmi?weight=72&height=175")
        assert res.status_code == 200
        data = res.get_json()
        assert data["bmi"] == 23.5
        assert data["category"] == "Normal"

    def test_bmi_missing_params_400(self, client):
        res = client.get("/bmi?weight=72")
        assert res.status_code == 400

    def test_bmi_invalid_values_400(self, client):
        res = client.get("/bmi?weight=0&height=170")
        assert res.status_code == 400


class TestAIProgramEndpoint:
    """Mirrors generate_ai_program from your version 3.2.4."""

    def test_ai_program_beginner(self, client, saved_client):
        res = client.get("/clients/Ravi Sharma/ai-program?experience=beginner")
        assert res.status_code == 200
        data = res.get_json()
        assert len({row["day"] for row in data["plan"]}) == 3

    def test_ai_program_invalid_experience_400(self, client, saved_client):
        res = client.get("/clients/Ravi Sharma/ai-program?experience=expert")
        assert res.status_code == 400

    def test_ai_program_missing_client_404(self, client):
        res = client.get("/clients/Nobody/ai-program")
        assert res.status_code == 404


class TestMembershipEndpoint:
    """Mirrors check_membership from your ACEestFull version."""

    def test_membership_status(self, client, saved_client):
        res = client.get("/clients/Ravi Sharma/membership")
        assert res.status_code == 200
        data = res.get_json()
        assert data["membership_status"] == "Active"

    def test_membership_missing_client_404(self, client):
        res = client.get("/clients/Nobody/membership")
        assert res.status_code == 404

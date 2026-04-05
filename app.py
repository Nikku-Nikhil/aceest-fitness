"""
app.py  –  ACEest Fitness & Gym  (Flask REST API)
===================================================
Business logic extracted from the tkinter desktop app (Aceestver 1.0 → 3.2.4).

Key domain concepts preserved from your files:
  • Three fitness programs: Fat Loss (FL), Muscle Gain (MG), Beginner (BG)
    with their calorie factors (22 / 35 / 26 kcal per kg)
  • Client management  (save / load / list)
  • Weekly adherence progress logging
  • Workout session logging (type, duration, notes)
  • Body metrics logging (weight, waist, bodyfat)
  • BMI calculator with risk category
  • Membership status check
  • AI program generator (deterministic for testability)
"""

import sqlite3
import random
from datetime import date, datetime
from flask import Flask, jsonify, request, abort, g

app = Flask(__name__)
DB_NAME = "aceest_fitness.db"

# ─────────────────────────────────────────────
# Domain constants  (from your setup_data / programs dict)
# ─────────────────────────────────────────────

PROGRAMS = {
    "Fat Loss (FL) – 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) – 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) – PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)":          {"factor": 26, "desc": "3-day simple beginner full-body"},
}

WORKOUT_TYPES = ["Strength", "Hypertrophy", "Conditioning", "Mixed", "Mobility"]

EXERCISE_POOL = {
    "Strength":     ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": [
        "Leg Press", "Incline Dumbbell Press", "Lat Pulldown",
        "Lateral Raise", "Bicep Curl", "Tricep Extension",
    ],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope", "Kettlebell Swings"],
    "Full Body":    ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}

# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────


def get_db():
    """Return a per-request SQLite connection (stored on Flask's g object)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_NAME)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    with app.app_context():
        db = get_db()
        db.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                age INTEGER,
                height REAL,
                weight REAL,
                program TEXT,
                calories INTEGER,
                target_weight REAL,
                target_adherence INTEGER,
                membership_status TEXT DEFAULT 'Active',
                membership_end TEXT
            );

            CREATE TABLE IF NOT EXISTS progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                week TEXT,
                adherence INTEGER
            );

            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                date TEXT,
                workout_type TEXT,
                duration_min INTEGER,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER,
                name TEXT,
                sets INTEGER,
                reps INTEGER,
                weight REAL
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                date TEXT,
                weight REAL,
                waist REAL,
                bodyfat REAL
            );
        """)
        db.commit()

# ─────────────────────────────────────────────
# Pure business-logic helpers  (easily unit-tested)
# ─────────────────────────────────────────────


def calculate_calories(weight_kg: float, program_name: str) -> int:
    """Return estimated daily kcal target (weight × program factor)."""
    if program_name not in PROGRAMS:
        raise ValueError(f"Unknown program: '{program_name}'. Valid: {list(PROGRAMS)}")
    if weight_kg <= 0:
        raise ValueError("Weight must be a positive number.")
    return int(weight_kg * PROGRAMS[program_name]["factor"])


def calculate_bmi(weight_kg: float, height_cm: float) -> dict:
    """Return BMI value and WHO risk category."""
    if height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Weight and height must be positive.")
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m ** 2), 1)
    if bmi < 18.5:
        category, risk = "Underweight", "Potential nutrient deficiency, low energy."
    elif bmi < 25:
        category, risk = "Normal", "Low risk if active and strong."
    elif bmi < 30:
        category, risk = "Overweight", "Moderate risk; focus on adherence and progressive activity."
    else:
        category, risk = "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."
    return {"bmi": bmi, "category": category, "risk_note": risk}


def generate_ai_program(program_name: str, experience: str, seed: int = 42) -> list:
    """
    Deterministic AI-style weekly workout generator.
    Mirrors the logic from your generate_ai_program / generate_program methods.
    Uses a fixed seed so tests are reproducible.
    """
    valid_exp = ("beginner", "intermediate", "advanced")
    if experience.lower() not in valid_exp:
        raise ValueError(f"Experience must be one of {valid_exp}.")

    # Choose exercise pool based on program goal
    if "Fat Loss" in program_name:
        focus = "Conditioning"
    elif "Muscle Gain" in program_name:
        focus = "Hypertrophy"
    else:
        focus = "Full Body"

    exp = experience.lower()
    if exp == "beginner":
        sets_r, reps_r, days = (2, 3), (8, 12), 3
    elif exp == "intermediate":
        sets_r, reps_r, days = (3, 4), (8, 15), 4
    else:
        sets_r, reps_r, days = (4, 5), (6, 15), 5

    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][:days]
    rng = random.Random(seed)
    pool = EXERCISE_POOL[focus]

    plan = []
    for day in day_names:
        exercises = rng.sample(pool, k=min(3 if days < 4 else 4, len(pool)))
        for ex in exercises:
            plan.append({
                "day": day,
                "exercise": ex,
                "sets": rng.randint(*sets_r),
                "reps": rng.randint(*reps_r),
            })
    return plan

# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────


@app.route("/", methods=["GET"])
def home():
    return jsonify({"gym": "ACEest Fitness & Gym", "status": "operational"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/programs", methods=["GET"])
def list_programs():
    return jsonify({"programs": [{"name": k, **v} for k, v in PROGRAMS.items()]})


# ── Clients ──────────────────────────────────

@app.route("/clients", methods=["GET"])
def get_clients():
    db = get_db()
    rows = db.execute("SELECT * FROM clients ORDER BY name").fetchall()
    return jsonify({"count": len(rows), "clients": [dict(r) for r in rows]})


@app.route("/clients/<string:name>", methods=["GET"])
def get_client(name):
    db = get_db()
    row = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    if not row:
        abort(404, description=f"Client '{name}' not found.")
    return jsonify(dict(row))


@app.route("/clients", methods=["POST"])
def save_client():
    """Mirrors save_client() from your tkinter app."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    program = data.get("program", "")
    age = data.get("age")
    height = data.get("height")
    weight = data.get("weight")
    membership_status = data.get("membership_status", "Active")
    membership_end = data.get("membership_end")
    target_weight = data.get("target_weight")
    target_adherence = data.get("target_adherence")

    if not name:
        abort(400, description="Field 'name' is required.")
    if program and program not in PROGRAMS:
        abort(400, description=f"Invalid program. Choose from: {list(PROGRAMS)}")

    calories = None
    if weight and program:
        try:
            calories = calculate_calories(float(weight), program)
        except ValueError as e:
            abort(400, description=str(e))

    db = get_db()
    try:
        db.execute(
            """INSERT OR REPLACE INTO clients
               (name, age, height, weight, program, calories,
                target_weight, target_adherence, membership_status, membership_end)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (name, age, height, weight, program, calories,
             target_weight, target_adherence, membership_status, membership_end),
        )
        db.commit()
    except Exception as e:
        abort(500, description=str(e))

    row = db.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
    return jsonify(dict(row)), 201


# ── Progress ─────────────────────────────────

@app.route("/clients/<string:name>/progress", methods=["POST"])
def save_progress(name):
    """Mirrors save_progress() from your tkinter app."""
    db = get_db()
    if not db.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
        abort(404, description=f"Client '{name}' not found.")

    data = request.get_json(silent=True) or {}
    adherence = data.get("adherence")
    if adherence is None:
        abort(400, description="Field 'adherence' (0-100) is required.")
    try:
        adherence = int(adherence)
        assert 0 <= adherence <= 100
    except (ValueError, AssertionError):
        abort(400, description="'adherence' must be an integer between 0 and 100.")

    week = datetime.now().strftime("Week %U - %Y")
    db.execute(
        "INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
        (name, week, adherence),
    )
    db.commit()
    return jsonify({"client": name, "week": week, "adherence": adherence}), 201


@app.route("/clients/<string:name>/progress", methods=["GET"])
def get_progress(name):
    db = get_db()
    if not db.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
        abort(404, description=f"Client '{name}' not found.")
    rows = db.execute(
        "SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
        (name,),
    ).fetchall()
    avg = round(sum(r["adherence"] for r in rows) / len(rows), 1) if rows else 0
    return jsonify({"client": name, "weeks_logged": len(rows),
                    "average_adherence": avg, "history": [dict(r) for r in rows]})


# ── Workouts ─────────────────────────────────

@app.route("/clients/<string:name>/workouts", methods=["POST"])
def log_workout(name):
    """Mirrors add_workout / open_log_workout_window from your tkinter app."""
    db = get_db()
    if not db.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
        abort(404, description=f"Client '{name}' not found.")

    data = request.get_json(silent=True) or {}
    workout_type = data.get("workout_type", "")
    duration = data.get("duration_min", 60)
    workout_date = data.get("date", date.today().isoformat())
    notes = data.get("notes", "")
    exercises = data.get("exercises", [])   # list of {name, sets, reps, weight}

    if workout_type not in WORKOUT_TYPES:
        abort(400, description=f"workout_type must be one of {WORKOUT_TYPES}.")

    db.execute(
        "INSERT INTO workouts (client_name, date, workout_type, duration_min, notes) VALUES (?,?,?,?,?)",
        (name, workout_date, workout_type, duration, notes),
    )
    workout_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

    for ex in exercises:
        db.execute(
            "INSERT INTO exercises (workout_id, name, sets, reps, weight) VALUES (?,?,?,?,?)",
            (workout_id, ex.get("name"), ex.get("sets"), ex.get("reps"), ex.get("weight", 0)),
        )
    db.commit()
    return jsonify({"workout_id": workout_id, "client": name,
                    "date": workout_date, "type": workout_type}), 201


@app.route("/clients/<string:name>/workouts", methods=["GET"])
def get_workouts(name):
    db = get_db()
    if not db.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
        abort(404, description=f"Client '{name}' not found.")
    rows = db.execute(
        "SELECT * FROM workouts WHERE client_name=? ORDER BY date DESC, id DESC",
        (name,),
    ).fetchall()
    return jsonify({"client": name, "count": len(rows),
                    "workouts": [dict(r) for r in rows]})


# ── Body Metrics ─────────────────────────────

@app.route("/clients/<string:name>/metrics", methods=["POST"])
def log_metrics(name):
    """Mirrors open_log_metrics_window from your tkinter app."""
    db = get_db()
    if not db.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
        abort(404, description=f"Client '{name}' not found.")

    data = request.get_json(silent=True) or {}
    metric_date = data.get("date", date.today().isoformat())
    weight = data.get("weight")
    waist = data.get("waist")
    bodyfat = data.get("bodyfat")

    if not metric_date:
        abort(400, description="Field 'date' is required.")

    db.execute(
        "INSERT INTO metrics (client_name, date, weight, waist, bodyfat) VALUES (?,?,?,?,?)",
        (name, metric_date, weight, waist, bodyfat),
    )
    db.commit()
    return jsonify({"client": name, "date": metric_date,
                    "weight": weight, "waist": waist, "bodyfat": bodyfat}), 201


# ── BMI ──────────────────────────────────────

@app.route("/bmi", methods=["GET"])
def bmi():
    """Mirrors show_bmi_info from your tkinter app."""
    try:
        weight = float(request.args["weight"])
        height = float(request.args["height"])
    except KeyError:
        abort(400, description="Query params 'weight' (kg) and 'height' (cm) are required.")
    except ValueError:
        abort(400, description="'weight' and 'height' must be numbers.")
    try:
        return jsonify(calculate_bmi(weight, height))
    except ValueError as e:
        abort(400, description=str(e))


# ── AI Program Generator ──────────────────────

@app.route("/clients/<string:name>/ai-program", methods=["GET"])
def ai_program(name):
    """Mirrors generate_ai_program from your tkinter app."""
    db = get_db()
    row = db.execute("SELECT program FROM clients WHERE name=?", (name,)).fetchone()
    if not row:
        abort(404, description=f"Client '{name}' not found.")
    if not row["program"]:
        abort(400, description="Client has no program assigned. Save client with a program first.")

    experience = request.args.get("experience", "beginner")
    try:
        plan = generate_ai_program(row["program"], experience)
    except ValueError as e:
        abort(400, description=str(e))
    return jsonify({"client": name, "program": row["program"],
                    "experience": experience, "plan": plan})


# ── Membership ────────────────────────────────

@app.route("/clients/<string:name>/membership", methods=["GET"])
def membership(name):
    """Mirrors check_membership from your tkinter app."""
    db = get_db()
    row = db.execute(
        "SELECT membership_status, membership_end FROM clients WHERE name=?", (name,)
    ).fetchone()
    if not row:
        abort(404, description=f"Client '{name}' not found.")
    return jsonify({"client": name, "membership_status": row["membership_status"],
                    "membership_end": row["membership_end"]})


# ─────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad Request", "message": e.description}), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not Found", "message": e.description}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal Server Error", "message": e.description}), 500


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=False)

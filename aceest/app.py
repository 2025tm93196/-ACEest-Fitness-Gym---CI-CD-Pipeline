"""ACEest Fitness & Gym - Flask service.

Web port of the Tkinter desktop application (versions 1.0 -> 3.2.4).
Business rules (programs, calorie factors, BMI, adherence) are kept
identical to the desktop versions.
"""
import os
import sqlite3
from datetime import datetime

from flask import Flask, jsonify, request

PROGRAMS = {
    "Fat Loss (FL) - 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) - 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) - PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER, height REAL, weight REAL,
    program TEXT, calories INTEGER,
    target_weight REAL, target_adherence INTEGER
);
CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT, week TEXT, adherence INTEGER
);
CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT, date TEXT, workout_type TEXT,
    duration_min INTEGER, notes TEXT
);
"""


def calculate_calories(weight, program):
    """Daily calorie target = weight (kg) x program factor."""
    if program not in PROGRAMS:
        raise ValueError("Unknown program: %s" % program)
    if weight is None or weight <= 0:
        raise ValueError("Weight must be greater than zero")
    return int(weight * PROGRAMS[program]["factor"])


def calculate_bmi(height_cm, weight_kg):
    """Return (bmi, category, risk_note); height in cm, weight in kg."""
    if height_cm is None or weight_kg is None or height_cm <= 0 or weight_kg <= 0:
        raise ValueError("Height and weight must be greater than zero")
    h_m = height_cm / 100.0
    bmi = round(weight_kg / (h_m * h_m), 1)
    if bmi < 18.5:
        return bmi, "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return bmi, "Normal", "Low risk if active and strong."
    if bmi < 30:
        return bmi, "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return bmi, "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("ACEEST_DB", "aceest_fitness.db")

    def get_db():
        conn = sqlite3.connect(app.config["DB_PATH"])
        conn.row_factory = sqlite3.Row
        return conn

    with get_db() as conn:
        conn.executescript(SCHEMA)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/programs")
    def programs():
        return jsonify(PROGRAMS)

    @app.post("/clients")
    def save_client():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        program = data.get("program")
        if not name:
            return jsonify(error="Name is required"), 400
        if program not in PROGRAMS:
            return jsonify(error="Valid program is required"), 400
        weight = data.get("weight")
        try:
            calories = calculate_calories(weight, program) if weight else None
        except (ValueError, TypeError):
            return jsonify(error="Invalid weight"), 400
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO clients (name, age, height, weight, program,"
                " calories, target_weight, target_adherence) VALUES (?,?,?,?,?,?,?,?)",
                (name, data.get("age"), data.get("height"), weight, program, calories,
                 data.get("target_weight"), data.get("target_adherence")),
            )
        return jsonify(name=name, program=program, calories=calories), 201

    @app.get("/clients")
    def list_clients():
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
        return jsonify([dict(r) for r in rows])

    @app.get("/clients/<name>")
    def get_client(name):
        with get_db() as conn:
            row = conn.execute("SELECT * FROM clients WHERE name=?", (name,)).fetchone()
        if not row:
            return jsonify(error="Client not found"), 404
        return jsonify(dict(row))

    @app.delete("/clients/<name>")
    def delete_client(name):
        with get_db() as conn:
            cur = conn.execute("DELETE FROM clients WHERE name=?", (name,))
        if cur.rowcount == 0:
            return jsonify(error="Client not found"), 404
        return jsonify(deleted=name)

    @app.get("/clients/<name>/bmi")
    def client_bmi(name):
        with get_db() as conn:
            row = conn.execute("SELECT height, weight FROM clients WHERE name=?", (name,)).fetchone()
        if not row:
            return jsonify(error="Client not found"), 404
        try:
            bmi, category, risk = calculate_bmi(row["height"], row["weight"])
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(name=name, bmi=bmi, category=category, risk=risk)

    @app.post("/clients/<name>/progress")
    def save_progress(name):
        data = request.get_json(silent=True) or {}
        adherence = data.get("adherence")
        if not isinstance(adherence, int) or not 0 <= adherence <= 100:
            return jsonify(error="Adherence must be an integer 0-100"), 400
        with get_db() as conn:
            if not conn.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
                return jsonify(error="Client not found"), 404
            week = datetime.now().strftime("Week %U - %Y")
            conn.execute("INSERT INTO progress (client_name, week, adherence) VALUES (?,?,?)",
                         (name, week, adherence))
        return jsonify(client=name, week=week, adherence=adherence), 201

    @app.get("/clients/<name>/progress")
    def get_progress(name):
        with get_db() as conn:
            rows = conn.execute("SELECT week, adherence FROM progress WHERE client_name=? ORDER BY id",
                                (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    @app.post("/clients/<name>/workouts")
    def log_workout(name):
        data = request.get_json(silent=True) or {}
        wtype = data.get("workout_type")
        if wtype not in ("Strength", "Hypertrophy", "Cardio", "Mobility"):
            return jsonify(error="Invalid workout_type"), 400
        with get_db() as conn:
            if not conn.execute("SELECT 1 FROM clients WHERE name=?", (name,)).fetchone():
                return jsonify(error="Client not found"), 404
            conn.execute("INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)"
                         " VALUES (?,?,?,?,?)",
                         (name, data.get("date") or datetime.now().date().isoformat(), wtype,
                          data.get("duration_min", 60), data.get("notes", "")))
        return jsonify(client=name, workout_type=wtype), 201

    @app.get("/clients/<name>/workouts")
    def list_workouts(name):
        with get_db() as conn:
            rows = conn.execute("SELECT date, workout_type, duration_min, notes FROM workouts"
                                " WHERE client_name=? ORDER BY date DESC", (name,)).fetchall()
        return jsonify([dict(r) for r in rows])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

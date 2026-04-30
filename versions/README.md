# ACEest Fitness – Code Version History

This folder contains the original **tkinter desktop app** versions from Assignment 1.
Each version represents an incremental development milestone.

The Flask REST API (`app.py` in the project root) is the production version built from v3.2.4.

---

## Version Progression

| File | Version | Key Features Added |
|---|---|---|
| `Aceestver-1.0.py` | v1.0 | Base UI – program display (Fat Loss, Muscle Gain, Beginner), no data persistence |
| `Aceestver-1.1.py` | v1.1 | Client profile inputs (name, age, weight), calorie factor per program, save/reset |
| `Aceestver1.1.2.py` | v1.1.2 | UI refinements, style improvements |
| `Aceestver2.0.1.py` | v2.0.1 | SQLite database introduced (clients + progress tables) |
| `Aceestver-2.1.2.py` | v2.1.2 | Save/Load client from DB, weekly adherence progress logging |
| `Aceestver-2.2.1.py` | v2.2.1 | Enhanced client management, multi-client support |
| `Aceestver-2.2.4.py` | v2.2.4 | Workout logging, exercise tracking, body metrics |
| `Aceestver-3.0.1.py` | v3.0.1 | Role-based login (Admin), dashboard with notebook tabs |
| `Aceestver-3.1.2.py` | v3.1.2 | BMI calculator, matplotlib adherence charts, PDF report generation |
| `Aceestver-3.2.4.py` | v3.2.4 | AI-style program generator, full membership management – **final version** |

---

## Flask API Mapping (app.py)

The Flask REST API (`app.py`) exposes all v3.2.4 features as HTTP endpoints:

| Tkinter Feature | Flask Endpoint |
|---|---|
| Save/Load Client | `POST/GET /clients` |
| Weekly Progress | `POST/GET /clients/<name>/progress` |
| Workout Logging | `POST/GET /clients/<name>/workouts` |
| Body Metrics | `POST /clients/<name>/metrics` |
| BMI Calculator | `GET /bmi?weight=&height=` |
| AI Program Generator | `GET /clients/<name>/ai-program` |
| Membership Check | `GET /clients/<name>/membership` |

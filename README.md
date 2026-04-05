# 🏋️ ACEest Fitness & Gym – DevOps CI/CD Assignment

> **Course:** Introduction to DevOps (CSIZG514 / SEZG514 / SEUSZG514) | S2-25  
> **Assignment 1** | Flask REST API + Docker + GitHub Actions + Jenkins

---

## Project Background

This project migrates the **ACEest Fitness & Performance** desktop application
(built across versions 1.0 → 3.2.4 using Python tkinter + SQLite) into a
**containerised Flask REST API** with a full automated CI/CD pipeline.

All core business logic is preserved:

| Desktop Feature (tkinter) | Flask API Equivalent |
|---|---|
| `save_client()` | `POST /clients` |
| `load_client()` | `GET /clients/<name>` |
| `save_progress()` | `POST /clients/<name>/progress` |
| `add_workout()` | `POST /clients/<name>/workouts` |
| `open_log_metrics_window()` | `POST /clients/<name>/metrics` |
| `show_bmi_info()` | `GET /bmi?weight=&height=` |
| `generate_ai_program()` | `GET /clients/<name>/ai-program?experience=` |
| `check_membership()` | `GET /clients/<name>/membership` |

---

## Repository Structure

```
aceest-fitness/
├── app.py                        # Flask application (all business logic)
├── test_app.py                   # 47 Pytest tests (unit + integration)
├── requirements.txt              # Pinned dependencies
├── Dockerfile                    # Multi-stage, non-root Docker image
├── Jenkinsfile                   # Jenkins declarative pipeline
├── .github/
│   └── workflows/
│       └── main.yml              # GitHub Actions CI/CD (3-job pipeline)
└── README.md
```

---

## Local Setup & Execution

### Prerequisites

| Tool   | Version |
|--------|---------|
| Python | 3.10+   |
| Docker | 24+     |

```bash
# 1. Clone
git clone https://github.com/<YOUR_USERNAME>/aceest-fitness.git
cd aceest-fitness

# 2. Virtual environment
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install
pip install -r requirements.txt

# 4. Run
python app.py
# → http://localhost:5000
```

---

## Running Tests Manually

```bash
source venv/bin/activate

# All 47 tests
pytest test_app.py -v

# With coverage
pytest test_app.py -v --cov=app --cov-report=term-missing
```

### Test coverage areas

| Test Class | What it covers |
|---|---|
| `TestCalculateCalories` | Calorie calculation per program (weight × factor) |
| `TestCalculateBMI` | BMI formula and WHO risk categories |
| `TestGenerateAIProgram` | AI program generator (day count, keys, determinism) |
| `TestHomeAndHealth` | Root and health-check endpoints |
| `TestPrograms` | `/programs` listing |
| `TestClientEndpoints` | Save, load, validate, 404 handling |
| `TestProgressEndpoints` | Adherence logging, averages, validation |
| `TestWorkoutEndpoints` | Workout log, type validation, history |
| `TestBMIEndpoint` | HTTP BMI route with good/bad inputs |
| `TestAIProgramEndpoint` | AI program via HTTP, experience levels |
| `TestMembershipEndpoint` | Membership status check |

---

## Docker Usage

```bash
# Build
docker build -t aceest-fitness:latest .

# Run
docker run -d -p 5000:5000 --name aceest aceest-fitness:latest

# Smoke test
curl http://localhost:5000/health

# Pytest inside container
docker run --rm \
  -v $(pwd)/test_app.py:/app/test_app.py:ro \
  --entrypoint pytest \
  aceest-fitness:latest \
  test_app.py -v

# Stop
docker stop aceest && docker rm aceest
```

### Dockerfile design

- **Multi-stage build** — builder stage compiles wheels; runtime stage contains no build tools
- **Non-root user** (`appuser`) — satisfies container security best practices
- **HEALTHCHECK** — enables native Docker and orchestrator health polling

---

## GitHub Actions – CI/CD Overview

**Trigger:** every `push` (any branch) and every `pull_request` to `main`.

```
┌──────────────┐     ┌───────────────────────┐     ┌─────────────────────┐
│ 1. build-lint│────▶│ 2. docker-build        │────▶│ 3. automated-tests  │
│              │     │                         │     │                     │
│ • pip install│     │ • docker/build-push     │     │ • Load saved image  │
│ • flake8     │     │ • Save as .tar.gz       │     │ • pytest in Docker  │
└──────────────┘     └───────────────────────┘     │ • pytest + coverage │
                                                     └─────────────────────┘
```

Jobs are chained with `needs:` — a failure in any job blocks downstream jobs.
The Docker image travels between jobs as a GitHub Actions Artifact, avoiding
any registry dependency.

---

## Jenkins – BUILD Stage Overview

The `Jenkinsfile` uses a **Declarative Pipeline** with six stages:

| Stage | Action |
|---|---|
| **Checkout** | Pull `main` branch from GitHub |
| **Install Dependencies** | `python3 -m venv` + `pip install` |
| **Lint** | `flake8` — fatal errors fail the build |
| **Unit Tests** | `pytest` — JUnit XML archived in Jenkins UI |
| **Docker Build** | Image tagged with `BUILD_NUMBER` |
| **Docker Smoke Test** | Run container, `curl /health`, stop container |

### Setting up Jenkins

1. Install Jenkins; enable **Pipeline** and **Git** plugins.
2. New **Pipeline** project → *Pipeline script from SCM* → Git.
3. Set your repository URL and branch to `main`.
4. Replace `<YOUR_USERNAME>` in `Jenkinsfile` with your GitHub username.
5. Optionally configure a GitHub Webhook for automatic triggers on push.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Welcome + status |
| GET | `/health` | Health check |
| GET | `/programs` | List all 4 fitness programs |
| GET | `/clients` | List all clients |
| POST | `/clients` | Save / update client |
| GET | `/clients/<name>` | Get one client |
| POST | `/clients/<name>/progress` | Log weekly adherence |
| GET | `/clients/<name>/progress` | Get adherence history + average |
| POST | `/clients/<name>/workouts` | Log workout session |
| GET | `/clients/<name>/workouts` | Get workout history |
| POST | `/clients/<name>/metrics` | Log body metrics (weight, waist, bodyfat) |
| GET | `/bmi?weight=&height=` | Calculate BMI + risk category |
| GET | `/clients/<name>/ai-program?experience=` | Generate workout plan |
| GET | `/clients/<name>/membership` | Check membership status |

---

*Built by migrating ACEest Fitness Desktop App (tkinter) → Flask REST API with full DevOps pipeline.*

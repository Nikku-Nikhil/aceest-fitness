# Assignment 2 – DevOps CI/CD Implementation Report
## ACEest Fitness & Gym
**Course:** Introduction to DEVOPS (CSIZG514/SEZG514) | **Semester:** S1-25
**Student:** Nikhil | **GitHub:** https://github.com/Nikku-Nikhil/aceest-fitness

---

## 1. CI/CD Architecture Overview

### Application Background
ACEest Fitness & Gym is a fitness management system that evolved through 10 incremental tkinter desktop app versions (v1.0 → v3.2.4). For this assignment, the final version was re-implemented as a **Flask REST API** (`app.py`) exposing endpoints for client management, workout logging, BMI calculation, progress tracking, and AI-based program generation.

### Pipeline Architecture

The CI/CD pipeline is implemented across two platforms:

#### A. GitHub Actions (5-job automated pipeline)

```
Push to GitHub
      │
      ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Job 1      │────▶│   Job 2      │────▶│    Job 3         │
│ Build & Lint│     │ Docker Build │     │ Automated Tests  │
│ (Flake8)    │     │ (BuildKit)   │     │ (Pytest + Cov.)  │
└─────────────┘     └──────────────┘     └──────────────────┘
                                                   │
                          ┌────────────────────────┘
                          ▼
               ┌──────────────────┐     ┌──────────────────┐
               │     Job 4        │────▶│    Job 5         │
               │ SonarCloud Scan  │     │ Docker Hub Push  │
               │ (Quality Gate)   │     │ (snikhil2001/    │
               └──────────────────┘     │  aceest-fitness) │
                                        └──────────────────┘
```

**Job Details:**
| Job | Tool | Purpose |
|---|---|---|
| Build & Lint | Flake8 | Code style enforcement (PEP8) |
| Docker Build | Docker BuildKit + GHA Cache | Multi-stage image build |
| Automated Tests | Pytest + pytest-cov | 35+ unit & integration tests, coverage XML |
| SonarCloud | SonarCloud GitHub Action | Static analysis, quality gate |
| Docker Push | Docker Hub | Publish `snikhil2001/aceest-fitness:latest` |

#### B. Jenkins Pipeline (9 stages, local CI server)

```
Checkout → Install Deps → Lint → Unit Tests →
SonarQube Analysis → Quality Gate → Docker Build → Smoke Test → Push to Docker Hub
```

### Containerization
- **Multi-stage Dockerfile**: Builder stage (pip install) + Runtime stage (non-root user, healthcheck)
- **Docker Hub Registry**: `snikhil2001/aceest-fitness` with versioned tags per build number
- **Health Check**: `GET /health` endpoint polled every 30s inside container

### Kubernetes Deployment (5 Strategies)
All manifests are in the `k8s/` directory under the `aceest` namespace:

| Strategy | File | Mechanism |
|---|---|---|
| Rolling Update | `deployment.yml` | maxSurge=1, maxUnavailable=0 — zero-downtime pod replacement |
| Blue-Green | `blue-green.yml` | Two deployments (blue/green); Service selector patched to switch |
| Canary Release | `canary.yml` | 9 stable replicas + 1 canary = ~10% canary traffic |
| Shadow | `shadow.yml` | Production + shadow deployment; mirrored traffic via Istio annotation |
| A/B Testing | `ab-testing.yml` | Two deployments with separate NodePort services (30085/30086) |

### Code Quality
- **SonarCloud** (`sonar-project.properties`): Org `nikku-nikhil`, project `nikku-nikhil_aceest-fitness`
- Metrics tracked: Security, Reliability, Maintainability, Coverage, Duplications
- Quality gate blocks Docker Hub push on failure

---

## 2. Challenges Faced and Mitigation Strategies

### Challenge 1: Flake8 W292 – Missing newline at end of file
**Error:** `app.py:475:52: W292 no newline at end of file`
**Cause:** File editor did not append a trailing newline byte.
**Fix:** Used `echo "" >> app.py` to append `0x0a` at the binary level, then committed.

### Challenge 2: `docker load` failing with "repositories: no such file or directory"
**Error:** `open /var/lib/docker/tmp/docker-import-XXXXX/repositories: no such file`
**Root Cause 1:** `docker load < image.tar.gz` — Docker could not auto-detect gzip format via stdin redirection.
**Fix 1:** Changed to `gunzip -c image.tar.gz | docker load`.
**Root Cause 2:** `docker/build-push-action` with only `push: false` keeps the image in BuildKit cache — never in the local Docker daemon, so `docker save` produced an empty tar.
**Fix 2:** Added `load: true` to `docker/build-push-action`, forcing image export to local daemon before `docker save`.

### Challenge 3: SonarCloud "Project not found" error
**Error:** `Project not found. Please check the 'sonar.projectKey' and 'sonar.organization'`
**Cause:** SonarCloud project had not been manually created before the CI job ran.
**Fix:** Created the project in SonarCloud via GitHub import. Then disabled "Automatic Analysis" to avoid conflict with the GitHub Actions CI-based analysis. Generated a Personal Access Token and added it as `SONAR_TOKEN` GitHub secret.

### Challenge 4: Docker Hub push 401 Unauthorized
**Error:** `access token has insufficient scopes`
**Cause:** Docker Hub Personal Access Token was generated with Read-only scope.
**Fix:** Regenerated token with **Read & Write** scope and updated the `DOCKER_PASSWORD` GitHub secret.

### Challenge 5: Git user not configured
**Error:** `git commit` failed — `git config user.name` returned nothing.
**Fix:** Set `git config user.name` and `git config user.email` from commit log metadata before committing.

---

## 3. Key Automation Outcomes

### Test Coverage
- **35+ test cases** covering all API endpoints and pure business logic functions
- Tests structured into 9 classes: `TestCalculateCalories`, `TestCalculateBMI`, `TestGenerateAIProgram`, `TestHomeAndHealth`, `TestPrograms`, `TestClientEndpoints`, `TestProgressEndpoints`, `TestWorkoutEndpoints`, `TestBMIEndpoint`, `TestAIProgramEndpoint`, `TestMembershipEndpoint`
- Each test uses an isolated in-memory SQLite DB via `tmp_path` fixture — no test pollution

### Pipeline Metrics
| Metric | Value |
|---|---|
| Pipeline jobs (GitHub Actions) | 5 |
| Jenkins stages | 9 |
| Docker image size | ~135 MB (multi-stage slim) |
| Code versions tracked | 10 (v1.0 → v3.2.4) |
| Git tags | v1.0.0, v2.0.0, v3.0.0, v3.2.4 |
| K8s deployment strategies | 5 |
| SonarCloud quality gate | Enforced (blocks push on fail) |

### DevOps Principles Demonstrated
- **Continuous Integration**: Every push triggers lint → test → build automatically
- **Continuous Delivery**: Passing builds auto-push verified Docker images to Docker Hub
- **Infrastructure as Code**: All K8s manifests version-controlled in `k8s/`
- **Shift-Left Testing**: Tests run before Docker build — failures caught early
- **Zero-Downtime Deployment**: Rolling update + Blue-Green strategies ensure no user impact
- **Rollback Capability**: `kubectl rollout undo` for Rolling; Service selector patch for Blue-Green; `kubectl delete` canary/shadow for instant rollback

---

## Repository Structure

```
aceest-fitness/
├── app.py                     # Flask REST API (v3.2.4 as microservice)
├── test_app.py                # Pytest test suite (35+ tests)
├── Dockerfile                 # Multi-stage, non-root, healthcheck
├── Jenkinsfile                # 9-stage Jenkins pipeline
├── requirements.txt
├── sonar-project.properties   # SonarCloud configuration
├── versions/                  # Original tkinter app v1.0–v3.2.4
│   ├── README.md              # Version progression table
│   └── Aceestver-*.py (×10)
├── k8s/                       # Kubernetes manifests
│   ├── namespace.yml
│   ├── service.yml
│   ├── deployment.yml         # Rolling Update
│   ├── blue-green.yml         # Blue-Green
│   ├── canary.yml             # Canary Release
│   ├── shadow.yml             # Shadow Deployment
│   └── ab-testing.yml         # A/B Testing
└── .github/workflows/
    └── main.yml               # 5-job GitHub Actions CI/CD
```

**GitHub Repository:** https://github.com/Nikku-Nikhil/aceest-fitness
**Docker Hub:** https://hub.docker.com/r/snikhil2001/aceest-fitness
**SonarCloud:** https://sonarcloud.io/organizations/nikku-nikhil/projects

# ACEest Fitness & Gym - CI/CD Pipeline

Flask service for gym/fitness management (clients, programs, calorie targets, BMI,
weekly adherence, workout logs) with automated testing, Docker packaging and CI/CD
via GitHub Actions and Jenkins. It is a web port of the ACEest Tkinter desktop
application (v1.0 - v3.2.4).

## Project structure
```
app.py                     Flask application (app factory + routes)
requirements.txt           Python dependencies
tests/test_app.py          Pytest suite (28 tests)
Dockerfile                 Multi-stage, non-root image
Jenkinsfile                Jenkins pipeline (clean build + quality gate)
.github/workflows/main.yml GitHub Actions CI
```

## Run locally
```bash
git clone <repo-url> && cd <repo>
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py                                        # http://localhost:5000
curl http://localhost:5000/health
```

## Run tests manually
```bash
pytest -v                                            # local
docker build -t aceest-fitness .
docker run --rm aceest-fitness pytest -v             # inside the container
```

## Run with Docker
```bash
docker build -t aceest-fitness .
docker run -p 5000:5000 -v aceest-data:/data aceest-fitness
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | Liveness check |
| GET | /programs | Programs and calorie factors |
| POST/GET | /clients | Save (upsert) / list clients |
| GET/DELETE | /clients/<name> | Get / delete a client |
| GET | /clients/<name>/bmi | BMI, category and risk note |
| POST/GET | /clients/<name>/progress | Log / read weekly adherence (0-100) |
| POST/GET | /clients/<name>/workouts | Log / read workouts |

## CI/CD overview
**GitHub Actions** (`.github/workflows/main.yml`) runs on every push and pull request:
1. *Build & Lint* - install dependencies, `py_compile`, `flake8`.
2. *Docker Build & Test* (after stage 1) - build the image, run `pytest` inside the container.

**Jenkins** (`Jenkinsfile`) is the secondary quality gate: it pulls the latest code from
GitHub, recreates a clean virtualenv, lints, runs the unit tests, builds the Docker image
and re-runs the tests inside it. Any failing stage fails the build.

# Data Engineering Learning Coach

Modules 1–3 add structured learner memory, a local Streamlit onboarding flow, and an evidence-weighted skill assessment while deliberately keeping LLM/agent behavior out of scope.

## Stack

- FastAPI backend
- Streamlit frontend
- SQLite with SQLAlchemy
- Pydantic schemas and configuration
- pytest test suite

## Project layout

```text
app/
  api/        HTTP routes
  agent/      future AI-agent boundary
  database/   SQLAlchemy engine, sessions, and initialization
  models/     learner-memory database models
  prompts/    future prompt assets
  schemas/    Pydantic API schemas
  services/   application service layer
  ui/         Streamlit entry point
  config.py   environment-backed settings
  main.py     FastAPI entry point
tests/        pytest suite
```

## Setup

Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Environment variables are read directly by the application. Load `.env` with your preferred shell/tool, or export values before running. The supported values are `APP_NAME`, `ENVIRONMENT`, `DATABASE_URL`, and `LOG_LEVEL`.

For the default SQLite URL, the database file is created at `data/learning_coach.db` when the API starts.

## Run the API

```bash
uvicorn app.main:app --reload
```

Visit `http://127.0.0.1:8000/health` to receive a health response, and `http://127.0.0.1:8000/docs` for the API documentation.

## Run the UI

In a second terminal with the virtual environment active:

```bash
streamlit run app/ui/streamlit_app.py
```

## Test

```bash
pytest
```

## Learner memory

The database persists learner profiles, a canonical skill catalog, per-learner
skill assessments, learning-topic progress, and portfolio projects. The
session-based CRUD functions live in `app/services/learner_memory_service.py`,
keeping this memory usable from future API and UI layers without coupling it to
an LLM.

## Learner onboarding and assessment

The Streamlit UI collects background, skill self-assessments, career goals, schedule, and learning preference. It validates required fields and feasible numeric values, persists one local onboarding profile, and shows an **Edit profile** action once it exists.

Module 3 covers 18 data-engineering skills on a 1–10 scale. It combines self-report with optional diagnostic, quiz, and project-evidence scores, then shows score, proficiency level, target gap, and priority. Self-report-only results are explicitly low confidence. Roadmap generation is intentionally out of scope.

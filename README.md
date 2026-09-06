# Data Engineering Learning Coach

Modules 1–5 add structured learner memory, a local Streamlit onboarding flow, an evidence-weighted skill assessment, a skill gap dependency graph, and an LLM-powered personalized roadmap generation service with structured validation.

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

## Learner onboarding, assessment, gap analysis, roadmap generation, and planning

The Streamlit UI collects background, skill self-assessments, career goals, schedule, and learning preference. It validates required fields and feasible numeric values, persists one local onboarding profile, and shows an Edit profile action once it exists.

Module 3 covers 18 data-engineering skills on a 1–10 scale. It combines self-report with optional diagnostic, quiz, and project-evidence scores, then shows score, proficiency level, target gap, and priority. Self-report-only results are explicitly low confidence.

Module 4 builds a skill dependency graph from a learner profile and skill assessments. It identifies missing prerequisites, weak areas, critical gaps, and downstream skills that depend on them.

Module 5 adds personalized roadmap generation with structured Pydantic validation. The roadmap uses the learner's skills, target role, target timeline, weekly study hours, and identified gaps to produce an ordered learning path.

Module 6 adds ⁠ generate_learning_plan ⁠, a deterministic planner that converts the roadmap into weekly learning sessions with topic, activity, expected outcome, focus, and tasks. It accounts for study hours, completed topics, mastered topics, weak areas, and revision needs.

Module 7 adds ⁠ handle_teaching_command ⁠, a deterministic mentor-mode teaching engine for learner requests such as explanations, daily tasks, quizzes, examples, and refactoring. It validates the requested topic against the learner's current level and roadmap context and provides a structured next step.

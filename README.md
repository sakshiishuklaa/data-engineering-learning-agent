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

## Learner onboarding, assessment, gap analysis, and roadmap generation

The Streamlit UI collects background, skill self-assessments, career goals, schedule, and learning preference. It validates required fields and feasible numeric values, persists one local onboarding profile, and shows an **Edit profile** action once it exists.

Module 3 covers 18 data-engineering skills on a 1–10 scale. It combines self-report with optional diagnostic, quiz, and project-evidence scores, then shows score, proficiency level, target gap, and priority. Self-report-only results are explicitly low confidence.

Module 4 builds an explainable target-role skill dependency graph from a learner profile, learner skills, target role, target timeline, and weekly study hours. It models prerequisite chains such as Python to PySpark to Spark Optimization, SQL to Data Modeling to Data Warehousing, Linux and Git to Docker to CI/CD, and ETL/ELT to Orchestration. The result reports skill gaps, readiness, blocked skills, critical gaps, estimated gap hours, and timeline capacity pressure, but it does not generate a roadmap.

Module 5 adds `generate_personalized_roadmap`, an LLM boundary that requires structured JSON/Pydantic output. The service accepts a learner profile, skill assessment, skill gap analysis, target role, timeline, and weekly study hours, then validates generated phases before callers can trust or persist them. Validation rejects free-form or malformed output, already-known topics, unsupported topics, prerequisite violations, timeline overruns, incorrect MUST_LEARN / GOOD_TO_LEARN / OPTIONAL labels, missing MUST_LEARN skills, and optional topics scheduled before required work. Tests use a mock LLM client, so no real API key is required.

Module 6 adds `generate_learning_plan`, a deterministic planner that converts a personalized roadmap into a weekly table with `Day`, `Topic`, `Activity`, `Duration`, and `Expected Outcome`, plus daily buckets for Learn, Practice, Hands-on, Revision, and Interview practice. The default allocation is 30% theory, 50% hands-on, and 20% interview/practice, and callers can override it with a validated `PlannerAllocation`. The planner skips completed topics unless revision is required, prioritizes weak topics during revision, and reschedules incomplete work while preserving important prerequisites without blindly shifting every future task.

Module 7 adds `handle_teaching_command`, a deterministic mentor-mode teaching engine for learner utterances such as "Teach me Spark", "Explain partitioning", "Give me today's task", "I don't understand joins", and "next topic". It maintains a `TeachingSession` with the current topic, learner level, current roadmap phase, completed/mastered topics, weak areas, and turn count. Each response follows the required flow: concept, simple explanation, data-engineering example, code/example, hands-on exercise, quiz, evaluation, and next step. Topic selection uses the roadmap, learning plan, weak areas, and mastered topics so beginner material that is already mastered is skipped or reframed instead of repeated.

# Data Engineering Learning Coach

Module 0 establishes the Python application foundation for a future AI-powered data engineering learning coach. It deliberately does not implement agent behavior or learning features yet.

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
  models/     future database models
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

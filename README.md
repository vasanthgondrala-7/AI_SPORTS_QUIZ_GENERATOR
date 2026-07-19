# AI-Powered Sports Quiz Generation Agent

Quick demo that generates grounded, multiple-choice sports quizzes using a RAG pipeline (ChromaDB + DuckDuckGo + OpenAI).

- See `app.py` for the Streamlit dashboard.

Setup
-----
1. Create a Python 3.9–3.11 virtualenv and activate it.

```bash
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`. To run a fast demo without API access, set `MOCK_MODE=1` in `.env`.

3. Seed local ChromaDB (only required when `MOCK_MODE=0`): the app will attempt to create and populate the DB on first run.

4. Run the Streamlit app:

```bash
streamlit run app.py
```

Notes
- The project includes a `MOCK_MODE` flag in `.env` to run without LLM or web access; this is the recommended demo mode for quick evaluation.
- If you see sqlite/ChromaDB errors on Windows, install `pysqlite3-binary` or use `MOCK_MODE=1`.
- The app offers a JSON export and a visible RAG context expander for auditability.

Architecture
------------
- `app.py` — Streamlit UI and session orchestration.
- `src/config.py` — environment configuration and feature toggles.
- `src/database.py` — ChromaDB helpers (optional; mocked when `MOCK_MODE=1`).
- `src/search.py` — DuckDuckGo search wrapper for live context.
- `src/llm_client.py` — OpenAI wrapper with retry and mock fallback.
- `src/generator.py` — RAG orchestration, prompting, schema validation and hallucination checks.
- `src/utils.py` — JSON parsing and schema validation utilities.

Design decisions & trade-offs
----------------------------
- Mock-first flow: The app supports `MOCK_MODE` to make the demo reproducible without provisioning keys or installing heavy ML dependencies.
- Strict JSON + validation: The generator enforces a JSON schema and requires explanations to reference retrieved sources to reduce hallucinations.
- Local vector DB: ChromaDB is used as a persistent local store when available; in constrained environments the app falls back to mock behavior.

1. Create a Python 3.9–3.11 virtualenv and activate it.

```bash
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and add your `OPENAI_API_KEY`.

3. Run the Streamlit app:

```bash
streamlit run app.py
```

Notes
- The project includes a `MOCK_MODE` flag in `.env` to run without LLM or web access.
- If you see sqlite/ChromaDB errors on Windows, install `pysqlite3-binary`.

Project structure
- `app.py` — Streamlit UI
- `src/` — core modules: `database.py`, `search.py`, `generator.py`, `llm_client.py`, `utils.py`
- `data/sports_facts.json` — sample facts used to seed ChromaDB

For evaluation: aim to keep prompts strict, use JSON schema validation, and surface the RAG context used for each quiz.#

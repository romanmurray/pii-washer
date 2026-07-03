# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PII-Washer is a local-only PII detection and text sanitization tool. Users paste text containing personal data, get a clean version with placeholders, use it with LLMs, then swap placeholders back. Privacy-first: no network calls, in-memory only, secure clear on shutdown.

## Commands

```bash
# Backend
pip install -e ".[dev]"                    # Install with dev deps (pytest, ruff, httpx)
uvicorn pii_washer.api.main:app --reload   # Run backend on :8000

# Frontend
cd pii-washer-ui && npm install            # Install frontend deps
cd pii-washer-ui && npm run dev            # Run frontend on :5173
cd pii-washer-ui && npm run lint           # ESLint
cd pii-washer-ui && npm run test           # Frontend tests (vitest)
cd pii-washer-ui && npm run build          # TypeScript check + Vite build

# Tests
pytest                                     # Run all backend tests
pytest -m integration                      # Tests against the real Presidio/spaCy engine
pytest pii_washer/tests/test_api.py        # Run a single test file
pytest -k "test_depersonalize"             # Run tests matching a name
ruff check .                               # Backend lint
```

## Architecture

**Backend (Python):** FastAPI REST API at `/api/v1/`. All components are wired through `SessionManager`, which is the single orchestration boundary — the API router calls only SessionManager methods.

- `SessionManager` — coordinates workflow through a state machine (`user_input` → `analyzed` → `depersonalized` → `awaiting_response` → `repersonalized`). Each state gates which operations are allowed via `WORKFLOW_STATES`.
- `PIIDetectionEngine` — wraps Microsoft Presidio + spaCy NER (`en_core_web_lg`) with custom regex recognizers for formats Presidio misses.
- `PlaceholderGenerator` — deterministic `[TYPE_N]` placeholder assignment with a `CATEGORY_PREFIX_MAP`.
- `TextSubstitutionEngine` — bidirectional: depersonalize (PII → placeholders) and repersonalize (placeholders → PII).
- `TempDataStore` — in-memory session storage with secure clear.
- `DocumentLoader` — text/file ingestion with validation. 1MB file size limit. Allowed extensions: `.txt`, `.md`, `.docx`, `.pdf`, `.csv`, `.xlsx`, `.html`. Binary formats use extractors in `pii_washer/extractors/`.

**Frontend (React 19 + TypeScript + Vite + Tailwind v4):** SPA in `pii-washer-ui/`. Uses Zustand for state, TanStack React Query for API calls, Radix UI primitives, and Lucide icons. Tab-based workflow: Input → Review → Response → Results. API client in `src/api/client.ts`.

**Desktop:** PyInstaller + pywebview. Entry point at `pyinstaller_entry.py` — starts FastAPI in a background thread, opens a native window via pywebview. The frontend dist is bundled at `ui/` inside the executable. Build command is in the README's "Desktop app" section.

## Key Constraints

- **Python 3.11–3.13 only.** spaCy (via its pydantic v1 dependency) is incompatible with Python 3.14.
- **spaCy model installed via direct URL**, not `spacy download`: `pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl`
- **Never write PII to disk.** File uploads are decoded in memory. Session data is in-memory only. The only file the app writes is a content-free log at `~/.pii-washer/pii-washer.log`.
- **No network calls at runtime.** No CDN assets, no external fonts, no update checks. `tldextract` is pinned to its bundled snapshot.
- **Tests use a MockDetectionEngine** that returns predictable detections without requiring spaCy/Presidio. The real engine is heavy (~560MB model) and slow to initialize; tests that need it are marked `integration`.
- The `create_app()` factory in `api/main.py` accepts an optional `session_manager` for test injection.
- **Version has a single source of truth: `pyproject.toml`.** The API reads it at runtime via `importlib.metadata.version("pii-washer")` (see `get_app_version()` in `pii_washer/api/config.py`). Only update `pyproject.toml` when bumping — then re-run `pip install -e .` so the installed metadata matches.

## Documentation Conventions

- `CHANGELOG.md` follows Keep a Changelog; every user-visible change lands there.
- Significant design decisions get an ADR in `docs/adr/NNNN-slug.md` — short: context, decision, consequences.
- Commit messages use conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

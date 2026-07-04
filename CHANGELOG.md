# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Social preview image tagline replaced with the project's actual one-liner: "Local-only PII detection and text sanitization"

### Fixed

- A lone first name after a greeting ("Hi Sandra,") is now detected — a new greeting-based name recognizer covers the case where no surname, title, or NER hit exists
- Street addresses keep their apartment suffix when a comma precedes it ("2847 Willow Creek Drive, Apt 12B" was previously cut at "Drive")
- State abbreviation + zip ("IL 62704") is now captured as one ADDRESS span — previously the state abbreviation was only used as context to accept the zip, and itself leaked through

## [1.4.0] - 2026-07-03

### Added

- `ID` detection category with `[ID_N]` placeholders, backed by a new labeled-identifier recognizer: values introduced by a label ("Routing number:", "CVV:", "Passport number:", "License plate:", "Employee ID:", …) are detected via the label itself — bank accounts, government IDs, insurance member/group numbers, plates, and organization-internal identifiers, without the false-positive flood that shape-only matching of bare codes would cause
- Dashed credit card format (`4111-1111-1111-1111`) in the custom card recognizer

### Fixed

- Phone detection now catches the common `(555) 123-4567` example format — the parenthesized recognizer no longer requires a NANP-valid exchange digit (the area code still must start 2-9; bare-separator formats are unchanged to avoid matching dates/IDs)
- The spaCy model no longer loads twice at startup — a leftover `spacy.load()` call was discarding a full copy of the ~560MB model before Presidio loaded it again; engine init is now roughly twice as fast with half the peak memory
- Credit card numbers that fail Luhn validation (AI-generated test data, typos) are no longer half-missed: near card context words they're now flagged whole at reduced confidence — previously spaCy could tag a 12-digit fragment as a date, producing a mislabeled partial redaction that left the last 4 digits exposed
- Date-of-birth candidates now require a plausible date shape — bare digit runs (card-number fragments) and relative words ("today") are no longer surfaced as low-confidence DOB detections
- Person-name detections no longer bleed across line breaks into the next line's label ("Michael Torres\nDate of birth" is now trimmed at the newline)

### Changed

- UI fonts switched from Google Fonts (Inter) to the system font stack — removes the only external network request the app made
- README, INSTALL, and CLAUDE.md rewritten for public release: current feature set, accurate Node.js requirement (20.19+), tool-specific Python constraint wording, honest privacy section documenting the `~/.pii-washer/pii-washer.log` file, desktop-build instructions, and a workflow state-machine diagram
- `.gitignore` no longer blanket-ignores `*.json` — the session-export feature that rule guarded was removed in 1.1.0
- `.npmrc` `legacy-peer-deps` flag documented (Tailwind's Vite plugin doesn't yet declare Vite 8 peer support)
- New brand identity: flat vector washing-machine mark (single master SVG), "PII-Washer" naming everywhere (was "Pii Washer"), header logos cut from ~700KB to 11KB each, favicon and app-icon set regenerated, ~9MB of unused icon/logo variants removed
- README now includes workflow screenshots (Review, Clean Text, Results)

### Removed

- "Source" link row in the About dialog
- Internal "Task N" tracker references in detection-engine comments (47 comments now self-contained)
- `docs/roadmap.md` — internal planning document, not part of the public repo; CHANGELOG remains the project history

## [1.3.0] - 2026-06-27

### Added

- Typed API exception classes in `pii_washer/api/exceptions.py` (`InvalidStateError`, `DetectionNotFoundError`, `DuplicateDetectionError`, `TextNotFoundError`) — each carries its own HTTP status and error code instead of being inferred from the error message
- `get_app_version()` in `pii_washer/api/config.py` reads the version from installed package metadata — single source of truth in `pyproject.toml`
- `NoSessionAlert` component for consistent empty-state UX across tabs

### Changed

- `MAX_FILE_SIZE` moved from `DocumentLoader` class attribute to `pii_washer/api/config.py`; router no longer imports `DocumentLoader` just for the constant
- `useResetSession` now targets session-scoped query keys (`['session']`, `['sessionStatus']`, `['sessions']`) instead of clearing the entire React Query cache
- Canonical remote moved to a self-hosted git server

### Fixed

- `ResponseTab` re-syncs its textarea off the session's `updated_at` timestamp instead of a text length+prefix fingerprint — no longer misses edits that happen to keep the same shape
- `add_manual_detection` raises the typed `InvalidStateError` for wrong-state calls, so it returns HTTP 409 like every other state check (was 422)
- Clipboard "copy" actions surface a failure toast instead of failing silently — matters in the pywebview desktop build where clipboard permissions can be denied

### Removed

- Legacy string-matching error classifier (`classify_value_error`) — error responses are now driven entirely by typed exception classes, completing the typed-exception migration
- Always-disabled "Next" button on the Review and Response tabs (forward navigation happens via the primary action buttons)
- GitHub Actions CI and release workflows (`.github/workflows/`) — no automated CI/release pipeline; lint, tests, and builds run manually on the Windows dev machine
- Update checker (`/api/v1/updates/check` + frontend "Check for Updates" UI) — relied on the GitHub releases API
- Cross-platform release artifacts (Windows / macOS / Linux executables) — project is Windows-only
- Tauri CORS origins from `CORS_ORIGINS` (Tauri was removed from the project long ago)
- Orphaned `SessionManager` methods: `get_depersonalized_text`, `load_response_file`
- Dead frontend files: `App.css` (Vite scaffolding), `api/health.ts`, unused `useAnalyze` hook
- Stale `.gitignore` entry for `pii-washer-ui/src-tauri/`
- Dummy `"version": "0.0.0"` from frontend `package.json`
- Stale `__version__ = "1.0.0"` from `pii_washer/__init__.py` (the `APP_VERSION` in `config.py` was kept in sync with `pyproject.toml`; both are now replaced by `get_app_version()`)

## [1.2.0] - 2026-04-03

### Added

- File format support: .docx, .pdf, .csv, .xlsx, .html
- Extractor architecture in `pii_washer/extractors/` with strategy pattern
- Structure preservation: headings, paragraphs, lists, and tables maintained in extracted text
- CI workflow: backend tests (Python 3.12/3.13), Ruff lint, frontend lint/build/test on every push/PR
- Cross-platform release builds: Windows, macOS, and Linux executables via GitHub Actions

## [1.1.1] - 2026-04-03

### Added

- Settings menu (gear icon) in header with About dialog and Check for Updates
- `GET /api/v1/updates/check` endpoint for version comparison against GitHub releases
- ALL CAPS name detection in `DictionaryNameRecognizer` and `TitleNameRecognizer`
- Typed `SessionDetailResponse` Pydantic model for `GET /sessions/{id}`
- Custom placeholder validation (character allowlist, 50-char max)
- React error boundary — app shows friendly error screen with "Start Over" instead of going blank
- Frontend test infrastructure (vitest + testing-library) with store and component tests
- API integration tests with real Presidio/spaCy (skips gracefully if model not installed)
- Codex adversarial review tracker (`docs/codex-review-tracker.md`) — single source of truth for all 22 findings

### Fixed

- Session creation response no longer includes `original_text` (reduces PII exposure in browser caches)
- Server error responses no longer leak internal exception details
- CORS restricted to only used methods and headers
- httpx client connection leak in update checker
- File size error message corrected from "10 MB" to "1 MB"
- Custom-edited placeholders now detected in `unknown_in_text` report during repersonalization

## [1.1.0] - 2026-04-01

### Added

- "Start Over" button in header to reset and begin a new task
- `POST /sessions/reset` endpoint for clearing session state

### Removed

- Session list, import/export, and multi-session management UI
- Backend endpoints: `GET /sessions`, `DELETE /sessions`, `POST /sessions/import`, `DELETE /sessions/{id}`, `GET /sessions/{id}/export`

## [1.0.1] - 2026-03-20

### Added

- Dictionary-based and heuristic name recognizers for improved PII name detection
- Error logging to `~/.pii-washer/pii-washer.log` with full tracebacks
- Integration and false positive test coverage

### Fixed

- Reduced false positives in name detection (bracketed text, newline bleed)
- ZIP code, phone number, and IP address validation accuracy
- Export toast no longer covers action buttons
- Text selection now works in the Review tab document viewer
- Path traversal guard on file operations
- Security review findings (session data handling, input validation)
- Removed ghost "confirmed" status that was accepted by the data store but never used by the workflow engine
- Declared missing `tldextract` dependency; added `pywebview` as optional desktop extra

### Changed

- Removed abandoned Tauri build artifacts from the frontend directory

## [1.0.0] - 2026-03-18

Initial public release. Local-only PII detection and text sanitization with a React UI and FastAPI backend.

# PII-Washer — Installation Guide

PII-Washer runs from source on Windows. The stack itself (FastAPI, React, Presidio) is cross-platform, but other operating systems are untested.

## Requirements

- **Python 3.11–3.13**
  - Python 3.14 is **not supported** — spaCy (the NLP library PII-Washer depends on) is not yet compatible with it.
  - Install from [python.org](https://www.python.org/downloads/) or use the Python Launcher (`py -3.13`).
- **Node.js 20.19+** (for the React frontend — Vite 8 requires it)
- **Git** (to clone the repository)
- **4 GB+ disk space** (the spaCy language model is ~560 MB)

## Step-by-step setup

### 1. Clone the repository

```powershell
git clone https://github.com/romanmurray/pii-washer.git
cd pii-washer
```

### 2. Create a Python virtual environment

If your default `python` is 3.14, create the venv with 3.13 explicitly:

```powershell
py -3.13 -m venv .venv
.venv\Scripts\activate
```

Confirm you're on a supported version:
```powershell
python --version
# Should show Python 3.11.x – 3.13.x
```

### 3. Install the Python backend

```powershell
pip install -e .
```

This installs Presidio Analyzer, spaCy, FastAPI, and the PII-Washer package itself in editable mode.

To also install development/test dependencies:
```powershell
pip install -e ".[dev]"
```

### 4. Install the spaCy language model

The NER model must be installed via direct URL (it is not available on PyPI):

```powershell
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl
```

This downloads ~560 MB. An internet connection is required for this step only — after installation, PII-Washer runs entirely offline.

### 5. Install the frontend

```powershell
cd pii-washer-ui
npm install
cd ..
```

### 6. Launch PII-Washer

You need two terminals — one for the backend, one for the frontend.

**Terminal 1 — Backend:**
```powershell
uvicorn pii_washer.api.main:app --reload
```

**Terminal 2 — Frontend:**
```powershell
cd pii-washer-ui
npm run dev
```

Open **http://localhost:5173** in your browser. The Vite dev server proxies API requests to the FastAPI backend automatically.

## Building the desktop app (optional)

PII-Washer can be packaged as a standalone Windows executable — see the **Desktop app** section in [README.md](README.md) for the PyInstaller command.

## Verifying the installation

Run the test suite to confirm everything is working:

```powershell
pytest                  # fast suite (mock detection engine)
pytest -m integration   # exercises the real Presidio/spaCy engine
```

## Troubleshooting

### "No module named pii_washer"
Make sure your virtual environment is activated and you ran `pip install -e .` from the project root.

### spaCy model errors
If you see errors about `en_core_web_lg` not being found, re-run the model install command from step 4. Do **not** use `python -m spacy download en_core_web_lg` — it is unreliable on Python 3.13+.

### Python 3.14 crashes on import
spaCy is incompatible with Python 3.14 due to its pydantic v1 dependency. Create the venv with `py -3.13`.

### npm install fails with a Node version error
Vite 8 requires Node 20.19+ (or 22.12+). Check `node --version` and upgrade from [nodejs.org](https://nodejs.org/) if needed.

### "Access is denied" when recreating the venv
Kill any running Python processes before deleting or recreating the `.venv` directory.

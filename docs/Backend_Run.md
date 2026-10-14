# PolyBridge — Backend Service

FastAPI-powered AST parsing, universal intermediate representation (IR) translation, code generation, and behavioral equivalence sandbox for PolyBridge.

---

## 📋 Prerequisites

- **Python**: `>= 3.12`
- **uv**: Fast Python package installer and resolver ([Installation Guide](https://github.com/astral-sh/uv))
- *(Optional for runtime sandboxing)*:
  - Node.js (for JavaScript execution)
  - JDK 17+ (`javac` / `java` for Java execution)
  - Go 1.21+ (for Go execution)

---

## ⚡ Quick Start

### 1. Install Dependencies

From this `backend` directory, synchronize the environment and install dependencies using `uv`:

```powershell
uv sync
```

This creates a local `.venv` and installs all packages defined in `pyproject.toml` (`fastapi`, `uvicorn`, `tree-sitter`, parsers, etc.).

---

### 2. Run the Development Server

Start the Uvicorn server with hot reloading enabled:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Once running:
- **API Base URL**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check Endpoint**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

### 3. Run the Test Suite

Run unit and integration tests using `pytest`:

```powershell
uv run pytest
```

---

## 🛠️ Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service info and supported languages |
| `GET` | `/api/health` | Runtime environment health & installed compilers |
| `POST` | `/api/transpile` | Parses source code to IR and generates target language code |
| `POST` | `/api/verify` | Runs source & target code in sandboxes and compares stdout |
| `GET` | `/api/examples` | Curated algorithmic presets (Fibonacci, Bubble Sort, etc.) |

---

## 🔍 Troubleshooting

- **Port 8000 already in use**:
  ```powershell
  # Find process using port 8000
  Get-NetTCPConnection -LocalPort 8000
  # Or start on alternative port:
  uv run uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
  ```

- **Reinstall or clean environment**:
  ```powershell
  Remove-Item -Recurse -Force .venv
  uv sync
  ```

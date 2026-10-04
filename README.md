# PolyBridge — A Scoped Multi-Language Transpiler with Web Playground and Behavioral Verification

**PolyBridge** is a transparent, inspectable educational source-to-source compiler (transpiler) that translates a procedural-plus-functions subset of **Python, JavaScript, Java, and Go** through a shared Intermediate Representation (IR).

It validates translation correctness through an execution-based **behavioral equivalence testing harness** and exposes the full compilation pipeline (Concrete Syntax Tree, Universal IR, and translated code) through an interactive React Web Playground.

---

## 🏛️ System Architecture

```text
                     ┌────────────────────────┐
                     │   Source Source Code   │
                     │ (Python / JS / Java / Go)
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │   Tree-sitter Parser   │
                     │ Concrete Syntax Tree   │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │ Scope & Limits Check   │
                     │  (≤ 300 lines, no OO)  │
                     └───────────┬────────────┘
                                 │
                                 ▼
                     ┌────────────────────────┐
                     │  AST Visitor & Inferrer│
                     │  Universal Agnostic IR │
                     └───────────┬────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
                 ▼                               ▼
     ┌────────────────────────┐      ┌────────────────────────┐
     │ Target Emitter Module  │      │ JSON / D3 Tree Export  │
     │ (Java, Go, JS, Python) │      │ (Visual AST Hierarchy) │
     └───────────┬────────────┘      └────────────────────────┘
                 │
                 ▼
     ┌────────────────────────────────────────────────────────┐
     │         Behavioral Equivalence Verification            │
     │ Subprocess Sandbox ──▶ Output Normalizer ──▶ Diff View │
     └────────────────────────────────────────────────────────┘
```

---

## ✨ Key Features

- **No AI / 100% Deterministic**: Built entirely on classical compiler design principles (Lexing $\rightarrow$ CST $\rightarrow$ Universal IR $\rightarrow$ Code Generation).
- **Multi-Language Tree-sitter Parsers**: Robust CST extraction for Python, JavaScript, Java, and Go.
- **Hub-and-Spoke IR Model**: Avoids $N \times (N-1)$ translation pairs by utilizing a single language-agnostic Intermediate Representation.
- **Local Type Inference**: Automatically infers static types for variables, expressions, and function signatures to generate valid Java and Go code from dynamic Python/JS.
- **Deterministic Emitters**: Boilerplate-aware code generators (wraps Java in `class Solution` & `public static void main`, Go in `package main` & `func main()`).
- **Behavioral Equivalence Harness**: Subprocess sandbox that executes source and target programs with identical inputs, normalizes floating-point / array formatting, and verifies stdout equality.
- **Interactive 3-Panel Playground**: Monaco Editor + Interactive SVG IR Tree Visualizer + Execution Console & Unified Diff.
- **Curated Algorithm Presets**: 1-click loading for Bubble Sort, Binary Search, Fibonacci, Prime Number Check, Factorial, and Linear Search.

---

## 📁 Repository Structure

```text
PolyBridge/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI server & endpoints
│   │   ├── ir/
│   │   │   ├── nodes.py             # Language-agnostic IR dataclasses & D3 tree export
│   │   │   └── type_infer.py        # Static type inference engine
│   │   ├── parsers/
│   │   │   ├── python_parser.py     # Tree-sitter Python -> IR
│   │   │   ├── js_parser.py         # Tree-sitter JavaScript -> IR
│   │   │   ├── java_parser.py       # Tree-sitter Java -> IR
│   │   │   └── go_parser.py         # Tree-sitter Go -> IR
│   │   ├── emitters/
│   │   │   ├── python_emitter.py    # IR -> Python 3
│   │   │   ├── js_emitter.py        # IR -> JavaScript ES6
│   │   │   ├── java_emitter.py      # IR -> Java 17 (class Solution wrapper)
│   │   │   └── go_emitter.py        # IR -> Go 1.21 (package main wrapper)
│   │   ├── sandbox/
│   │   │   ├── runner.py            # Subprocess execution harness
│   │   │   └── normalizer.py        # Output normalization & unified diff
│   │   ├── examples/
│   │   │   └── preset_algorithms.py # Curated algorithm test cases
│   │   └── validator.py             # Scope and line limit validation
│   ├── tests/                       # Comprehensive pytest suite (12/12 passing)
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/                        # React + TypeScript + Vite Web Playground
│   ├── src/
│   │   ├── components/
│   │   │   ├── IRTreeViewer.tsx     # Interactive SVG AST tree with zoom/pan
│   │   │   └── VerificationDiff.tsx # Side-by-side console & diff view
│   │   ├── App.tsx                  # Master 3-panel split layout
│   │   └── index.css                # Custom dark developer theme
│   └── package.json
└── README.md
```

---

## 🚀 Getting Started

### 1. Backend Setup

Prerequisites: Python 3.12+ and `uv`

```powershell
cd backend
# Create virtual environment and install dependencies
uv sync

# Run backend test suite
uv run pytest

# Start FastAPI development server
uv run uvicorn app.main:app --reload --port 8000
```
Backend API will be available at `http://127.0.0.1:8000` (Docs at `http://127.0.0.1:8000/docs`).

### 2. Frontend Setup

Prerequisites: Node.js 18+ and `npm`

```powershell
cd frontend
# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Web Playground will open at `http://localhost:5173`.

---

## 👥 Authors & Academic Context

**Ramdeobaba University** — Department of Computer Science and Engineering  
**Project**: B.Tech CSE Capstone Project (Session 2026–27)

- **Saumya Khobragade** (Roll No. 56)
- **Ayush Dutta** (Roll No. 22)
- **Krish Parothi** (Roll No. 15)
- **Hardik Sharma** (Roll No. 47)

**Under the Guidance of:** Dr. Padma Adane
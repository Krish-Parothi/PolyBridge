# PolyBridge — Multi-Source, Multi-Target Transpilation Platform

**PolyBridge** is a transparent, inspectable multi-source, multi-target source-to-source compiler (transpiler) that translates between **Python 3, JavaScript ES6, Java 17, Go 1.21, C++20, Arduino C++, and Verilog 2001 (HDL)** through a shared Universal Intermediate Representation (IR).

It validates translation correctness through an execution-based **behavioral equivalence testing harness** and exposes the full compilation pipeline (Concrete Syntax Tree, Universal IR, and translated code) through an interactive React Web Playground.

---

## 🏛️ System Architecture

```text
                     ┌───────────────────────────────────────────────┐
                     │              Source Code                      │
                     │ (Python, JS, Java, Go, C++, Arduino, Verilog) │
                     └───────────────────────┬───────────────────────┘
                                             │
                                             ▼
                     ┌───────────────────────────────────────────────┐
                     │          Tree-sitter AST Extraction           │
                     └───────────────────────┬───────────────────────┘
                                             │
                                             ▼
                     ┌───────────────────────────────────────────────┐
                     │        Scope Validation & Diagnostics         │
                     └───────────────────────┬───────────────────────┘
                                             │
                                             ▼
                     ┌───────────────────────────────────────────────┐
                     │       Type Inference & Universal IR           │
                     └───────────────────────┬───────────────────────┘
                                             │
                             ┌───────────────┴───────────────┐
                             │                               │
                             ▼                               ▼
                 ┌───────────────────────┐       ┌───────────────────────┐
                 │ Target Language       │       │ Interactive Visual IR │
                 │ Emitters (7 Targets)  │       │ Explorer & RTL View   │
                 └───────────┬───────────┘       └───────────────────────┘
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
│   │   │   ├── nodes.py             # Language-agnostic IR dataclasses & tree export
│   │   │   ├── cfg.py               # CFG and three-address inspection views
│   │   │   ├── optimizer.py         # Conservative semantics-preserving passes
│   │   │   ├── validation.py        # IR invariant checks
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

## Compiler pipeline

Each request follows the same inspectable sequence:

```text
source text
  -> Tree-sitter CST
  -> parser diagnostics
  -> Universal IR
  -> type inference and semantic analysis
  -> IR validation
  -> optional optimization
  -> target emitter
  -> target compilation/simulation
  -> normalized behavioral comparison
```

The IR keeps structured expressions and control-flow statements language-neutral
where possible. `app.ir.cfg` exposes basic blocks, explicit edges, and a TAC
view for inspection; the existing emitters still consume the structured IR.
The optimizer is conservative and can be controlled through the API using
`optimize` and `optimization_level`. Responses include `ir_before`, `ir_after`,
optimization statistics, CFG data, and TAC data.

## Supported constructs and limits

The reliable common subset is procedural code: scalar values, arrays/slices,
function calls (including recursion), assignments, arithmetic and comparisons,
conditionals, `while`/`for` loops, range/foreach loops, returns, printing, and
selected standard-library mappings. The seven frontends retain source-specific
handling for Java wrappers, Arduino `setup`/`loop`, and Verilog RTL/testbench
modules.

The project intentionally rejects or diagnoses unsupported features instead of
silently translating them. Current limits include user-defined classes and
inheritance in the procedural subset, arbitrary external packages, dynamic heap
allocation in the scoped C++/Arduino subset, Verilog gate primitives and
`inout` ports, and language features without a corresponding IR node. A valid
parse does not by itself prove semantic equivalence for constructs outside this
common subset.

## Behavioral and hardware verification

`/api/verify` executes source and target programs in separate temporary
subprocesses with the same stdin. It reports compilation failures, runtime
failures, timeouts, unavailable runtimes, output mismatches, and verified
matches separately. `test_inputs` can provide multiple inputs; a match is only
reported when every case executes successfully and compares equal.

Software targets are compiled/run with their local toolchains. C++ uses a C++20
compiler, Java uses `javac`/`java`, and Go uses `go build` before execution.
Arduino uses a host-side mocked `Serial`/`delay` core for deterministic sketch
checks; it is not a substitute for board or Wokwi validation. Verilog is kept
on a separate HDL path and is compiled/simulated with Icarus Verilog when
`iverilog` and `vvp` are installed. If a simulator is unavailable, the result
is explicitly `runtime_unavailable` rather than a successful verification.

The local runner uses temporary files, bounded subprocess timeouts, cleanup, and
controlled compiler argument lists. It is a development sandbox, not a
security boundary against a hostile multi-tenant workload: production
deployment should add OS/container isolation, cgroups or job objects for
memory limits, a read-only filesystem, seccomp/AppContainer policy, and a
separate worker service before accepting untrusted code.

## Verification commands

From `backend/`:

```powershell
uv sync
uv run pytest -q
```

From `frontend/`:

```powershell
npm install
npm run lint
npm run build
```

The regression suite includes the seven-language compatibility sample matrix,
C++ canonical and range-for cases, actual C++/Arduino/Verilog execution,
optimizer/CFG/TAC checks, multiple-input verification, parser diagnostics, and
frontend API contracts. Toolchain availability still matters for local runs;
the health endpoint reports the detected compilers and simulators.

## 👥 Authors & Academic Context

**Ramdeobaba University** — Department of Computer Science and Engineering  
**Project**: B.Tech CSE Capstone Project (Session 2026–27)

- **Saumya Khobragade** (Roll No. 56)
- **Ayush Dutta** (Roll No. 22)
- **Krish Parothi** (Roll No. 15)
- **Hardik Sharma** (Roll No. 47)

**Under the Guidance of:** Dr. Padma Adane

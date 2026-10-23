# PolyBridge Phase 2 — Multi-Source, Multi-Target Transpilation Platform

## 1. Executive Summary

Phase 2 expands PolyBridge from a 4-language transpiler into a **multi-source, multi-target compiler workbench** supporting **7 languages**:
1. **Python 3**
2. **Java 17**
3. **JavaScript (ES6)**
4. **Go 1.21**
5. **C++20**
6. **Verilog 2001 (Hardware HDL)**
7. **Arduino C++ (.ino)**

Every translation adheres to the strict compiler architecture:
$$\text{Source Code} \longrightarrow \text{Tree-sitter Frontend} \longrightarrow \text{AST} \longrightarrow \text{Universal IR} \longrightarrow \text{Target Emitter} \longrightarrow \text{Target Code}$$

No direct source-to-target shortcuts or ad-hoc templates are used. Hardware description semantics are preserved without forcing unsuitable abstractions into general-purpose software IR.

---

## 2. Implemented Frontends (Parsers)

All 7 frontends parse source code into Universal Intermediate Representation (`Program`, `FunctionDef`, `Statement`, `Expression`, `IRType`):

| Language | Parser Module | AST Library | Key Parsing Capabilities |
| :--- | :--- | :--- | :--- |
| **Python 3** | [`app.parsers.python_parser.PythonParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/python_parser.py) | `tree_sitter_python` | Defs, loops, lists, slices, floor div (`//`), type annotations, standard libraries (`math`, `numpy`, `pandas`). |
| **JavaScript (ES6)** | [`app.parsers.js_parser.JavaScriptParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/js_parser.py) | `tree_sitter_javascript` | Functions, `let`/`const`, arrays, arrow expressions, `console.log`, `Math` object methods. |
| **Java 17** | [`app.parsers.java_parser.JavaParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/java_parser.py) | `tree_sitter_java` | Class unwrapping, static methods, primitive types, array types (`int[]`), `System.out.println`. |
| **Go 1.21** | [`app.parsers.go_parser.GoParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/go_parser.py) | `tree_sitter_go` | `func`, slices (`[]int`), short var declaration (`:=`), `fmt.Println`, `main()` body extraction. |
| **C++20** | [`app.parsers.cpp_parser.CppParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/cpp_parser.py) | `tree_sitter_cpp` | Top-level functions, `std::vector<T>`, `std::cout << ... << std::endl`, primitive types, counted `for` loops, `main()` extraction. |
| **Arduino C++** | [`app.parsers.arduino_parser.ArduinoParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/arduino_parser.py) | `tree_sitter_cpp` | Extracts procedural logic from `void setup()`, translates `Serial.println(...)` & `printValue(...)`, parses helper functions. |
| **Verilog 2001** | [`app.parsers.verilog_parser.VerilogParser`](file:///e:/Projects/PolyBridge/backend/app/parsers/verilog_parser.py) | `tree_sitter_verilog` | Module ports (inputs $\to$ params, outputs $\to$ return), `always @(*)`, continuous `assign`, testbench `initial begin` parsing. |

---

## 3. Implemented Target Emitters

All 7 target emitters lower Universal IR to idiomatic, standard-compliant code:

| Language | Emitter Module | Standards & Features |
| :--- | :--- | :--- |
| **Python 3** | [`app.emitters.python_emitter.PythonEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/python_emitter.py) | Clean PEP 8 Python, indented blocks, native list literals. |
| **JavaScript** | [`app.emitters.js_emitter.JavaScriptEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/js_emitter.py) | Modern ES6 syntax, `console.log`, `Math.floor`. |
| **Java 17** | [`app.emitters.java_emitter.JavaEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/java_emitter.py) | Standard wrapper `public class Solution`, static methods, `main()`. |
| **Go 1.21** | [`app.emitters.go_emitter.GoEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/go_emitter.py) | `package main`, `import "fmt"`, slice operations, `func main()`. |
| **C++20** | [`app.emitters.cpp_emitter.CppEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/cpp_emitter.py) | `#include <iostream>`, `#include <vector>`, typed signatures, `int main()`. |
| **Arduino C++** | [`app.emitters.arduino_emitter.ArduinoEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/arduino_emitter.py) | Microcontroller sketch with `setup()`, `loop()`, embedded static `Vector<T>`, zero-heap allocation. |
| **Verilog 2001** | [`app.emitters.verilog_emitter.VerilogEmitter`](file:///e:/Projects/PolyBridge/backend/app/emitters/verilog_emitter.py) | Synthesizable IEEE 1364-2001 RTL (combinational / clocked FSM) and self-checking testbenches. |

---

## 4. Compatibility Matrix (Actual Test Results)

The $7 \times 7 = 49$ translation matrix was verified with automated regression tests in [`backend/tests/test_phase2_compatibility.py`](file:///e:/Projects/PolyBridge/backend/tests/test_phase2_compatibility.py):

| Source \ Target | Python 3 | JavaScript | Java 17 | Go 1.21 | C++20 | Arduino C++ | Verilog 2001 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Python 3** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **JavaScript** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Java 17** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Go 1.21** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **C++20** | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Arduino C++**| ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |
| **Verilog 2001**| ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS | ✅ PASS |

**Pass Rate**: 49 / 49 combinations (100% automated pass).

---

## 5. Supported Language Constructs

### Core Language-Independent Constructs
- **Functions**: Parameter list with type annotations, return statements, multiple functions.
- **Variables**: Typed declarations, variable assignments, augmented assignments (`+=`, `-=`, etc.).
- **Control Flow**:
  - `if` / `else if` / `else` conditional branching.
  - `while` loops with arbitrary conditions.
  - Counted `for` range loops (`for i in range(...)` $\leftrightarrow$ `for (int i = 0; i < n; i++)`).
- **Operators**:
  - Arithmetic: `+`, `-`, `*`, `/`, `//` (floor div helper), `%`.
  - Relational: `==`, `!=`, `<`, `<=`, `>`, `>=`.
  - Logical: `and` / `&&`, `or` / `||`, `not` / `!`.
- **Data Structures**: Fixed & dynamic 1D arrays (`list`, `int[]`, `[]int`, `std::vector<int>`), element indexing `arr[i]`, array length queries.
- **I/O & Diagnostics**: Standard console output (`print`, `console.log`, `System.out.println`, `fmt.Println`, `std::cout`, `Serial.println`, `$display`).

---

## 6. Known Translation Limitations & Explicit Diagnostics

PolyBridge enforces strict scope validation with structured diagnostics to avoid undefined semantic mismatches:

1. **Object-Oriented Programming (OOP)**:
   - User-defined classes, inheritance (`extends`, `implements`), virtual methods, and custom constructors are rejected.
   - *Diagnostic*: `Scope violation: Class inheritance (extends / implements) is not supported in PolyBridge.`
2. **Dynamic Memory Allocation**:
   - Raw pointers, manual pointer arithmetic, `new`, `delete`, `malloc()`, and `free()` are rejected.
   - *Diagnostic*: `Scope violation: Dynamic heap allocation (new/malloc) is not supported in scoped procedural IR.`
3. **Hardware HDL Constraints (Verilog)**:
   - Multi-clock asynchronous domain crossings cannot be lowered to procedural single-threaded code.
   - Bidirectional tri-state buses (`inout`) and high-impedance `1'bz` states cannot be represented in procedural IR.
   - *Diagnostic*: `Scope violation: Bidirectional 'inout' tri-state ports cannot be mapped to procedural IR.`
   - Gate-level structural primitives (`nand`, `bufif0`, etc.) require behavioral RTL rewriting.
   - *Diagnostic*: `Scope violation: Gate-level structural primitive '<gate>' is not supported. Use RTL behavioral logic.`
4. **External Libraries**:
   - Only curated algorithmic libraries (`math`, `numpy`, `pandas`) are mapped. Arbitrary third-party imports trigger scope errors.

---

## 7. Regression Test Results

- **Backend Total Tests**: 175 passed (0 failed, 1 warning) in 45.36s.
  - Phase 2 Compatibility Matrix: 70 passed.
  - Phase 1 Core & Correctness Suites: 105 passed.
- **Frontend Production Build**: Clean build with Vite & TypeScript (`tsc -b && vite build`) producing 0 errors.

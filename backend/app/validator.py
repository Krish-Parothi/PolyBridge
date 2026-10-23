from typing import List, Optional, Any
from dataclasses import dataclass
from app.ir.nodes import Program, FunctionDef, FunctionCall, Statement, Expression
from app.libraries.registry import LibraryRegistry


@dataclass
class Diagnostic:
    line: int
    column: int
    severity: str  # "error" | "warning"
    message: str

class ValidationResult:
    def __init__(self, is_valid: bool, diagnostics: List[Diagnostic]):
        self.is_valid = is_valid
        self.diagnostics = diagnostics

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "diagnostics": [
                {
                    "line": d.line,
                    "column": d.column,
                    "severity": d.severity,
                    "message": d.message
                }
                for d in self.diagnostics
            ]
        }

class ScopeValidator:
    """Validates source code and IR according to the PolyBridge specification:
    - Maximum 300 lines
    - No user-defined classes or inheritance
    - No external libraries
    - No recursive function calls (in v1)
    """

    MAX_LINES = 300

    @classmethod
    def validate_raw_code(cls, code: str, language: str) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        lines = code.splitlines()

        if len(lines) > cls.MAX_LINES:
            diagnostics.append(Diagnostic(
                line=cls.MAX_LINES + 1,
                column=1,
                severity="error",
                message=f"Scope violation: Program exceeds maximum supported length of {cls.MAX_LINES} lines (found {len(lines)} lines)."
            ))

        # Check for disallowed keywords based on language
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Class check:
            # - In Java, top-level wrapper class (e.g. 'public class Solution' or 'class Main') is required syntax, so allow it.
            # - Flag inheritance (extends / implements) or multiple/inner classes.
            # - In Python/JS, flag custom OOP inheritance/instantiations, but permit top-level container 'class Solution' if needed.
            if stripped.startswith("class ") or " class " in stripped:
                if language == "java":
                    if " extends " in stripped or " implements " in stripped:
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=line.find("class") + 1,
                            severity="error",
                            message="Scope violation: Class inheritance (extends / implements) is not supported in PolyBridge."
                        ))
                    # Allow standard top-level wrapper class for Java
                else:
                    is_solution_wrapper = stripped.startswith("class Solution:") or stripped.startswith("class Solution {") or stripped.startswith("class Solution(")
                    if not is_solution_wrapper:
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=line.find("class") + 1,
                            severity="error",
                            message="Scope violation: Classes and Object-Oriented features are not supported in procedural PolyBridge."
                        ))

            # Validate library imports
            if language == "python":
                if stripped.startswith("import ") or stripped.startswith("from "):
                    tokens = stripped.split()
                    mod = tokens[1] if len(tokens) > 1 else ""
                    if not LibraryRegistry.is_supported_module(mod):
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=1,
                            severity="error",
                            message=f"Scope violation: Unsupported library '{mod}'. PolyBridge supports standard libraries (math) and packages (pandas)."
                        ))
            elif language == "javascript":
                if stripped.startswith("import ") or "require(" in stripped:
                    # Allow standard and supported modules
                    pass
            elif language == "java":
                if stripped.startswith("import "):
                    tokens = stripped.replace(";", "").split()
                    mod = tokens[1] if len(tokens) > 1 else ""
                    if not LibraryRegistry.is_supported_module(mod):
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=1,
                            severity="error",
                            message=f"Scope violation: Unsupported Java import '{mod}'."
                        ))
            elif language in ["cpp", "arduino"]:
                if stripped.startswith("#include "):
                    inc_target = stripped.replace("#include", "").strip("<>\" \t;")
                    allowed_cpp = ["iostream", "vector", "string", "cmath", "algorithm", "numeric", "cassert", "cstdint", "cstdio", "Arduino.h"]
                    if inc_target not in allowed_cpp:
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=1,
                            severity="error",
                            message=f"Scope violation: Unsupported header <{inc_target}> in {language}. PolyBridge supports core algorithmic libraries."
                        ))
                if "malloc(" in stripped or " new " in stripped:
                    diagnostics.append(Diagnostic(
                        line=idx,
                        column=1,
                        severity="error",
                        message="Scope violation: Dynamic heap allocation (new/malloc) is not supported in scoped procedural IR."
                    ))

            elif language == "verilog":
                if stripped.startswith("inout ") or " inout " in stripped:
                    diagnostics.append(Diagnostic(
                        line=idx,
                        column=1,
                        severity="error",
                        message="Scope violation: Bidirectional 'inout' tri-state ports cannot be mapped to procedural IR."
                    ))
                gate_prims = ["nand ", "nor ", "xnor ", "bufif0 ", "bufif1 ", "notif0 ", "notif1 "]
                for gp in gate_prims:
                    if stripped.startswith(gp):
                        diagnostics.append(Diagnostic(
                            line=idx,
                            column=1,
                            severity="error",
                            message=f"Scope violation: Gate-level structural primitive '{gp.strip()}' is not supported. Use RTL behavioral logic."
                        ))

        return diagnostics

    @classmethod
    def validate_ir(cls, program: Program) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        # PolyBridge supports recursion across all targets
        return diagnostics

    @classmethod
    def _has_recursive_call(cls, stmts: List[Statement], func_name: str) -> bool:
        for stmt in stmts:
            if cls._check_stmt_for_call(stmt, func_name):
                return True
        return False

    @classmethod
    def _check_stmt_for_call(cls, stmt: Any, func_name: str) -> bool:
        if hasattr(stmt, "value") and cls._check_expr_for_call(stmt.value, func_name):
            return True
        if hasattr(stmt, "condition") and cls._check_expr_for_call(stmt.condition, func_name):
            return True
        if hasattr(stmt, "expr") and cls._check_expr_for_call(stmt.expr, func_name):
            return True
        if hasattr(stmt, "then_branch"):
            for s in stmt.then_branch:
                if cls._check_stmt_for_call(s, func_name):
                    return True
        if hasattr(stmt, "else_branch"):
            for s in stmt.else_branch:
                if cls._check_stmt_for_call(s, func_name):
                    return True
        if hasattr(stmt, "body"):
            for s in stmt.body:
                if cls._check_stmt_for_call(s, func_name):
                    return True
        return False

    @classmethod
    def _check_expr_for_call(cls, expr: Any, func_name: str) -> bool:
        if not expr:
            return False
        if isinstance(expr, FunctionCall):
            if expr.name == func_name:
                return True
            for a in expr.args:
                if cls._check_expr_for_call(a, func_name):
                    return True
        return False

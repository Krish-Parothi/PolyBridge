from typing import List, Optional, Any
from dataclasses import dataclass
from app.ir.nodes import Program, FunctionDef, FunctionCall, Statement, Expression


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
            # Disallow classes
            if stripped.startswith("class ") or " class " in stripped:
                diagnostics.append(Diagnostic(
                    line=idx,
                    column=line.find("class") + 1,
                    severity="error",
                    message="Scope violation: Classes and Object-Oriented features are not supported in procedural PolyBridge v1."
                ))

            # Disallow external imports
            if language == "python":
                if stripped.startswith("import ") or stripped.startswith("from "):
                    diagnostics.append(Diagnostic(
                        line=idx,
                        column=1,
                        severity="error",
                        message="Scope violation: External library imports are disallowed in PolyBridge v1."
                    ))
            elif language == "javascript":
                if stripped.startswith("import ") or "require(" in stripped:
                    diagnostics.append(Diagnostic(
                        line=idx,
                        column=1,
                        severity="error",
                        message="Scope violation: External module imports/require are disallowed in PolyBridge v1."
                    ))
            elif language == "java":
                if stripped.startswith("import ") and not stripped.startswith("import java.util.Arrays"):
                    diagnostics.append(Diagnostic(
                        line=idx,
                        column=1,
                        severity="error",
                        message="Scope violation: External package imports are disallowed in PolyBridge v1."
                    ))

        return diagnostics

    @classmethod
    def validate_ir(cls, program: Program) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        # Check for recursion (v1 limitation)
        for fn in program.functions:
            if cls._has_recursive_call(fn.body, fn.name):
                diagnostics.append(Diagnostic(
                    line=1,
                    column=1,
                    severity="error",
                    message=f"Scope violation: Recursive function call detected in '{fn.name}()'. PolyBridge v1 supports iterative procedural algorithms only."
                ))

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

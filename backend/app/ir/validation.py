"""Structural validation for Universal IR before it reaches an emitter."""

from __future__ import annotations

from typing import List, Optional

from app.ir.cfg import build_cfg
from app.ir.nodes import (
    ArrayAccess,
    ArrayLength,
    ArrayLiteral,
    Assignment,
    BinaryOp,
    CastExpr,
    DoWhileStmt,
    Expression,
    ExpressionStmt,
    ForEachStmt,
    ForRangeStmt,
    FunctionCall,
    FunctionDef,
    IfStmt,
    MethodCall,
    Program,
    ReturnStmt,
    Statement,
    TernaryOp,
    UnaryOp,
    VarDecl,
    WhileStmt,
)


class IRValidator:
    """Checks invariants that are independent of a particular target language."""

    def validate(self, program: Program) -> List[str]:
        errors: List[str] = []
        if not isinstance(program, Program):
            return ["IR root must be a Program"]

        function_names = set()
        for fn in program.functions:
            if not fn.name:
                errors.append("Function name cannot be empty")
            if fn.name in function_names:
                errors.append(f"Duplicate function '{fn.name}'")
            function_names.add(fn.name)
            if len({p.name for p in fn.params}) != len(fn.params):
                errors.append(f"Function '{fn.name}' has duplicate parameters")
            self._validate_statements(fn.body, f"function {fn.name}", errors)
            errors.extend(f"{fn.name}: {e}" for e in build_cfg(fn).validate())

        self._validate_statements(program.global_statements, "global scope", errors)
        return errors

    def _validate_statements(self, statements: List[Statement], context: str, errors: List[str]) -> None:
        for index, stmt in enumerate(statements):
            if stmt is None:
                errors.append(f"{context}: statement {index} is null")
                continue
            if isinstance(stmt, VarDecl):
                if not stmt.name:
                    errors.append(f"{context}: declaration {index} has no name")
                self._validate_expr(stmt.initializer, f"{context} declaration {stmt.name}", errors)
            elif isinstance(stmt, Assignment):
                self._validate_expr(stmt.target, f"{context} assignment target", errors)
                self._validate_expr(stmt.value, f"{context} assignment value", errors)
            elif isinstance(stmt, (IfStmt, WhileStmt, DoWhileStmt)):
                self._validate_expr(stmt.condition, f"{context} condition", errors)
                self._validate_statements(stmt.then_branch if isinstance(stmt, IfStmt) else stmt.body, context, errors)
                if isinstance(stmt, IfStmt):
                    self._validate_statements(stmt.else_branch, context, errors)
            elif isinstance(stmt, ForRangeStmt):
                if not stmt.var_name:
                    errors.append(f"{context}: range loop has no iterator")
                self._validate_expr(stmt.start, f"{context} range start", errors)
                self._validate_expr(stmt.end, f"{context} range end", errors)
                self._validate_expr(stmt.step, f"{context} range step", errors)
                self._validate_statements(stmt.body, context, errors)
            elif isinstance(stmt, ForEachStmt):
                self._validate_expr(stmt.iterable, f"{context} iterable", errors)
                self._validate_statements(stmt.body, context, errors)
            elif isinstance(stmt, ReturnStmt):
                self._validate_expr(stmt.value, f"{context} return", errors)
            elif isinstance(stmt, ExpressionStmt):
                self._validate_expr(stmt.expr, f"{context} expression", errors)
            elif hasattr(stmt, "value"):
                self._validate_expr(getattr(stmt, "value", None), f"{context} statement", errors)

    def _validate_expr(self, expr: Optional[Expression], context: str, errors: List[str]) -> None:
        if expr is None:
            return
        if isinstance(expr, BinaryOp):
            if expr.left is None or expr.right is None:
                errors.append(f"{context}: binary operator '{expr.op}' has a missing operand")
            self._validate_expr(expr.left, context, errors)
            self._validate_expr(expr.right, context, errors)
        elif isinstance(expr, UnaryOp):
            self._validate_expr(expr.operand, context, errors)
        elif isinstance(expr, (ArrayAccess, TernaryOp, CastExpr, MethodCall)):
            for value in self._children(expr):
                self._validate_expr(value, context, errors)
        elif isinstance(expr, ArrayLength):
            self._validate_expr(expr.array, context, errors)
        elif isinstance(expr, ArrayLiteral):
            for value in expr.elements:
                self._validate_expr(value, context, errors)
        elif isinstance(expr, FunctionCall):
            if not expr.name:
                errors.append(f"{context}: function call has no name")
            for arg in expr.args:
                self._validate_expr(arg, context, errors)

    @staticmethod
    def _children(expr: Expression) -> List[Optional[Expression]]:
        if isinstance(expr, ArrayAccess):
            return [expr.array, expr.index]
        if isinstance(expr, TernaryOp):
            return [expr.condition, expr.then_expr, expr.else_expr]
        if isinstance(expr, CastExpr):
            return [expr.operand]
        if isinstance(expr, MethodCall):
            return [expr.object_expr, *expr.args]
        return []


def validate_ir(program: Program) -> List[str]:
    return IRValidator().validate(program)

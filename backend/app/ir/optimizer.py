"""Conservative, target-independent Universal IR optimization passes."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.ir.nodes import (
    ArrayAccess,
    ArrayLength,
    ArrayLiteral,
    Assignment,
    AugmentedAssignment,
    BinaryOp,
    BreakStmt,
    CastExpr,
    ContinueStmt,
    DoWhileStmt,
    Expression,
    ExpressionStmt,
    ForEachStmt,
    ForRangeStmt,
    FunctionCall,
    FunctionDef,
    Identifier,
    IfStmt,
    Literal,
    MethodCall,
    PrintStmt,
    Program,
    ReturnStmt,
    Statement,
    TernaryOp,
    UnaryOp,
    VarDecl,
    WhileStmt,
)


@dataclass
class OptimizationConfig:
    enabled: bool = True
    constant_folding: bool = True
    constant_propagation: bool = True
    dead_code_elimination: bool = True
    common_subexpression_elimination: bool = True
    algebraic_simplification: bool = True
    unreachable_code_elimination: bool = True


@dataclass
class OptimizationStats:
    before_nodes: int = 0
    after_nodes: int = 0
    constants_folded: int = 0
    constants_propagated: int = 0
    algebraic_simplifications: int = 0
    dead_statements_removed: int = 0
    unreachable_statements_removed: int = 0
    common_subexpressions_reused: int = 0
    passes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "before_nodes": self.before_nodes,
            "after_nodes": self.after_nodes,
            "constants_folded": self.constants_folded,
            "constants_propagated": self.constants_propagated,
            "algebraic_simplifications": self.algebraic_simplifications,
            "dead_statements_removed": self.dead_statements_removed,
            "unreachable_statements_removed": self.unreachable_statements_removed,
            "common_subexpressions_reused": self.common_subexpressions_reused,
            "passes": list(self.passes),
        }


class IROptimizer:
    """Applies only semantics-preserving transformations to structured IR.

    The optimizer intentionally avoids changing loop shape, integer widths, or
    hardware scheduling.  This keeps the same conservative pass set valid for
    software targets, Arduino sketches, and the Verilog HLS view.
    """

    def __init__(self, config: Optional[OptimizationConfig] = None, target_language: str = "python") -> None:
        self.config = config or OptimizationConfig()
        self.target_language = target_language.lower()
        self.stats = OptimizationStats()

    def optimize(self, program: Program) -> Tuple[Program, OptimizationStats]:
        self.stats = OptimizationStats(before_nodes=self._count_program_nodes(program))
        if not self.config.enabled:
            self.stats.after_nodes = self.stats.before_nodes
            return program, self.stats

        for fn in program.functions:
            fn.body = self._opt_block(fn.body, {})
        program.global_statements = self._opt_block(program.global_statements, {})

        if self.stats.constants_folded:
            self.stats.passes.append("constant_folding")
        if self.stats.constants_propagated:
            self.stats.passes.append("constant_propagation")
        if self.stats.algebraic_simplifications:
            self.stats.passes.append("algebraic_simplification")
        if self.stats.common_subexpressions_reused:
            self.stats.passes.append("common_subexpression_elimination")
        if self.stats.dead_statements_removed:
            self.stats.passes.append("dead_code_elimination")
        if self.stats.unreachable_statements_removed:
            self.stats.passes.append("unreachable_code_elimination")
        self.stats.after_nodes = self._count_program_nodes(program)
        return program, self.stats

    def _opt_block(self, statements: List[Statement], env: Dict[str, Literal]) -> List[Statement]:
        result: List[Statement] = []
        cse_cache: Dict[str, str] = {}
        reachable = True

        for stmt in statements:
            if not reachable:
                self.stats.unreachable_statements_removed += 1
                continue

            if isinstance(stmt, VarDecl):
                stmt.initializer = self._opt_expr(stmt.initializer, env)
                if self.config.common_subexpression_elimination and stmt.initializer:
                    stmt.initializer = self._reuse_cse(stmt.initializer, cse_cache)
                result.append(stmt)
                if self.config.constant_propagation and isinstance(stmt.initializer, Literal):
                    env[stmt.name] = copy.deepcopy(stmt.initializer)
                else:
                    env.pop(stmt.name, None)
                self._remember_cse(stmt.initializer, stmt.name, cse_cache)
                continue

            if isinstance(stmt, Assignment):
                stmt.target = self._opt_target(stmt.target, env)
                stmt.value = self._opt_expr(stmt.value, env)
                result.append(stmt)
                if isinstance(stmt.target, Identifier) and isinstance(stmt.value, Literal):
                    env[stmt.target.name] = copy.deepcopy(stmt.value)
                elif isinstance(stmt.target, Identifier):
                    env.pop(stmt.target.name, None)
                cse_cache.clear()
                continue

            if isinstance(stmt, AugmentedAssignment):
                stmt.target = self._opt_target(stmt.target, env)
                stmt.value = self._opt_expr(stmt.value, env)
                result.append(stmt)
                if isinstance(stmt.target, Identifier):
                    env.pop(stmt.target.name, None)
                cse_cache.clear()
                continue

            if isinstance(stmt, IfStmt):
                stmt.condition = self._opt_expr(stmt.condition, env)
                if isinstance(stmt.condition, Literal) and isinstance(stmt.condition.value, bool):
                    chosen = stmt.then_branch if stmt.condition.value else stmt.else_branch
                    discarded = stmt.else_branch if stmt.condition.value else stmt.then_branch
                    self.stats.unreachable_statements_removed += len(discarded)
                    result.extend(self._opt_block(chosen, env))
                    continue
                then_env = {k: copy.deepcopy(v) for k, v in env.items()}
                else_env = {k: copy.deepcopy(v) for k, v in env.items()}
                stmt.then_branch = self._opt_block(stmt.then_branch, then_env)
                stmt.else_branch = self._opt_block(stmt.else_branch, else_env)
                for name in set(then_env) & set(else_env):
                    if self._same_literal(then_env[name], else_env[name]):
                        env[name] = then_env[name]
                result.append(stmt)
                cse_cache.clear()
                continue

            if isinstance(stmt, WhileStmt):
                mutated = self._assigned_names(stmt.body)
                loop_env = {k: copy.deepcopy(v) for k, v in env.items() if k not in mutated}
                stmt.condition = self._opt_expr(stmt.condition, loop_env)
                if isinstance(stmt.condition, Literal) and not bool(stmt.condition.value):
                    self.stats.unreachable_statements_removed += 1 + len(stmt.body)
                    continue
                stmt.body = self._opt_block(stmt.body, loop_env)
                result.append(stmt)
                # The loop may execute zero or many times.  Do not propagate
                # pre-loop constants past potentially mutating loop bodies.
                env.clear()
                cse_cache.clear()
                continue

            if isinstance(stmt, DoWhileStmt):
                mutated = self._assigned_names(stmt.body)
                loop_env = {k: copy.deepcopy(v) for k, v in env.items() if k not in mutated}
                stmt.body = self._opt_block(stmt.body, loop_env)
                # A do-while evaluates its condition after the body.  Values
                # from before the loop must never be propagated into it.
                stmt.condition = self._opt_expr(stmt.condition, {})
                result.append(stmt)
                env.clear()
                cse_cache.clear()
                continue

            if isinstance(stmt, ForRangeStmt):
                stmt.start = self._opt_expr(stmt.start, env)
                stmt.end = self._opt_expr(stmt.end, env)
                stmt.step = self._opt_expr(stmt.step, env)
                mutated = self._assigned_names(stmt.body) | {stmt.var_name}
                loop_env = {k: copy.deepcopy(v) for k, v in env.items() if k not in mutated}
                stmt.body = self._opt_block(stmt.body, loop_env)
                result.append(stmt)
                env.clear()
                cse_cache.clear()
                continue

            if isinstance(stmt, ForEachStmt):
                stmt.iterable = self._opt_expr(stmt.iterable, env)
                mutated = self._assigned_names(stmt.body) | {stmt.var_name}
                loop_env = {k: copy.deepcopy(v) for k, v in env.items() if k not in mutated}
                stmt.body = self._opt_block(stmt.body, loop_env)
                result.append(stmt)
                env.clear()
                cse_cache.clear()
                continue

            if isinstance(stmt, ReturnStmt):
                stmt.value = self._opt_expr(stmt.value, env)
                result.append(stmt)
                reachable = False
                continue

            if isinstance(stmt, PrintStmt):
                stmt.args = [self._opt_expr(a, env) for a in stmt.args]
                result.append(stmt)
                cse_cache.clear()
                continue

            if isinstance(stmt, ExpressionStmt):
                stmt.expr = self._opt_expr(stmt.expr, env)
                result.append(stmt)
                cse_cache.clear()
                continue

            result.append(stmt)
            if isinstance(stmt, (BreakStmt, ContinueStmt)):
                reachable = False

        if self.config.dead_code_elimination:
            result = self._remove_dead_literal_declarations(result)
        return result

    def _opt_target(self, expr: Optional[Expression], env: Dict[str, Literal]) -> Optional[Expression]:
        if isinstance(expr, ArrayAccess):
            expr.array = self._opt_expr(expr.array, env)
            expr.index = self._opt_expr(expr.index, env)
        return expr

    def _opt_expr(self, expr: Optional[Expression], env: Dict[str, Literal]) -> Optional[Expression]:
        if expr is None:
            return None
        if isinstance(expr, Identifier):
            if self.config.constant_propagation and expr.name in env:
                self.stats.constants_propagated += 1
                return copy.deepcopy(env[expr.name])
            return expr
        if isinstance(expr, BinaryOp):
            expr.left = self._opt_expr(expr.left, env)
            expr.right = self._opt_expr(expr.right, env)
            folded = self._fold_binary(expr)
            if folded is not None:
                self.stats.constants_folded += 1
                return folded
            if self.config.algebraic_simplification:
                simplified = self._simplify_binary(expr)
                if simplified is not expr:
                    self.stats.algebraic_simplifications += 1
                    return simplified
            return expr
        if isinstance(expr, UnaryOp):
            expr.operand = self._opt_expr(expr.operand, env)
            if isinstance(expr.operand, Literal):
                try:
                    value = self._eval_unary(expr.op, expr.operand.value)
                    self.stats.constants_folded += 1
                    return Literal(value)
                except (TypeError, ValueError):
                    pass
            return expr
        if isinstance(expr, ArrayLiteral):
            expr.elements = [self._opt_expr(e, env) for e in expr.elements]
            return expr
        if isinstance(expr, ArrayAccess):
            expr.array = self._opt_expr(expr.array, env)
            expr.index = self._opt_expr(expr.index, env)
            return expr
        if isinstance(expr, ArrayLength):
            expr.array = self._opt_expr(expr.array, env)
            return expr
        if isinstance(expr, FunctionCall):
            # Preserve named values at call boundaries.  Besides keeping
            # diagnostics readable, this avoids changing APIs that inspect
            # object identity or rely on target-specific argument coercion.
            expr.args = [self._opt_expr(a, {}) for a in expr.args]
            return expr
        if isinstance(expr, MethodCall):
            expr.object_expr = self._opt_expr(expr.object_expr, env)
            expr.args = [self._opt_expr(a, env) for a in expr.args]
            return expr
        if isinstance(expr, TernaryOp):
            expr.condition = self._opt_expr(expr.condition, env)
            expr.then_expr = self._opt_expr(expr.then_expr, env)
            expr.else_expr = self._opt_expr(expr.else_expr, env)
            if isinstance(expr.condition, Literal) and isinstance(expr.condition.value, bool):
                self.stats.unreachable_statements_removed += 1
                return expr.then_expr if expr.condition.value else expr.else_expr
            return expr
        if isinstance(expr, CastExpr):
            expr.operand = self._opt_expr(expr.operand, env)
            return expr
        return expr

    def _fold_binary(self, expr: BinaryOp) -> Optional[Literal]:
        if not isinstance(expr.left, Literal) or not isinstance(expr.right, Literal):
            return None
        try:
            value = self._eval_binary(expr.op, expr.left.value, expr.right.value)
        except (ArithmeticError, TypeError, ValueError):
            return None
        return Literal(value)

    @staticmethod
    def _eval_unary(op: str, value: object) -> object:
        if op in ("!", "not"):
            return not value
        if op == "+":
            return +value
        if op == "-":
            return -value
        return value

    @staticmethod
    def _eval_binary(op: str, left: object, right: object) -> object:
        operations = {
            "+": lambda: left + right,
            "-": lambda: left - right,
            "*": lambda: left * right,
            "/": lambda: left / right,
            "//": lambda: left // right,
            "%": lambda: left % right,
            "**": lambda: left ** right,
            "<": lambda: left < right,
            "<=": lambda: left <= right,
            ">": lambda: left > right,
            ">=": lambda: left >= right,
            "==": lambda: left == right,
            "===": lambda: left == right,
            "!=": lambda: left != right,
            "!==": lambda: left != right,
            "and": lambda: left and right,
            "&&": lambda: left and right,
            "or": lambda: left or right,
            "||": lambda: left or right,
            "&": lambda: left & right,
            "|": lambda: left | right,
            "^": lambda: left ^ right,
        }
        if op not in operations:
            raise ValueError(op)
        return operations[op]()

    def _simplify_binary(self, expr: BinaryOp) -> Expression:
        left, right = expr.left, expr.right
        if isinstance(right, Literal) and right.value == 0 and expr.op in ("+", "-"):
            return left
        if isinstance(right, Literal) and right.value == 1 and expr.op in ("*", "/"):
            return left
        if isinstance(left, Literal) and left.value == 0 and expr.op == "+":
            return right
        if isinstance(left, Literal) and left.value == 1 and expr.op == "*":
            return right
        if isinstance(left, Literal) and left.value == 0 and expr.op == "*" and self._pure(right):
            return Literal(0)
        return expr

    @staticmethod
    def _pure(expr: Optional[Expression]) -> bool:
        if expr is None or isinstance(expr, (Literal, Identifier)):
            return True
        if isinstance(expr, UnaryOp):
            return IROptimizer._pure(expr.operand)
        if isinstance(expr, BinaryOp):
            return IROptimizer._pure(expr.left) and IROptimizer._pure(expr.right)
        if isinstance(expr, CastExpr):
            return IROptimizer._pure(expr.operand)
        if isinstance(expr, ArrayAccess):
            return IROptimizer._pure(expr.array) and IROptimizer._pure(expr.index)
        return False

    def _reuse_cse(self, expr: Expression, cache: Dict[str, str]) -> Expression:
        if not self._pure(expr):
            return expr
        key = self._signature(expr)
        if key in cache:
            self.stats.common_subexpressions_reused += 1
            return Identifier(cache[key])
        return expr

    def _remember_cse(self, expr: Optional[Expression], name: str, cache: Dict[str, str]) -> None:
        if expr is not None and self._pure(expr):
            cache[self._signature(expr)] = name

    @staticmethod
    def _signature(expr: Expression) -> str:
        return json.dumps(expr.to_dict(), sort_keys=True, default=str)

    def _remove_dead_literal_declarations(self, statements: List[Statement]) -> List[Statement]:
        used = set()
        for stmt in statements:
            if isinstance(stmt, (Assignment, AugmentedAssignment)):
                used.update(self._names(stmt.value))
                if isinstance(stmt, AugmentedAssignment) or not isinstance(stmt.target, Identifier):
                    used.update(self._names(stmt.target))
            elif isinstance(stmt, (PrintStmt, ExpressionStmt, ReturnStmt)):
                used.update(self._names(getattr(stmt, "value", None) or getattr(stmt, "expr", None)))
            elif isinstance(stmt, IfStmt):
                used.update(self._names(stmt.condition))
                for nested in stmt.then_branch + stmt.else_branch:
                    used.update(self._names_in_stmt(nested))
            elif isinstance(stmt, (WhileStmt, DoWhileStmt)):
                used.update(self._names(stmt.condition))
                for nested in stmt.body:
                    used.update(self._names_in_stmt(nested))
            elif isinstance(stmt, (ForRangeStmt, ForEachStmt)):
                used.update(self._names(stmt.start if isinstance(stmt, ForRangeStmt) else stmt.iterable))
                if isinstance(stmt, ForRangeStmt):
                    used.update(self._names(stmt.end))
                for nested in stmt.body:
                    used.update(self._names_in_stmt(nested))

        result: List[Statement] = []
        for stmt in statements:
            if isinstance(stmt, VarDecl) and isinstance(stmt.initializer, Literal) and stmt.name not in used:
                self.stats.dead_statements_removed += 1
                continue
            result.append(stmt)
        return result

    def _names_in_stmt(self, stmt: Statement) -> set[str]:
        names = set()
        for attr in ("value", "condition", "expr", "iterable", "start", "end", "step", "target"):
            names.update(self._names(getattr(stmt, attr, None)))
        for branch in (getattr(stmt, "body", []), getattr(stmt, "then_branch", []), getattr(stmt, "else_branch", [])):
            for nested in branch:
                names.update(self._names_in_stmt(nested))
        return names

    def _assigned_names(self, statements: List[Statement]) -> set[str]:
        names: set[str] = set()
        for stmt in statements:
            if isinstance(stmt, VarDecl):
                names.add(stmt.name)
            elif isinstance(stmt, (Assignment, AugmentedAssignment)) and isinstance(stmt.target, Identifier):
                names.add(stmt.target.name)
            for branch in (
                getattr(stmt, "body", []),
                getattr(stmt, "then_branch", []),
                getattr(stmt, "else_branch", []),
            ):
                names.update(self._assigned_names(branch))
        return names

    def _names(self, expr: Optional[Expression]) -> set[str]:
        if expr is None:
            return set()
        if isinstance(expr, Identifier):
            return {expr.name}
        result = set()
        for child in self._expr_children(expr):
            result.update(self._names(child))
        return result

    @staticmethod
    def _expr_children(expr: Expression) -> List[Expression]:
        if isinstance(expr, BinaryOp):
            return [expr.left, expr.right]
        if isinstance(expr, UnaryOp):
            return [expr.operand]
        if isinstance(expr, ArrayLiteral):
            return list(expr.elements)
        if isinstance(expr, ArrayAccess):
            return [expr.array, expr.index]
        if isinstance(expr, ArrayLength):
            return [expr.array]
        if isinstance(expr, FunctionCall):
            return list(expr.args)
        if isinstance(expr, MethodCall):
            return [expr.object_expr, *expr.args]
        if isinstance(expr, TernaryOp):
            return [expr.condition, expr.then_expr, expr.else_expr]
        if isinstance(expr, CastExpr):
            return [expr.operand]
        return []

    @staticmethod
    def _same_literal(left: Literal, right: Literal) -> bool:
        return isinstance(left, Literal) and isinstance(right, Literal) and left.value == right.value

    def _count_program_nodes(self, program: Program) -> int:
        def count(value: object) -> int:
            if isinstance(value, list):
                return sum(count(item) for item in value)
            if hasattr(value, "to_dict"):
                return 1 + sum(count(v) for k, v in value.to_dict().items() if k not in {"type"})
            if isinstance(value, dict):
                return sum(count(v) for v in value.values())
            return 0
        return count(program)

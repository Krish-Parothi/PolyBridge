"""Control-flow and three-address views of the language-independent IR.

The emitters continue to consume the structured Universal IR.  This module is
an analysis/lowering view used for validation, diagnostics, optimization
statistics, and tooling; it deliberately does not replace the existing AST.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.ir.nodes import (
    Assignment,
    BinaryOp,
    BreakStmt,
    ContinueStmt,
    Expression,
    ExpressionStmt,
    ForEachStmt,
    ForRangeStmt,
    FunctionDef,
    FunctionCall,
    IfStmt,
    Identifier,
    Literal,
    PrintStmt,
    ReturnStmt,
    Statement,
    UnaryOp,
    VarDecl,
    WhileStmt,
)


@dataclass
class BasicBlock:
    """A maximal sequence of statements with one entry and one exit edge set."""

    id: int
    label: str
    statements: List[Statement] = field(default_factory=list)
    successors: List[int] = field(default_factory=list)
    predecessors: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "statements": [s.to_dict() for s in self.statements],
            "successors": list(self.successors),
            "predecessors": list(self.predecessors),
        }


@dataclass
class ControlFlowGraph:
    function_name: str
    blocks: List[BasicBlock]
    entry: int
    exits: List[int]

    def to_dict(self) -> Dict[str, object]:
        return {
            "function": self.function_name,
            "entry": self.entry,
            "exits": list(self.exits),
            "blocks": [b.to_dict() for b in self.blocks],
        }

    def validate(self) -> List[str]:
        errors: List[str] = []
        ids = {b.id for b in self.blocks}
        if self.entry not in ids:
            errors.append(f"CFG entry block {self.entry} does not exist")
        for block in self.blocks:
            for target in block.successors:
                if target not in ids:
                    errors.append(f"CFG block {block.id} points to missing block {target}")
            for source in block.predecessors:
                if source not in ids:
                    errors.append(f"CFG block {block.id} has missing predecessor {source}")
        return errors


@dataclass
class TACInstruction:
    """Small, serializable three-address instruction used for inspection."""

    op: str
    result: Optional[str] = None
    arg1: Optional[str] = None
    arg2: Optional[str] = None
    block: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "op": self.op,
            "result": self.result,
            "arg1": self.arg1,
            "arg2": self.arg2,
            "block": self.block,
        }


class CFGBuilder:
    """Build a conservative CFG from structured Universal IR statements."""

    def __init__(self) -> None:
        self.blocks: List[BasicBlock] = []

    def build_function(self, fn: FunctionDef) -> ControlFlowGraph:
        self.blocks = []
        entry = self._new_block(f"{fn.name}:entry")
        exits = self._emit_sequence(fn.body, [entry])
        if not exits:
            exits = [entry]
        self._rebuild_predecessors()
        return ControlFlowGraph(fn.name, self.blocks, entry, exits)

    def _new_block(self, label: str) -> int:
        block_id = len(self.blocks)
        self.blocks.append(BasicBlock(block_id, label))
        return block_id

    def _connect(self, source: int, target: int) -> None:
        if target not in self.blocks[source].successors:
            self.blocks[source].successors.append(target)

    def _emit_sequence(self, statements: Iterable[Statement], incoming: List[int]) -> List[int]:
        current = list(incoming)
        for stmt in statements:
            if not current:
                # Preserve unreachable statements in an isolated block so the
                # validator and diagnostics can show them explicitly.
                current = [self._new_block("unreachable")]

            if isinstance(stmt, IfStmt):
                for block_id in current:
                    self.blocks[block_id].statements.append(stmt)
                then_entry = self._new_block("if.then")
                else_entry = self._new_block("if.else")
                join = self._new_block("if.join")
                for block_id in current:
                    self._connect(block_id, then_entry)
                    self._connect(block_id, else_entry)
                then_exits = self._emit_sequence(stmt.then_branch, [then_entry])
                else_exits = self._emit_sequence(stmt.else_branch, [else_entry]) if stmt.else_branch else [else_entry]
                for block_id in then_exits + else_exits:
                    self._connect(block_id, join)
                current = [join]
                continue

            if isinstance(stmt, (WhileStmt, ForRangeStmt, ForEachStmt)):
                header = self._new_block("loop.header")
                body = self._new_block("loop.body")
                after = self._new_block("loop.after")
                for block_id in current:
                    self._connect(block_id, header)
                self.blocks[header].statements.append(stmt)
                self._connect(header, body)
                self._connect(header, after)
                body_exits = self._emit_sequence(stmt.body, [body])
                for block_id in body_exits:
                    self._connect(block_id, header)
                current = [after]
                continue

            for block_id in current:
                self.blocks[block_id].statements.append(stmt)
            if isinstance(stmt, (ReturnStmt, BreakStmt, ContinueStmt)):
                current = []
        return current

    def _rebuild_predecessors(self) -> None:
        for block in self.blocks:
            block.predecessors.clear()
        for block in self.blocks:
            for successor in block.successors:
                if block.id not in self.blocks[successor].predecessors:
                    self.blocks[successor].predecessors.append(block.id)


def build_cfg(function: FunctionDef) -> ControlFlowGraph:
    return CFGBuilder().build_function(function)


def build_program_cfg(functions: Iterable[FunctionDef]) -> Dict[str, ControlFlowGraph]:
    return {fn.name: build_cfg(fn) for fn in functions}


class TACLowerer:
    """Lower expressions and structured statements into inspectable TAC."""

    def __init__(self) -> None:
        self.instructions: List[TACInstruction] = []
        self.temp_index = 0
        self.label_index = 0

    def lower_function(self, fn: FunctionDef) -> List[TACInstruction]:
        self.instructions = []
        self.temp_index = 0
        self.label_index = 0
        self._lower_statements(fn.body)
        return list(self.instructions)

    def _temp(self) -> str:
        self.temp_index += 1
        return f"t{self.temp_index}"

    def _label(self, prefix: str = "L") -> str:
        self.label_index += 1
        return f"{prefix}{self.label_index}"

    def _emit_expr(self, expr: Optional[Expression]) -> str:
        if expr is None:
            return ""
        if isinstance(expr, Literal):
            return repr(expr.value)
        if isinstance(expr, Identifier):
            return expr.name
        if isinstance(expr, UnaryOp):
            operand = self._emit_expr(expr.operand)
            result = self._temp()
            self.instructions.append(TACInstruction("unary", result, expr.op, operand))
            return result
        if isinstance(expr, BinaryOp):
            left = self._emit_expr(expr.left)
            right = self._emit_expr(expr.right)
            result = self._temp()
            self.instructions.append(TACInstruction("binary", result, left, f"{expr.op} {right}"))
            return result
        if isinstance(expr, FunctionCall):
            args = [self._emit_expr(a) for a in expr.args]
            result = self._temp()
            self.instructions.append(TACInstruction("call", result, expr.name, ",".join(args)))
            return result
        # Array/member expressions are still represented as a single operand;
        # emitters retain the full structured node for code generation.
        result = self._temp()
        self.instructions.append(TACInstruction("expr", result, type(expr).__name__))
        return result

    def _lower_statements(self, statements: Iterable[Statement]) -> None:
        for stmt in statements:
            if isinstance(stmt, VarDecl):
                value = self._emit_expr(stmt.initializer) if stmt.initializer else None
                self.instructions.append(TACInstruction("declare", stmt.name, value))
            elif isinstance(stmt, Assignment):
                value = self._emit_expr(stmt.value)
                target = self._emit_expr(stmt.target)
                self.instructions.append(TACInstruction("assign", target, value))
            elif isinstance(stmt, ExpressionStmt):
                self._emit_expr(stmt.expr)
            elif isinstance(stmt, PrintStmt):
                for arg in stmt.args:
                    self.instructions.append(TACInstruction("print", arg1=self._emit_expr(arg)))
            elif isinstance(stmt, ReturnStmt):
                self.instructions.append(TACInstruction("return", arg1=self._emit_expr(stmt.value)))
            elif isinstance(stmt, IfStmt):
                condition = self._emit_expr(stmt.condition)
                then_label = self._label("then")
                end_label = self._label("endif")
                else_label = self._label("else") if stmt.else_branch else end_label
                self.instructions.append(TACInstruction("branch", arg1=condition, arg2=then_label, result=else_label))
                self.instructions.append(TACInstruction("label", result=then_label))
                self._lower_statements(stmt.then_branch)
                self.instructions.append(TACInstruction("goto", result=end_label))
                if stmt.else_branch:
                    self.instructions.append(TACInstruction("label", result=else_label))
                    self._lower_statements(stmt.else_branch)
                self.instructions.append(TACInstruction("label", result=end_label))
            elif isinstance(stmt, WhileStmt):
                header = self._label("while")
                body = self._label("while_body")
                after = self._label("while_end")
                self.instructions.append(TACInstruction("label", result=header))
                condition = self._emit_expr(stmt.condition)
                self.instructions.append(TACInstruction("branch", arg1=condition, arg2=body, result=after))
                self.instructions.append(TACInstruction("label", result=body))
                self._lower_statements(stmt.body)
                self.instructions.append(TACInstruction("goto", result=header))
                self.instructions.append(TACInstruction("label", result=after))
            elif isinstance(stmt, ForRangeStmt):
                start = self._emit_expr(stmt.start)
                end = self._emit_expr(stmt.end)
                step = self._emit_expr(stmt.step) if stmt.step else "1"
                self.instructions.append(TACInstruction("declare", stmt.var_name, start))
                header = self._label("for")
                body = self._label("for_body")
                after = self._label("for_end")
                self.instructions.append(TACInstruction("label", result=header))
                self.instructions.append(TACInstruction("branch", arg1=f"{stmt.var_name} < {end}", arg2=body, result=after))
                self.instructions.append(TACInstruction("label", result=body))
                self._lower_statements(stmt.body)
                self.instructions.append(TACInstruction("binary", stmt.var_name, stmt.var_name, f"+ {step}"))
                self.instructions.append(TACInstruction("goto", result=header))
                self.instructions.append(TACInstruction("label", result=after))


def lower_to_tac(function: FunctionDef) -> List[TACInstruction]:
    return TACLowerer().lower_function(function)

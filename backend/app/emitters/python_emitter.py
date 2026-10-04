from typing import List, Optional
from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class PythonEmitter:
    """Emits clean, idiomatic Python 3 code from Universal IR."""

    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str

    def emit(self, program: Program) -> str:
        lines: List[str] = []

        # Emit functions
        for fn in program.functions:
            lines.extend(self._emit_function(fn))
            lines.append("")

        # Emit global statements
        for stmt in program.global_statements:
            lines.extend(self._emit_statement(stmt, indent_level=0))

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        params_str = ", ".join(p.name for p in fn.params)
        lines = [f"def {fn.name}({params_str}):"]
        if not fn.body:
            lines.append(f"{self._indent(1)}pass")
            return lines

        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=1))
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            if stmt.initializer:
                val = self._emit_expr(stmt.initializer)
                return [f"{ind}{stmt.name} = {val}"]
            return [f"{ind}{stmt.name} = None"]

        elif isinstance(stmt, Assignment):
            target = self._emit_expr(stmt.target)
            val = self._emit_expr(stmt.value)
            return [f"{ind}{target} = {val}"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}if {cond}:"]
            if stmt.then_branch:
                for s in stmt.then_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            else:
                lines.append(f"{self._indent(indent_level + 1)}pass")

            if stmt.else_branch:
                lines.append(f"{ind}else:")
                for s in stmt.else_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            return lines

        elif isinstance(stmt, WhileStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}while {cond}:"]
            if stmt.body:
                for s in stmt.body:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            else:
                lines.append(f"{self._indent(indent_level + 1)}pass")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            start = self._emit_expr(stmt.start) if stmt.start else "0"
            end = self._emit_expr(stmt.end) if stmt.end else "0"
            if stmt.step:
                step = self._emit_expr(stmt.step)
                range_call = f"range({start}, {end}, {step})"
            elif start == "0":
                range_call = f"range({end})"
            else:
                range_call = f"range({start}, {end})"

            lines = [f"{ind}for {stmt.var_name} in {range_call}:"]
            if stmt.body:
                for s in stmt.body:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            else:
                lines.append(f"{self._indent(indent_level + 1)}pass")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)}"]
            return [f"{ind}return"]

        elif isinstance(stmt, PrintStmt):
            args_str = ", ".join(self._emit_expr(a) for a in stmt.args)
            return [f"{ind}print({args_str})"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)}"]

        return []

    def _emit_expr(self, expr: Optional[Expression]) -> str:
        if not expr:
            return ""

        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "True" if expr.value else "False"
            return repr(expr.value)

        elif isinstance(expr, Identifier):
            return expr.name

        elif isinstance(expr, BinaryOp):
            left_str = self._emit_expr(expr.left)
            right_str = self._emit_expr(expr.right)
            op = expr.op
            if op == "&&":
                op = "and"
            elif op == "||":
                op = "or"
            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand)
            op = "not " if expr.op in ["!", "not"] else expr.op
            return f"{op}{operand_str}"

        elif isinstance(expr, ArrayLiteral):
            elems = ", ".join(self._emit_expr(e) for e in expr.elements)
            return f"[{elems}]"

        elif isinstance(expr, ArrayAccess):
            arr_str = self._emit_expr(expr.array)
            idx_str = self._emit_expr(expr.index)
            return f"{arr_str}[{idx_str}]"

        elif isinstance(expr, ArrayLength):
            arr_str = self._emit_expr(expr.array)
            return f"len({arr_str})"

        elif isinstance(expr, FunctionCall):
            args_str = ", ".join(self._emit_expr(a) for a in expr.args)
            return f"{expr.name}({args_str})"

        return ""

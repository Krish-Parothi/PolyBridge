from typing import List, Optional, Set
from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class JavaScriptEmitter:
    """Emits modern ES6 JavaScript code from Universal IR."""

    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()

    def emit(self, program: Program) -> str:
        lines: List[str] = []
        self.declared_vars.clear()

        # Emit functions
        for fn in program.functions:
            lines.extend(self._emit_function(fn))
            lines.append("")

        # Emit global statements
        for stmt in program.global_statements:
            lines.extend(self._emit_statement(stmt, indent_level=0, is_global=True))

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        saved_vars = set(self.declared_vars)
        # Register parameters as declared
        for p in fn.params:
            self.declared_vars.add(p.name)

        params_str = ", ".join(p.name for p in fn.params)
        lines = [f"function {fn.name}({params_str}) {{"]
        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=1, is_global=False))
        lines.append("}")

        self.declared_vars = saved_vars
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int, is_global: bool = False) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            self.declared_vars.add(stmt.name)
            if stmt.initializer:
                val = self._emit_expr(stmt.initializer)
                return [f"{ind}let {stmt.name} = {val};"]
            return [f"{ind}let {stmt.name};"]

        elif isinstance(stmt, Assignment):
            target = self._emit_expr(stmt.target)
            val = self._emit_expr(stmt.value)
            # If target is an undeclared identifier, declare it with let
            if isinstance(stmt.target, Identifier) and stmt.target.name not in self.declared_vars:
                self.declared_vars.add(stmt.target.name)
                return [f"{ind}let {target} = {val};"]
            return [f"{ind}{target} = {val};"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}if ({cond}) {{"]
            for s in stmt.then_branch:
                lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            if stmt.else_branch:
                lines.append(f"{ind}}} else {{")
                for s in stmt.else_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, WhileStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}while ({cond}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            start = self._emit_expr(stmt.start) if stmt.start else "0"
            end = self._emit_expr(stmt.end) if stmt.end else "0"
            step_str = f"{stmt.var_name} += {self._emit_expr(stmt.step)}" if stmt.step else f"{stmt.var_name}++"

            lines = [f"{ind}for (let {stmt.var_name} = {start}; {stmt.var_name} < {end}; {step_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)};"]
            return [f"{ind}return;"]

        elif isinstance(stmt, PrintStmt):
            args_str = ", ".join(self._emit_expr(a) for a in stmt.args)
            return [f"{ind}console.log({args_str});"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)};"]

        return []

    def _emit_expr(self, expr: Optional[Expression]) -> str:
        if not expr:
            return ""

        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            elif isinstance(expr.value, str):
                return f'"{expr.value}"'
            return str(expr.value)

        elif isinstance(expr, Identifier):
            return expr.name

        elif isinstance(expr, BinaryOp):
            left_str = self._emit_expr(expr.left)
            right_str = self._emit_expr(expr.right)
            op = expr.op
            if op == "and":
                op = "&&"
            elif op == "or":
                op = "||"
            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand)
            op = "!" if expr.op in ["!", "not"] else expr.op
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
            return f"{arr_str}.length"

        elif isinstance(expr, FunctionCall):
            args_str = ", ".join(self._emit_expr(a) for a in expr.args)
            return f"{expr.name}({args_str})"

        return ""

from typing import List, Optional, Set
from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class GoEmitter:
    """Emits Go 1.21 code with package main and func main boilerplate."""

    def __init__(self, indent_str: str = "\t"):
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        lines: List[str] = ["package main", "", 'import "fmt"', ""]

        # Emit functions
        for fn in program.functions:
            lines.extend(self._emit_function(fn))
            lines.append("")

        # Emit main function
        lines.append("func main() {")
        for stmt in program.global_statements:
            lines.extend(self._emit_statement(stmt, indent_level=1))
        lines.append("}")

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _to_go_type(self, t: IRType) -> str:
        if t.kind == TypeKind.INT:
            return "int"
        elif t.kind == TypeKind.FLOAT:
            return "float64"
        elif t.kind == TypeKind.STRING:
            return "string"
        elif t.kind == TypeKind.BOOL:
            return "bool"
        elif t.kind == TypeKind.VOID:
            return ""
        elif t.kind == TypeKind.ARRAY:
            elem = self._to_go_type(t.element_type) if t.element_type else "int"
            return f"[]{elem}"
        return "int"

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        saved_vars = set(self.declared_vars)

        params_strs: List[str] = []
        for p in fn.params:
            ptype = self._to_go_type(p.param_type)
            self.declared_vars.add(p.name)
            params_strs.append(f"{p.name} {ptype}")

        ret_type_str = self._to_go_type(fn.return_type)
        params_joined = ", ".join(params_strs)
        ret_suffix = f" {ret_type_str}" if ret_type_str else ""

        lines = [f"func {fn.name}({params_joined}){ret_suffix} {{"]
        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=1))
        lines.append("}")

        self.declared_vars = saved_vars
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            self.declared_vars.add(stmt.name)
            if stmt.initializer:
                val = self._emit_expr(stmt.initializer)
                return [f"{ind}{stmt.name} := {val}"]
            gtype = self._to_go_type(stmt.var_type)
            return [f"{ind}var {stmt.name} {gtype}"]

        elif isinstance(stmt, Assignment):
            target = self._emit_expr(stmt.target)
            val = self._emit_expr(stmt.value)
            if isinstance(stmt.target, Identifier) and stmt.target.name not in self.declared_vars:
                self.declared_vars.add(stmt.target.name)
                return [f"{ind}{target} := {val}"]
            return [f"{ind}{target} = {val}"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}if {cond} {{"]
            for s in stmt.then_branch:
                lines.extend(self._emit_statement(s, indent_level + 1))
            if stmt.else_branch:
                lines.append(f"{ind}}} else {{")
                for s in stmt.else_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, WhileStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}for {cond} {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            start = self._emit_expr(stmt.start) if stmt.start else "0"
            end = self._emit_expr(stmt.end) if stmt.end else "0"
            step_str = f"{stmt.var_name} += {self._emit_expr(stmt.step)}" if stmt.step else f"{stmt.var_name}++"

            lines = [f"{ind}for {stmt.var_name} := {start}; {stmt.var_name} < {end}; {step_str} {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)}"]
            return [f"{ind}return"]

        elif isinstance(stmt, PrintStmt):
            args_str = ", ".join(self._emit_expr(a) for a in stmt.args)
            return [f"{ind}fmt.Println({args_str})"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)}"]

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
            # Default slice type in Go
            return f"[]int{{{elems}}}"

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

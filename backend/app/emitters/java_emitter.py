from typing import List, Optional, Set
from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class JavaEmitter:
    """Emits Java 17 code with class Solution and public static void main boilerplate."""

    def __init__(self, class_name: str = "Solution", indent_str: str = "    "):
        self.class_name = class_name
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()
        self.var_types: dict[str, str] = {}
        self.uses_arrays = False

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        self.var_types.clear()
        self.uses_arrays = False

        # Pre-scan for arrays
        self._detect_array_usage(program)

        class_lines: List[str] = []
        if self.uses_arrays:
            class_lines.append("import java.util.Arrays;")
            class_lines.append("")

        class_lines.append(f"public class {self.class_name} {{")

        # Emit static methods
        for fn in program.functions:
            class_lines.extend(self._emit_function(fn))
            class_lines.append("")

        # Emit main method
        class_lines.append(f"{self._indent(1)}public static void main(String[] args) {{")
        for stmt in program.global_statements:
            class_lines.extend(self._emit_statement(stmt, indent_level=2))
        class_lines.append(f"{self._indent(1)}}}")

        class_lines.append("}")
        return "\n".join(class_lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _to_java_type(self, t: IRType) -> str:
        if t.kind == TypeKind.INT:
            return "int"
        elif t.kind == TypeKind.FLOAT:
            return "double"
        elif t.kind == TypeKind.STRING:
            return "String"
        elif t.kind == TypeKind.BOOL:
            return "boolean"
        elif t.kind == TypeKind.VOID:
            return "void"
        elif t.kind == TypeKind.ARRAY:
            elem = self._to_java_type(t.element_type) if t.element_type else "int"
            return f"{elem}[]"
        return "int"  # safe default

    def _detect_array_usage(self, program: Program):
        for fn in program.functions:
            if fn.return_type.kind == TypeKind.ARRAY:
                self.uses_arrays = True
            for p in fn.params:
                if p.param_type.kind == TypeKind.ARRAY:
                    self.uses_arrays = True
            for stmt in fn.body:
                if self._stmt_uses_array(stmt):
                    self.uses_arrays = True
        for stmt in program.global_statements:
            if self._stmt_uses_array(stmt):
                self.uses_arrays = True

    def _stmt_uses_array(self, stmt: Statement) -> bool:
        if isinstance(stmt, VarDecl) and stmt.var_type.kind == TypeKind.ARRAY:
            return True
        if isinstance(stmt, (Assignment, ReturnStmt, PrintStmt)):
            return True
        return False

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        saved_vars = set(self.declared_vars)
        saved_types = dict(self.var_types)

        params_strs: List[str] = []
        for p in fn.params:
            ptype = self._to_java_type(p.param_type)
            self.declared_vars.add(p.name)
            self.var_types[p.name] = ptype
            params_strs.append(f"{ptype} {p.name}")

        ret_type_str = self._to_java_type(fn.return_type)
        params_joined = ", ".join(params_strs)

        lines = [f"{self._indent(1)}public static {ret_type_str} {fn.name}({params_joined}) {{"]
        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=2))
        lines.append(f"{self._indent(1)}}}")

        self.declared_vars = saved_vars
        self.var_types = saved_types
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            self.declared_vars.add(stmt.name)
            jtype = self._to_java_type(stmt.var_type)
            self.var_types[stmt.name] = jtype
            if stmt.initializer:
                val = self._emit_expr(stmt.initializer, expected_type=jtype)
                return [f"{ind}{jtype} {stmt.name} = {val};"]
            return [f"{ind}{jtype} {stmt.name};"]

        elif isinstance(stmt, Assignment):
            target = self._emit_expr(stmt.target)
            if isinstance(stmt.target, Identifier) and stmt.target.name not in self.declared_vars:
                # First time assignment -> declare variable
                jtype = self._to_java_type(stmt.target.inferred_type)
                self.declared_vars.add(stmt.target.name)
                self.var_types[stmt.target.name] = jtype
                val = self._emit_expr(stmt.value, expected_type=jtype)
                return [f"{ind}{jtype} {target} = {val};"]

            expected = self.var_types.get(target, "int")
            val = self._emit_expr(stmt.value, expected_type=expected)
            return [f"{ind}{target} = {val};"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_expr(stmt.condition)
            lines = [f"{ind}if ({cond}) {{"]
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
            lines = [f"{ind}while ({cond}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            start = self._emit_expr(stmt.start) if stmt.start else "0"
            end = self._emit_expr(stmt.end) if stmt.end else "0"
            step_str = f"{stmt.var_name} += {self._emit_expr(stmt.step)}" if stmt.step else f"{stmt.var_name}++"

            lines = [f"{ind}for (int {stmt.var_name} = {start}; {stmt.var_name} < {end}; {step_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)};"]
            return [f"{ind}return;"]

        elif isinstance(stmt, PrintStmt):
            if len(stmt.args) == 1:
                arg = stmt.args[0]
                is_arr = arg.inferred_type.kind == TypeKind.ARRAY
                if isinstance(arg, Identifier) and self.var_types.get(arg.name, "").endswith("[]"):
                    is_arr = True
                if is_arr:
                    self.uses_arrays = True
                    return [f"{ind}System.out.println(Arrays.toString({self._emit_expr(arg)}));"]
                return [f"{ind}System.out.println({self._emit_expr(arg)});"]
            else:
                args_str = " + \" \" + ".join(self._emit_expr(a) for a in stmt.args)
                return [f"{ind}System.out.println({args_str});"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)};"]

        return []

    def _emit_expr(self, expr: Optional[Expression], expected_type: str = "") -> str:
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
            # In Java, e.g. new int[]{1, 2, 3}
            base = "int"
            if expected_type.endswith("[]"):
                base = expected_type[:-2]
            return f"new {base}[]{{{elems}}}"

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

from typing import List, Optional, Set, Dict, Any
from app.ir.nodes import (
    Program, FunctionDef, Parameter, Statement, Expression,
    VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
    ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
    BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
    FunctionCall, IRType, TypeKind
)
from app.libraries.registry import LibraryRegistry

class CppEmitter:
    """Emits modern C++20 code from Universal IR."""

    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()
        self.var_types: Dict[str, str] = {}
        self.used_includes: Set[str] = {"#include <iostream>"}
        self.module_aliases: Dict[str, str] = {}
        self.uses_vectors = False
        self.needs_floor_div = False

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        self.var_types.clear()
        self.used_includes = {"#include <iostream>"}
        self.module_aliases.clear()
        self.uses_vectors = False
        self.needs_floor_div = False

        # Scan for imported modules
        for imp in getattr(program, "imports", []):
            if imp.alias:
                self.module_aliases[imp.alias] = imp.module
            for ti in LibraryRegistry.get_target_imports({imp.module}, "cpp"):
                self.used_includes.add(ti)

        # Pre-scan for vector usage
        self._detect_array_usage(program)
        if self.uses_vectors:
            self.used_includes.add("#include <vector>")

        body_lines: List[str] = []

        # Emit functions
        for fn in program.functions:
            body_lines.extend(self._emit_function(fn))
            body_lines.append("")

        # Emit main function
        main_lines: List[str] = ["int main() {"]
        for stmt in program.global_statements:
            main_lines.extend(self._emit_statement(stmt, indent_level=1))
        main_lines.append(f"{self._indent(1)}return 0;")
        main_lines.append("}")

        if self.needs_floor_div:
            floor_helper = [
                "int floorDiv(int a, int b) {",
                f"{self.indent_str}int d = a / b;",
                f"{self.indent_str}int r = a % b;",
                f"{self.indent_str}if ((r != 0) && ((r < 0) ^ (b < 0))) {{",
                f"{self.indent_str}{self.indent_str}d--;",
                f"{self.indent_str}}}",
                f"{self.indent_str}return d;",
                "}",
                ""
            ]
            body_lines = floor_helper + body_lines

        lines: List[str] = []
        for inc in sorted(self.used_includes):
            lines.append(inc)
        lines.append("")

        lines.extend(body_lines)
        lines.extend(main_lines)

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _to_cpp_type(self, t: IRType) -> str:
        if t.kind == TypeKind.INT:
            return "int"
        elif t.kind == TypeKind.FLOAT:
            return "double"
        elif t.kind == TypeKind.STRING:
            self.used_includes.add("#include <string>")
            return "std::string"
        elif t.kind == TypeKind.BOOL:
            return "bool"
        elif t.kind == TypeKind.VOID:
            return "void"
        elif t.kind == TypeKind.ARRAY:
            self.used_includes.add("#include <vector>")
            elem = self._to_cpp_type(t.element_type) if t.element_type else "int"
            return f"std::vector<{elem}>"
        return "int"

    def _detect_array_usage(self, node: Any):
        if isinstance(node, Program):
            for fn in node.functions:
                self._detect_array_usage(fn)
            for stmt in node.global_statements:
                self._detect_array_usage(stmt)
        elif isinstance(node, FunctionDef):
            for p in node.params:
                if p.param_type.kind == TypeKind.ARRAY:
                    self.uses_vectors = True
            for s in node.body:
                self._detect_array_usage(s)
        elif isinstance(node, (VarDecl, Assignment)):
            if hasattr(node, "var_type") and node.var_type.kind == TypeKind.ARRAY:
                self.uses_vectors = True
            if hasattr(node, "initializer") and node.initializer:
                self._detect_array_usage(node.initializer)
            if hasattr(node, "value") and node.value:
                self._detect_array_usage(node.value)
        elif isinstance(node, ArrayLiteral):
            self.uses_vectors = True

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        ret_type = self._to_cpp_type(fn.return_type)
        params_str = ", ".join(f"{self._to_cpp_type(p.param_type)} {p.name}" for p in fn.params)
        lines = [f"{ret_type} {fn.name}({params_str}) {{"]
        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=1))
        lines.append("}")
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            t_str = self._to_cpp_type(stmt.var_type)
            self.declared_vars.add(stmt.name)
            self.var_types[stmt.name] = t_str
            if stmt.initializer:
                init_str = self._emit_expr(stmt.initializer, expected_type=t_str)
                return [f"{ind}{t_str} {stmt.name} = {init_str};"]
            return [f"{ind}{t_str} {stmt.name};"]

        elif isinstance(stmt, Assignment):
            target_str = self._emit_expr(stmt.target)
            if isinstance(stmt.target, Identifier) and stmt.target.name not in self.declared_vars:
                # Variable was never declared, declare it as auto or inferred type
                self.declared_vars.add(stmt.target.name)
                t_str = self._to_cpp_type(stmt.value.inferred_type) if stmt.value else "auto"
                val_str = self._emit_expr(stmt.value, expected_type=t_str)
                return [f"{ind}{t_str} {target_str} = {val_str};"]
            val_str = self._emit_expr(stmt.value)
            return [f"{ind}{target_str} = {val_str};"]

        elif isinstance(stmt, IfStmt):
            cond_str = self._emit_expr(stmt.condition)
            lines = [f"{ind}if ({cond_str}) {{"]
            for s in stmt.then_body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            if stmt.else_body:
                lines.append(f"{ind}}} else {{")
                for s in stmt.else_body:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, WhileStmt):
            cond_str = self._emit_expr(stmt.condition)
            lines = [f"{ind}while ({cond_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            var_name = stmt.var_name
            start_str = self._emit_expr(stmt.start) if stmt.start else "0"
            end_str = self._emit_expr(stmt.end)
            step_str = self._emit_expr(stmt.step) if stmt.step else "1"

            if step_str == "1":
                header = f"for (int {var_name} = {start_str}; {var_name} < {end_str}; {var_name}++)"
            else:
                header = f"for (int {var_name} = {start_str}; {var_name} < {end_str}; {var_name} += {step_str})"

            lines = [f"{ind}{header} {{"]
            self.declared_vars.add(var_name)
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)};"]
            return [f"{ind}return;"]

        elif isinstance(stmt, PrintStmt):
            args_str = " << \" \" << ".join(self._emit_expr(a) for a in stmt.args)
            if not args_str:
                return [f"{ind}std::cout << std::endl;"]
            return [f"{ind}std::cout << {args_str} << std::endl;"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)};"]

        return []

    def _emit_expr(self, expr: Expression, expected_type: str = "") -> str:
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
            elif op == "//":
                self.needs_floor_div = True
                return f"floorDiv({left_str}, {right_str})"
            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand)
            op = "!" if expr.op in ["!", "not"] else expr.op
            return f"{op}{operand_str}"

        elif isinstance(expr, ArrayLiteral):
            elems = ", ".join(self._emit_expr(e) for e in expr.elements)
            self.used_includes.add("#include <vector>")
            return f"std::vector<int>{{{elems}}}"

        elif isinstance(expr, ArrayAccess):
            arr_str = self._emit_expr(expr.array)
            idx_str = self._emit_expr(expr.index)
            return f"{arr_str}[{idx_str}]"

        elif isinstance(expr, ArrayLength):
            arr_str = self._emit_expr(expr.array)
            return f"(int){arr_str}.size()"

        elif isinstance(expr, FunctionCall):
            args_strs = [self._emit_expr(a) for a in expr.args]
            translated, req_include = LibraryRegistry.resolve_call(expr.name, args_strs, "cpp", self.module_aliases)
            if req_include:
                self.used_includes.add(req_include)
            if translated:
                return translated
            args_str = ", ".join(args_strs)
            return f"{expr.name}({args_str})"

        return ""

from typing import List, Optional, Set, Dict
from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind,
        ForEachStmt, AugmentedAssignment, DoWhileStmt, TernaryOp, CastExpr, MethodCall
    )
from app.libraries.registry import LibraryRegistry

class JavaScriptEmitter:
    """Emits modern ES6 JavaScript code from Universal IR."""

    def __init__(self, indent_str: str = "    "):
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()
        self.used_imports: Set[str] = set()
        self.module_aliases: Dict[str, str] = {}

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        self.used_imports.clear()
        self.module_aliases.clear()

        # Collect imported aliases and map module imports
        for imp in getattr(program, "imports", []):
            if imp.alias:
                self.module_aliases[imp.alias] = imp.module
            for ti in LibraryRegistry.get_target_imports({imp.module}, "javascript"):
                self.used_imports.add(ti)

        body_lines: List[str] = []

        # Emit functions
        for fn in program.functions:
            body_lines.extend(self._emit_function(fn))
            body_lines.append("")

        # Emit global statements
        for stmt in program.global_statements:
            body_lines.extend(self._emit_statement(stmt, indent_level=0, is_global=True))

        lines: List[str] = []
        for imp in sorted(self.used_imports):
            lines.append(imp)
        if self.used_imports and body_lines:
            lines.append("")

        lines.extend(body_lines)
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

        elif isinstance(stmt, AugmentedAssignment):
            target = self._emit_expr(stmt.target)
            val = self._emit_expr(stmt.value)
            op = stmt.op
            if op == "//=":
                return [f"{ind}{target} = Math.floor({target} / {val});"]
            return [f"{ind}{target} {op} {val};"]

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

        elif isinstance(stmt, DoWhileStmt):
            cond = self._emit_expr(stmt.condition) if stmt.condition else "true"
            lines = [f"{ind}do {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            lines.append(f"{ind}}} while ({cond});")
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

        elif isinstance(stmt, ForEachStmt):
            iter_str = self._emit_expr(stmt.iterable)
            lines = [f"{ind}for (let {stmt.var_name} of {iter_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1, is_global))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)};"]
            return [f"{ind}return;"]

        elif isinstance(stmt, BreakStmt):
            return [f"{ind}break;"]

        elif isinstance(stmt, ContinueStmt):
            return [f"{ind}continue;"]

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
            if expr.value is None:
                return "null"
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
            elif op == "//" or (op == "/" and expr.inferred_type.kind == TypeKind.INT):
                return f"Math.floor(({left_str}) / ({right_str}))"
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
            # Handle negative indexing like arr[-1]
            if isinstance(expr.index, Literal) and isinstance(expr.index.value, int) and expr.index.value < 0:
                offset = abs(expr.index.value)
                return f"{arr_str}[({arr_str}.length - {offset})]"
            elif isinstance(expr.index, UnaryOp) and expr.index.op == "-":
                operand_str = self._emit_expr(expr.index.operand)
                return f"{arr_str}[({arr_str}.length - {operand_str})]"
            idx_str = self._emit_expr(expr.index)
            return f"{arr_str}[{idx_str}]"

        elif isinstance(expr, ArrayLength):
            arr_str = self._emit_expr(expr.array)
            return f"{arr_str}.length"

        elif isinstance(expr, TernaryOp):
            cond = self._emit_expr(expr.condition)
            then_str = self._emit_expr(expr.then_expr)
            else_str = self._emit_expr(expr.else_expr)
            return f"({cond} ? {then_str} : {else_str})"

        elif isinstance(expr, CastExpr):
            op_str = self._emit_expr(expr.operand)
            if expr.target_type.kind == TypeKind.INT:
                return f"Math.floor(Number({op_str}))"
            elif expr.target_type.kind == TypeKind.FLOAT:
                return f"Number({op_str})"
            elif expr.target_type.kind == TypeKind.STRING:
                return f"String({op_str})"
            elif expr.target_type.kind == TypeKind.BOOL:
                return f"Boolean({op_str})"
            return op_str

        elif isinstance(expr, MethodCall):
            obj_str = self._emit_expr(expr.object_expr)
            m = expr.method_name
            args_strs = [self._emit_expr(a) for a in expr.args]
            if m in ["append", "push"] and len(args_strs) == 1:
                return f"{obj_str}.push({args_strs[0]})"
            elif m in ["lower"]:
                return f"{obj_str}.toLowerCase()"
            elif m in ["upper"]:
                return f"{obj_str}.toUpperCase()"
            elif m in ["strip"]:
                return f"{obj_str}.trim()"
            elif m in ["find"]:
                return f"{obj_str}.indexOf({args_strs[0]})"
            joined_args = ", ".join(args_strs)
            return f"{obj_str}.{m}({joined_args})"

        elif isinstance(expr, FunctionCall):
            args_strs = [self._emit_expr(a) for a in expr.args]
            translated, req_import = LibraryRegistry.resolve_call(expr.name, args_strs, "javascript", self.module_aliases)
            if req_import:
                self.used_imports.add(req_import)
            if translated:
                return translated
            if expr.name.endswith(".append") and len(args_strs) == 1:
                obj = expr.name[:-7]
                return f"{obj}.push({args_strs[0]})"
            if expr.name == "append" and len(args_strs) == 2:
                return f"{args_strs[0]}.push({args_strs[1]})"
            args_str = ", ".join(args_strs)
            return f"{expr.name}({args_str})"

        return ""

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

class JavaEmitter:
    """Emits Java 17 code with class Solution and public static void main boilerplate."""

    def __init__(self, class_name: str = "Solution", indent_str: str = "    "):
        self.class_name = class_name
        self.indent_str = indent_str
        self.declared_vars: Set[str] = set()
        self.var_types: dict[str, str] = {}
        self.uses_arrays = False
        self.used_imports: Set[str] = set()
        self.module_aliases: Dict[str, str] = {}

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        self.var_types.clear()
        self.uses_arrays = False
        self.used_imports.clear()
        self.module_aliases.clear()

        # Collect imported aliases and map module imports
        for imp in getattr(program, "imports", []):
            if imp.alias:
                self.module_aliases[imp.alias] = imp.module
            for ti in LibraryRegistry.get_target_imports({imp.module}, "java"):
                self.used_imports.add(ti)

        # Pre-scan for arrays
        self._detect_array_usage(program)
        if self.uses_arrays:
            self.used_imports.add("import java.util.Arrays;")

        # Pre-emit methods to capture required imports from calls
        body_lines: List[str] = []
        for fn in program.functions:
            body_lines.extend(self._emit_function(fn))
            body_lines.append("")

        main_lines: List[str] = [f"{self._indent(1)}public static void main(String[] args) {{"]
        for stmt in program.global_statements:
            main_lines.extend(self._emit_statement(stmt, indent_level=2))
        main_lines.append(f"{self._indent(1)}}}")

        class_lines: List[str] = []
        for imp_stmt in sorted(self.used_imports):
            class_lines.append(imp_stmt)
        if self.used_imports:
            class_lines.append("")

        class_lines.append(f"public class {self.class_name} {{")
        class_lines.extend(body_lines)
        class_lines.extend(main_lines)
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
                val = self._emit_expr(stmt.value)
                if stmt.target.inferred_type.kind == TypeKind.UNKNOWN:
                    # In Java 17, use 'var' for local variables when exact type is complex/unknown
                    jtype = "var"
                else:
                    jtype = self._to_java_type(stmt.target.inferred_type)
                self.declared_vars.add(stmt.target.name)
                self.var_types[stmt.target.name] = jtype
                return [f"{ind}{jtype} {target} = {val};"]

            expected = self.var_types.get(target, "int")
            val = self._emit_expr(stmt.value, expected_type=expected)
            return [f"{ind}{target} = {val};"]

        elif isinstance(stmt, AugmentedAssignment):
            target = self._emit_expr(stmt.target)
            val = self._emit_expr(stmt.value)
            op = stmt.op
            if op == "**=":
                return [f"{ind}{target} = (long) Math.pow({target}, {val});"]
            elif op == "//=":
                op = "/="
            return [f"{ind}{target} {op} {val};"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_condition(stmt.condition)
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
            cond = self._emit_condition(stmt.condition)
            lines = [f"{ind}while ({cond}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, DoWhileStmt):
            cond = self._emit_condition(stmt.condition) if stmt.condition else "true"
            lines = [f"{ind}do {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}} while ({cond});")
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

        elif isinstance(stmt, ForEachStmt):
            iter_str = self._emit_expr(stmt.iterable)
            elem_t = "int"
            if stmt.iterable and stmt.iterable.inferred_type.kind == TypeKind.ARRAY and stmt.iterable.inferred_type.element_type:
                elem_t = self._to_java_type(stmt.iterable.inferred_type.element_type)
            elif stmt.iterable and stmt.iterable.inferred_type.kind == TypeKind.STRING:
                elem_t = "char"
                iter_str = f"{iter_str}.toCharArray()"
            self.declared_vars.add(stmt.var_name)
            self.var_types[stmt.var_name] = elem_t
            lines = [f"{ind}for ({elem_t} {stmt.var_name} : {iter_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
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
            if isinstance(stmt.expr, FunctionCall):
                if (stmt.expr.name.endswith(".append") or stmt.expr.name.endswith(".push")) and stmt.expr.args:
                    obj = stmt.expr.name.split(".")[0]
                    arg = self._emit_expr(stmt.expr.args[0])
                    self.uses_arrays = True
                    self.used_imports.add("import java.util.Arrays;")
                    return [
                        f"{ind}{obj} = Arrays.copyOf({obj}, {obj}.length + 1);",
                        f"{ind}{obj}[{obj}.length - 1] = {arg};"
                    ]
                elif stmt.expr.name == "append" and len(stmt.expr.args) == 2:
                    obj = self._emit_expr(stmt.expr.args[0])
                    arg = self._emit_expr(stmt.expr.args[1])
                    self.uses_arrays = True
                    self.used_imports.add("import java.util.Arrays;")
                    return [
                        f"{ind}{obj} = Arrays.copyOf({obj}, {obj}.length + 1);",
                        f"{ind}{obj}[{obj}.length - 1] = {arg};"
                    ]
            elif isinstance(stmt.expr, MethodCall):
                if stmt.expr.method_name in ["append", "push"] and stmt.expr.args:
                    obj = self._emit_expr(stmt.expr.object_expr)
                    arg = self._emit_expr(stmt.expr.args[0])
                    self.uses_arrays = True
                    self.used_imports.add("import java.util.Arrays;")
                    return [
                        f"{ind}{obj} = Arrays.copyOf({obj}, {obj}.length + 1);",
                        f"{ind}{obj}[{obj}.length - 1] = {arg};"
                    ]
                args_str = ", ".join(self._emit_expr(a) for a in stmt.expr.args)
                return [f"{ind}{self._emit_expr(stmt.expr.object_expr)}.{stmt.expr.method_name}({args_str});"]
            return [f"{ind}{self._emit_expr(stmt.expr)};"]

        return []

    def _emit_condition(self, expr: Optional[Expression]) -> str:
        if not expr:
            return "true"
        cond_str = self._emit_expr(expr)
        if isinstance(expr, BinaryOp) and expr.op in ["==", "!=", "===", "!==", "<", "<=", ">", ">=", "&&", "||", "and", "or"]:
            return cond_str
        if isinstance(expr, UnaryOp) and expr.op in ["!", "not"]:
            return cond_str
        if isinstance(expr, Literal) and isinstance(expr.value, bool):
            return cond_str
        if expr.inferred_type.kind == TypeKind.BOOL:
            return cond_str
        if expr.inferred_type.kind == TypeKind.INT:
            return f"({cond_str} != 0)"
        elif expr.inferred_type.kind == TypeKind.STRING:
            return f"(!{cond_str}.isEmpty())"
        elif expr.inferred_type.kind == TypeKind.ARRAY:
            return f"({cond_str}.length > 0)"
        elif isinstance(expr, Identifier):
            if self.var_types.get(expr.name) == "boolean":
                return cond_str
            return f"({cond_str} != 0)"
        return cond_str

    def _emit_expr(self, expr: Optional[Expression], expected_type: str = "") -> str:
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

            is_str = (expr.left.inferred_type.kind == TypeKind.STRING or 
                      expr.right.inferred_type.kind == TypeKind.STRING or
                      self.var_types.get(left_str) == "String" or
                      self.var_types.get(right_str) == "String")
            if is_str:
                if op in ["==", "==="]:
                    return f"{left_str}.equals({right_str})"
                elif op in ["!=", "!=="]:
                    return f"(!{left_str}.equals({right_str}))"

            if op == "and":
                op = "&&"
            elif op == "or":
                op = "||"
            elif op == "//":
                return f"Math.floorDiv({left_str}, {right_str})"
            elif op == "**":
                return f"(long) Math.pow({left_str}, {right_str})"
            elif op == "===":
                op = "=="
            elif op == "!==":
                op = "!="
            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand)
            op = "!" if expr.op in ["!", "not"] else expr.op
            return f"{op}{operand_str}"

        elif isinstance(expr, ArrayLiteral):
            elems = ", ".join(self._emit_expr(e) for e in expr.elements)
            jtype = self._to_java_type(expr.inferred_type) if expr.inferred_type and expr.inferred_type.kind != TypeKind.UNKNOWN else ""
            if jtype and jtype.endswith("[]"):
                return f"new {jtype}{{{elems}}}"
            if expected_type.endswith("[]"):
                return f"new {expected_type}{{{elems}}}"
            if expr.elements and isinstance(expr.elements[0], ArrayLiteral):
                return f"new int[][]{{{elems}}}"
            return f"new int[]{{{elems}}}"

        elif isinstance(expr, ArrayAccess):
            arr_str = self._emit_expr(expr.array)
            is_str = expr.array.inferred_type.kind == TypeKind.STRING or self.var_types.get(arr_str) == "String"
            
            is_neg = False
            offset = ""
            if isinstance(expr.index, Literal) and isinstance(expr.index.value, int) and expr.index.value < 0:
                is_neg = True
                offset = str(-expr.index.value)
            elif isinstance(expr.index, UnaryOp) and expr.index.op == "-":
                is_neg = True
                offset = self._emit_expr(expr.index.operand)

            if is_neg:
                len_call = f"{arr_str}.length()" if is_str else f"{arr_str}.length"
                idx_str = f"({len_call} - {offset})"
            else:
                idx_str = self._emit_expr(expr.index)

            if is_str:
                return f"String.valueOf({arr_str}.charAt({idx_str}))"
            return f"{arr_str}[{idx_str}]"

        elif isinstance(expr, ArrayLength):
            arr_str = self._emit_expr(expr.array)
            is_str = expr.array.inferred_type.kind == TypeKind.STRING or self.var_types.get(arr_str) == "String"
            if is_str:
                return f"{arr_str}.length()"
            return f"{arr_str}.length"

        elif isinstance(expr, TernaryOp):
            cond = self._emit_condition(expr.condition)
            then_str = self._emit_expr(expr.then_expr)
            else_str = self._emit_expr(expr.else_expr)
            return f"({cond} ? {then_str} : {else_str})"

        elif isinstance(expr, CastExpr):
            op_str = self._emit_expr(expr.operand)
            if expr.target_type.kind == TypeKind.INT:
                return f"((int) ({op_str}))"
            elif expr.target_type.kind == TypeKind.FLOAT:
                return f"((double) ({op_str}))"
            elif expr.target_type.kind == TypeKind.STRING:
                return f"String.valueOf({op_str})"
            elif expr.target_type.kind == TypeKind.BOOL:
                return f"((boolean) ({op_str}))"
            return op_str

        elif isinstance(expr, MethodCall):
            obj_str = self._emit_expr(expr.object_expr)
            m = expr.method_name
            args_strs = [self._emit_expr(a) for a in expr.args]
            if m in ["lower", "toLowerCase"]:
                return f"{obj_str}.toLowerCase()"
            elif m in ["upper", "toUpperCase"]:
                return f"{obj_str}.toUpperCase()"
            elif m in ["strip", "trim"]:
                return f"{obj_str}.trim()"
            elif m in ["find", "indexOf"]:
                return f"{obj_str}.indexOf({args_strs[0]})"
            joined_args = ", ".join(args_strs)
            return f"{obj_str}.{m}({joined_args})"

        elif isinstance(expr, FunctionCall):
            args_strs = [self._emit_expr(a) for a in expr.args]
            translated, req_import = LibraryRegistry.resolve_call(expr.name, args_strs, "java", self.module_aliases)
            if req_import:
                self.used_imports.add(req_import)
            if translated:
                return translated
            args_str = ", ".join(args_strs)
            return f"{expr.name}({args_str})"

        return ""

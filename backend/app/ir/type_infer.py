from typing import Dict, Optional, List, Any
from app.ir.nodes import (
    IRType, TypeKind, Program, FunctionDef, Statement, Expression,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, VarDecl, Assignment, IfStmt, WhileStmt,
    ForRangeStmt, ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt
)

class TypeInferrer:
    """Performs type inference across the IR AST to enrich nodes with static types."""

    def __init__(self):
        self.global_env: Dict[str, IRType] = {}
        self.func_signatures: Dict[str, FunctionDef] = {}

    def infer_program(self, program: Program) -> Program:
        # First pass: register function signatures
        for fn in program.functions:
            self.func_signatures[fn.name] = fn

        # Second pass: infer types in global statements
        for stmt in program.global_statements:
            self._infer_statement(stmt, self.global_env)

        # Third pass: infer types inside each function
        for fn in program.functions:
            fn_env: Dict[str, IRType] = dict(self.global_env)
            for idx, param in enumerate(fn.params):
                if param.param_type.kind == TypeKind.UNKNOWN:
                    # Will try to infer from calls or usages
                    param.param_type = self._guess_param_type(fn, param.name, idx, program)
                fn_env[param.name] = param.param_type

            returned_types: List[IRType] = []
            for stmt in fn.body:
                self._infer_statement(stmt, fn_env, returned_types)

            if returned_types:
                # Pick the most specific return type
                best_ret = returned_types[0]
                for r in returned_types:
                    if r.kind != TypeKind.UNKNOWN and r.kind != TypeKind.VOID:
                        best_ret = r
                        break
                fn.return_type = best_ret
            elif fn.return_type.kind == TypeKind.UNKNOWN:
                fn.return_type = IRType.void_type()

        # Fourth pass: re-infer global statements now that function return types are determined
        for stmt in program.global_statements:
            self._infer_statement(stmt, self.global_env)

        return program

    def _guess_param_type(self, fn: FunctionDef, param_name: str, param_index: int = 0, program: Optional[Program] = None) -> IRType:
        # Check usages inside function body
        for stmt in fn.body:
            t = self._check_usage(stmt, param_name)
            if t:
                return t
        # Check call sites across program
        if program:
            call_type = self._find_arg_type_at_call_sites(program, fn.name, param_index)
            if call_type and call_type.kind != TypeKind.UNKNOWN:
                return call_type
        # Default to int if cannot determine
        return IRType.int_type()

    def _find_arg_type_at_call_sites(self, program: Program, func_name: str, param_index: int) -> Optional[IRType]:
        for stmt in program.global_statements:
            t = self._check_call_in_stmt(stmt, func_name, param_index)
            if t:
                return t
        for fn in program.functions:
            for stmt in fn.body:
                t = self._check_call_in_stmt(stmt, func_name, param_index)
                if t:
                    return t
        return None

    def _check_call_in_stmt(self, stmt: Any, func_name: str, param_index: int) -> Optional[IRType]:
        if not stmt:
            return None
        if isinstance(stmt, VarDecl) and stmt.initializer:
            return self._check_call_in_expr(stmt.initializer, func_name, param_index)
        elif isinstance(stmt, Assignment) and stmt.value:
            return self._check_call_in_expr(stmt.value, func_name, param_index)
        elif isinstance(stmt, ExpressionStmt) and stmt.expr:
            return self._check_call_in_expr(stmt.expr, func_name, param_index)
        elif isinstance(stmt, PrintStmt):
            for a in stmt.args:
                t = self._check_call_in_expr(a, func_name, param_index)
                if t:
                    return t
        elif isinstance(stmt, IfStmt):
            for s in stmt.then_branch:
                t = self._check_call_in_stmt(s, func_name, param_index)
                if t:
                    return t
            for s in stmt.else_branch:
                t = self._check_call_in_stmt(s, func_name, param_index)
                if t:
                    return t
        elif isinstance(stmt, WhileStmt):
            for s in stmt.body:
                t = self._check_call_in_stmt(s, func_name, param_index)
                if t:
                    return t
        elif isinstance(stmt, ForRangeStmt):
            for s in stmt.body:
                t = self._check_call_in_stmt(s, func_name, param_index)
                if t:
                    return t
        return None

    def _check_call_in_expr(self, expr: Any, func_name: str, param_index: int) -> Optional[IRType]:
        if not expr:
            return None
        if isinstance(expr, FunctionCall):
            if expr.name == func_name and param_index < len(expr.args):
                arg = expr.args[param_index]
                if isinstance(arg, Identifier) and arg.name in self.global_env:
                    return self.global_env[arg.name]
                elif isinstance(arg, ArrayLiteral):
                    return arg.inferred_type if arg.inferred_type.kind != TypeKind.UNKNOWN else IRType.array_of(IRType.int_type())
                elif isinstance(arg, Literal):
                    return arg.inferred_type
                elif arg.inferred_type and arg.inferred_type.kind != TypeKind.UNKNOWN:
                    return arg.inferred_type
            for a in expr.args:
                t = self._check_call_in_expr(a, func_name, param_index)
                if t:
                    return t
        elif isinstance(expr, BinaryOp):
            t = self._check_call_in_expr(expr.left, func_name, param_index)
            if t:
                return t
            return self._check_call_in_expr(expr.right, func_name, param_index)
        elif isinstance(expr, UnaryOp):
            return self._check_call_in_expr(expr.operand, func_name, param_index)
        return None

    def _check_usage(self, node: Any, param_name: str) -> Optional[IRType]:
        if not node:
            return None
        if isinstance(node, ArrayAccess):
            if isinstance(node.array, Identifier) and node.array.name == param_name:
                return IRType.array_of(IRType.int_type())
            if isinstance(node.array, ArrayAccess) and isinstance(node.array.array, Identifier) and node.array.array.name == param_name:
                return IRType.array_of(IRType.array_of(IRType.int_type()))
            if isinstance(node.index, Identifier) and node.index.name == param_name:
                return IRType.int_type()
            t = self._check_usage(node.array, param_name)
            if t:
                return t
            t = self._check_usage(node.index, param_name)
            if t:
                return t
        elif isinstance(node, ArrayLength):
            if isinstance(node.array, Identifier) and node.array.name == param_name:
                return IRType.array_of(IRType.int_type())
            if isinstance(node.array, ArrayAccess) and isinstance(node.array.array, Identifier) and node.array.array.name == param_name:
                return IRType.array_of(IRType.array_of(IRType.int_type()))
            t = self._check_usage(node.array, param_name)
            if t:
                return t
        elif isinstance(node, (IfStmt, WhileStmt)):
            cond_t = self._check_usage(node.condition, param_name)
            if cond_t:
                return cond_t
            for s in (node.then_branch if isinstance(node, IfStmt) else node.body):
                t = self._check_usage(s, param_name)
                if t:
                    return t
            if isinstance(node, IfStmt):
                for s in node.else_branch:
                    t = self._check_usage(s, param_name)
                    if t:
                        return t
        elif isinstance(node, ForRangeStmt):
            if (isinstance(node.start, Identifier) and node.start.name == param_name) or \
               (isinstance(node.end, Identifier) and node.end.name == param_name) or \
               (node.step and isinstance(node.step, Identifier) and node.step.name == param_name):
                return IRType.int_type()
            t = self._check_usage(node.start, param_name)
            if t:
                return t
            t = self._check_usage(node.end, param_name)
            if t:
                return t
            if node.step:
                t = self._check_usage(node.step, param_name)
                if t:
                    return t
            for s in node.body:
                t = self._check_usage(s, param_name)
                if t:
                    return t
        elif isinstance(node, VarDecl):
            if node.initializer:
                return self._check_usage(node.initializer, param_name)
        elif isinstance(node, Assignment):
            t1 = self._check_usage(node.target, param_name)
            if t1:
                return t1
            t2 = self._check_usage(node.value, param_name)
            if t2:
                return t2
        elif isinstance(node, ReturnStmt):
            if node.value:
                return self._check_usage(node.value, param_name)
        elif isinstance(node, PrintStmt):
            for a in node.args:
                t = self._check_usage(a, param_name)
                if t:
                    return t
        elif isinstance(node, ExpressionStmt):
            return self._check_usage(node.expr, param_name)
        elif isinstance(node, BinaryOp):
            if isinstance(node.left, Identifier) and node.left.name == param_name:
                if isinstance(node.right, ArrayAccess):
                    return IRType.int_type()
                if node.op in ["<", "<=", ">", ">=", "+", "-", "*", "/", "//", "%"]:
                    return IRType.int_type()
                return node.right.inferred_type if node.right and node.right.inferred_type.kind != TypeKind.UNKNOWN else IRType.int_type()
            if isinstance(node.right, Identifier) and node.right.name == param_name:
                if isinstance(node.left, ArrayAccess):
                    return IRType.int_type()
                if node.op in ["<", "<=", ">", ">=", "+", "-", "*", "/", "//", "%"]:
                    return IRType.int_type()
                return node.left.inferred_type if node.left and node.left.inferred_type.kind != TypeKind.UNKNOWN else IRType.int_type()
            t = self._check_usage(node.left, param_name)
            if t:
                return t
            t = self._check_usage(node.right, param_name)
            if t:
                return t
        elif isinstance(node, UnaryOp):
            if node.op in ["-", "+"]:
                if isinstance(node.operand, Identifier) and node.operand.name == param_name:
                    return IRType.int_type()
            elif node.op in ["!", "not"]:
                if isinstance(node.operand, Identifier) and node.operand.name == param_name:
                    return IRType.bool_type()
            return self._check_usage(node.operand, param_name)
        elif isinstance(node, FunctionCall):
            if node.name in ["len", "size"] and node.args:
                if isinstance(node.args[0], Identifier) and node.args[0].name == param_name:
                    return IRType.array_of(IRType.int_type())
            if (node.name.endswith(".append") or node.name.endswith(".push")):
                obj = node.name.split(".")[0]
                if obj == param_name:
                    return IRType.array_of(IRType.int_type())
            if node.name in ["append", "push"] and node.args:
                if isinstance(node.args[0], Identifier) and node.args[0].name == param_name:
                    return IRType.array_of(IRType.int_type())
            for a in node.args:
                t = self._check_usage(a, param_name)
                if t:
                    return t
        return None

    def _infer_statement(self, stmt: Statement, env: Dict[str, IRType], return_types: Optional[List[IRType]] = None):
        if isinstance(stmt, VarDecl):
            if stmt.initializer:
                t = self._infer_expression(stmt.initializer, env)
                if stmt.var_type.kind == TypeKind.UNKNOWN:
                    stmt.var_type = t
            env[stmt.name] = stmt.var_type

        elif isinstance(stmt, Assignment):
            val_type = self._infer_expression(stmt.value, env)
            if isinstance(stmt.target, Identifier):
                stmt.target.inferred_type = val_type
                if stmt.target.name not in env or env[stmt.target.name].kind == TypeKind.UNKNOWN:
                    env[stmt.target.name] = val_type
            elif isinstance(stmt.target, ArrayAccess):
                self._infer_expression(stmt.target, env)

        elif isinstance(stmt, IfStmt):
            self._infer_expression(stmt.condition, env)
            for s in stmt.then_branch:
                self._infer_statement(s, env, return_types)
            for s in stmt.else_branch:
                self._infer_statement(s, env, return_types)

        elif isinstance(stmt, WhileStmt):
            self._infer_expression(stmt.condition, env)
            for s in stmt.body:
                self._infer_statement(s, env, return_types)

        elif isinstance(stmt, ForRangeStmt):
            env[stmt.var_name] = IRType.int_type()
            if stmt.start:
                self._infer_expression(stmt.start, env)
            if stmt.end:
                self._infer_expression(stmt.end, env)
            if stmt.step:
                self._infer_expression(stmt.step, env)
            for s in stmt.body:
                self._infer_statement(s, env, return_types)

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                t = self._infer_expression(stmt.value, env)
                if return_types is not None:
                    return_types.append(t)
            elif return_types is not None:
                return_types.append(IRType.void_type())

        elif isinstance(stmt, PrintStmt):
            for arg in stmt.args:
                self._infer_expression(arg, env)

        elif isinstance(stmt, (BreakStmt, ContinueStmt)):
            pass

        elif isinstance(stmt, ExpressionStmt):
            self._infer_expression(stmt.expr, env)
            if isinstance(stmt.expr, FunctionCall):
                name = stmt.expr.name
                if (name.endswith(".append") or name.endswith(".push")) and stmt.expr.args:
                    obj = name.split(".")[0]
                    if obj in env and env[obj].kind == TypeKind.ARRAY:
                        arg_type = self._infer_expression(stmt.expr.args[0], env)
                        if env[obj].element_type is None or env[obj].element_type.kind == TypeKind.UNKNOWN:
                            env[obj].element_type = arg_type

    def _infer_expression(self, expr: Expression, env: Dict[str, IRType]) -> IRType:
        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                expr.inferred_type = IRType.bool_type()
            elif isinstance(expr.value, int):
                expr.inferred_type = IRType.int_type()
            elif isinstance(expr.value, float):
                expr.inferred_type = IRType.float_type()
            elif isinstance(expr.value, str):
                expr.inferred_type = IRType.string_type()
            return expr.inferred_type

        elif isinstance(expr, Identifier):
            if expr.name in env:
                expr.inferred_type = env[expr.name]
            else:
                expr.inferred_type = IRType.int_type()  # sensible fallback
            return expr.inferred_type

        elif isinstance(expr, BinaryOp):
            lt = self._infer_expression(expr.left, env) if expr.left else IRType.unknown()
            rt = self._infer_expression(expr.right, env) if expr.right else IRType.unknown()

            if expr.op in ["==", "!=", "<", "<=", ">", ">=", "&&", "||", "and", "or"]:
                expr.inferred_type = IRType.bool_type()
            elif expr.op in ["//"]:
                expr.inferred_type = IRType.int_type()
            elif expr.op == "/":
                if lt.kind == TypeKind.INT and rt.kind == TypeKind.INT:
                    expr.inferred_type = IRType.int_type()
                else:
                    expr.inferred_type = IRType.float_type()
            elif lt.kind == TypeKind.STRING or rt.kind == TypeKind.STRING:
                expr.inferred_type = IRType.string_type()
            elif lt.kind == TypeKind.FLOAT or rt.kind == TypeKind.FLOAT:
                expr.inferred_type = IRType.float_type()
            else:
                expr.inferred_type = IRType.int_type()
            return expr.inferred_type

        elif isinstance(expr, UnaryOp):
            if expr.op in ["!", "not"]:
                expr.inferred_type = IRType.bool_type()
            else:
                inner = self._infer_expression(expr.operand, env) if expr.operand else IRType.int_type()
                expr.inferred_type = inner
            return expr.inferred_type

        elif isinstance(expr, ArrayLiteral):
            if expr.elements:
                elem_types = [self._infer_expression(e, env) for e in expr.elements]
                elem_type = elem_types[0]
                expr.inferred_type = IRType.array_of(elem_type)
            else:
                expr.inferred_type = IRType.array_of(IRType.int_type())
            return expr.inferred_type

        elif isinstance(expr, ArrayAccess):
            arr_type = self._infer_expression(expr.array, env) if expr.array else IRType.unknown()
            if expr.index:
                self._infer_expression(expr.index, env)
            if arr_type.kind == TypeKind.STRING:
                expr.inferred_type = IRType.string_type()
            elif arr_type.kind == TypeKind.ARRAY and arr_type.element_type:
                expr.inferred_type = arr_type.element_type
            else:
                expr.inferred_type = IRType.int_type()
            return expr.inferred_type

        elif isinstance(expr, ArrayLength):
            if expr.array:
                self._infer_expression(expr.array, env)
            expr.inferred_type = IRType.int_type()
            return expr.inferred_type

        elif isinstance(expr, FunctionCall):
            for a in expr.args:
                self._infer_expression(a, env)
            if expr.name in self.func_signatures:
                expr.inferred_type = self.func_signatures[expr.name].return_type
            elif any(expr.name.lower().endswith(f".{fn}") or expr.name.lower() == fn for fn in ["sqrt", "sin", "cos", "tan", "log", "exp", "pow"]):
                expr.inferred_type = IRType.float_type()
            elif any(expr.name.lower().endswith(f".{fn}") or expr.name.lower() == fn for fn in ["floor", "ceil", "round", "abs"]):
                expr.inferred_type = IRType.int_type()
            else:
                expr.inferred_type = IRType.unknown()
            return expr.inferred_type

        return IRType.unknown()

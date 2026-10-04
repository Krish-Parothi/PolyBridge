from typing import Dict, Optional, List, Any
from app.ir.nodes import (
    IRType, TypeKind, Program, FunctionDef, Statement, Expression,
Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
ArrayLength, FunctionCall, VarDecl, Assignment, IfStmt, WhileStmt,
ForRangeStmt, ReturnStmt, PrintStmt, ExpressionStmt
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
            for param in fn.params:
                if param.param_type.kind == TypeKind.UNKNOWN:
                    # Will try to infer from calls or usages
                    param.param_type = self._guess_param_type(fn, param.name)
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

        return program

    def _guess_param_type(self, fn: FunctionDef, param_name: str) -> IRType:
        # Check usages inside function body
        for stmt in fn.body:
            t = self._check_usage(stmt, param_name)
            if t:
                return t
        # Default to int if cannot determine
        return IRType.int_type()

    def _check_usage(self, node: Any, param_name: str) -> Optional[IRType]:
        if isinstance(node, ArrayAccess):
            if isinstance(node.array, Identifier) and node.array.name == param_name:
                return IRType.array_of(IRType.int_type())
        elif isinstance(node, ArrayLength):
            if isinstance(node.array, Identifier) and node.array.name == param_name:
                return IRType.array_of(IRType.int_type())
        elif isinstance(node, (IfStmt, WhileStmt)):
            cond_t = self._check_usage(node.condition, param_name)
            if cond_t:
                return cond_t
            for s in (node.then_branch if isinstance(node, IfStmt) else node.body):
                t = self._check_usage(s, param_name)
                if t:
                    return t
        elif isinstance(node, Assignment):
            t1 = self._check_usage(node.target, param_name)
            if t1:
                return t1
            t2 = self._check_usage(node.value, param_name)
            if t2:
                return t2
        elif isinstance(node, BinaryOp):
            if isinstance(node.left, Identifier) and node.left.name == param_name:
                return node.right.inferred_type if node.right else IRType.int_type()
            if isinstance(node.right, Identifier) and node.right.name == param_name:
                return node.left.inferred_type if node.left else IRType.int_type()
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

        elif isinstance(stmt, ExpressionStmt):
            self._infer_expression(stmt.expr, env)

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
            elif expr.op == "/":
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
            if arr_type.kind == TypeKind.ARRAY and arr_type.element_type:
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
            else:
                expr.inferred_type = IRType.unknown()
            return expr.inferred_type

        return IRType.unknown()

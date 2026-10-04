from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class PythonParser:
    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []

        for child in root.children:
            if child.type == "function_definition":
                fn = self._parse_function(child, code_bytes)
                if fn:
                    functions.append(fn)
            else:
                stmts = self._parse_statement(child, code_bytes)
                if stmts:
                    global_statements.extend(stmts)

        return Program(functions=functions, global_statements=global_statements)

    def _get_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _parse_function(self, node: Node, code_bytes: bytes) -> Optional[FunctionDef]:
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        body_node = node.child_by_field_name("body")

        if not name_node or not body_node:
            return None

        func_name = self._get_text(name_node, code_bytes)
        params: List[Parameter] = []
        if params_node:
            for p in params_node.children:
                if p.type == "identifier":
                    params.append(Parameter(name=self._get_text(p, code_bytes), param_type=IRType.unknown()))

        body_stmts: List[Statement] = []
        for child in body_node.children:
            stmts = self._parse_statement(child, code_bytes)
            if stmts:
                body_stmts.extend(stmts)

        return FunctionDef(
            name=func_name,
            params=params,
            return_type=IRType.unknown(),
            body=body_stmts
        )

    def _parse_statement(self, node: Node, code_bytes: bytes) -> List[Statement]:
        ntype = node.type

        if ntype == "expression_statement":
            first_child = node.children[0] if node.children else None
            if not first_child:
                return []
            if first_child.type == "assignment":
                return self._parse_assignment(first_child, code_bytes)
            else:
                expr = self._parse_expression(first_child, code_bytes)
                if isinstance(expr, FunctionCall) and expr.name == "print":
                    return [PrintStmt(args=expr.args)]
                return [ExpressionStmt(expr=expr)] if expr else []

        elif ntype == "if_statement":
            return self._parse_if(node, code_bytes)

        elif ntype == "while_statement":
            cond_node = node.child_by_field_name("condition")
            body_node = node.child_by_field_name("body")
            cond = self._parse_expression(cond_node, code_bytes) if cond_node else Literal(True)
            body: List[Statement] = []
            if body_node:
                for c in body_node.children:
                    s = self._parse_statement(c, code_bytes)
                    if s:
                        body.extend(s)
            return [WhileStmt(condition=cond, body=body)]

        elif ntype == "for_statement":
            return self._parse_for(node, code_bytes)

        elif ntype == "return_statement":
            val = None
            for c in node.children:
                if c.type != "return":
                    val = self._parse_expression(c, code_bytes)
                    break
            return [ReturnStmt(value=val)]

        return []

    def _parse_assignment(self, node: Node, code_bytes: bytes) -> List[Statement]:
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")

        if not left_node or not right_node:
            return []

        # Handle tuple swap like: a, b = b, a or arr[j], arr[j+1] = arr[j+1], arr[j]
        if left_node.type == "pattern_list" and right_node.type in ["expression_list", "pattern_list"]:
            left_targets = [self._parse_expression(c, code_bytes) for c in left_node.children if c.type not in [",", "(", ")"]]
            right_vals = [self._parse_expression(c, code_bytes) for c in right_node.children if c.type not in [",", "(", ")"]]
            stmts: List[Statement] = []
            # Use temp variables for multiple assignments
            for i, (t, v) in enumerate(zip(left_targets, right_vals)):
                temp_name = f"__temp_{i}"
                stmts.append(VarDecl(name=temp_name, var_type=IRType.unknown(), initializer=v))
            for i, t in enumerate(left_targets):
                temp_name = f"__temp_{i}"
                stmts.append(Assignment(target=t, value=Identifier(name=temp_name)))
            return stmts

        target = self._parse_expression(left_node, code_bytes)
        value = self._parse_expression(right_node, code_bytes)

        # In IR, simple identifier assignment at definition time can be treated as VarDecl or Assignment.
        # We emit Assignment, and type inferrer / emitters wrap variable declarations properly.
        return [Assignment(target=target, value=value)]

    def _parse_if(self, node: Node, code_bytes: bytes) -> List[Statement]:
        cond_node = node.child_by_field_name("condition")
        consequence_node = node.child_by_field_name("consequence")
        alternative_node = node.child_by_field_name("alternative")

        cond = self._parse_expression(cond_node, code_bytes) if cond_node else Literal(True)
        then_branch: List[Statement] = []
        if consequence_node:
            for c in consequence_node.children:
                s = self._parse_statement(c, code_bytes)
                if s:
                    then_branch.extend(s)

        else_branch: List[Statement] = []
        if alternative_node:
            # alternative could be elif_clause or else_clause
            for c in alternative_node.children:
                if c.type in ["elif_clause", "if_statement"]:
                    s = self._parse_if(c, code_bytes)
                    else_branch.extend(s)
                elif c.type == "else_clause":
                    body = c.child_by_field_name("body")
                    if body:
                        for bc in body.children:
                            s = self._parse_statement(bc, code_bytes)
                            if s:
                                else_branch.extend(s)
                elif c.type not in ["else", ":"]:
                    s = self._parse_statement(c, code_bytes)
                    if s:
                        else_branch.extend(s)

        return [IfStmt(condition=cond, then_branch=then_branch, else_branch=else_branch)]

    def _parse_for(self, node: Node, code_bytes: bytes) -> List[Statement]:
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")
        body_node = node.child_by_field_name("body")

        var_name = self._get_text(left_node, code_bytes) if left_node else "i"

        start_expr: Expression = Literal(0)
        end_expr: Expression = Literal(0)
        step_expr: Optional[Expression] = None

        if right_node and right_node.type == "call":
            fn_node = right_node.child_by_field_name("function")
            fn_name = self._get_text(fn_node, code_bytes) if fn_node else ""
            if fn_name == "range":
                args_node = right_node.child_by_field_name("arguments")
                args = []
                if args_node:
                    for a in args_node.children:
                        if a.type not in ["(", ")", ","]:
                            args.append(self._parse_expression(a, code_bytes))
                if len(args) == 1:
                    start_expr = Literal(0)
                    end_expr = args[0]
                elif len(args) == 2:
                    start_expr = args[0]
                    end_expr = args[1]
                elif len(args) >= 3:
                    start_expr = args[0]
                    end_expr = args[1]
                    step_expr = args[2]

        body: List[Statement] = []
        if body_node:
            for c in body_node.children:
                s = self._parse_statement(c, code_bytes)
                if s:
                    body.extend(s)

        return [ForRangeStmt(
            var_name=var_name,
            start=start_expr,
            end=end_expr,
            step=step_expr,
            body=body
        )]

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype == "integer":
            text = self._get_text(node, code_bytes)
            return Literal(int(text))
        elif ntype == "float":
            text = self._get_text(node, code_bytes)
            return Literal(float(text))
        elif ntype == "string":
            text = self._get_text(node, code_bytes)
            # Strip quotes
            clean_str = text[1:-1] if len(text) >= 2 and text[0] in ['"', "'"] else text
            return Literal(clean_str)
        elif ntype == "true":
            return Literal(True)
        elif ntype == "false":
            return Literal(False)
        elif ntype == "identifier":
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "binary_operator" or ntype == "comparison_operator" or ntype == "boolean_operator":
            # left op right
            left_node = node.child_by_field_name("left") or node.children[0]
            right_node = node.child_by_field_name("right") or node.children[-1]
            op_text = ""
            for c in node.children:
                if c != left_node and c != right_node and c.type not in ["comment"]:
                    op_text = self._get_text(c, code_bytes).strip()
                    break

            # Normalize operators
            op_norm = op_text
            if op_norm == "and":
                op_norm = "&&"
            elif op_norm == "or":
                op_norm = "||"

            left = self._parse_expression(left_node, code_bytes)
            right = self._parse_expression(right_node, code_bytes)
            return BinaryOp(left=left, op=op_norm, right=right)

        elif ntype == "unary_operator":
            op_node = node.children[0]
            op_text = self._get_text(op_node, code_bytes)
            arg_node = node.children[1] if len(node.children) > 1 else None
            return UnaryOp(op=op_text, operand=self._parse_expression(arg_node, code_bytes))

        elif ntype == "not_operator":
            arg_node = node.children[1] if len(node.children) > 1 else None
            return UnaryOp(op="!", operand=self._parse_expression(arg_node, code_bytes))

        elif ntype == "list":
            elements: List[Expression] = []
            for c in node.children:
                if c.type not in ["[", "]", ","]:
                    elem = self._parse_expression(c, code_bytes)
                    if elem:
                        elements.append(elem)
            return ArrayLiteral(elements=elements)

        elif ntype == "subscript":
            val_node = node.child_by_field_name("value")
            sub_node = node.child_by_field_name("subscript")
            array_expr = self._parse_expression(val_node, code_bytes)
            idx_expr = self._parse_expression(sub_node, code_bytes)
            return ArrayAccess(array=array_expr, index=idx_expr)

        elif ntype == "call":
            fn_node = node.child_by_field_name("function")
            fn_name = self._get_text(fn_node, code_bytes) if fn_node else ""
            args_node = node.child_by_field_name("arguments")
            args: List[Expression] = []
            if args_node:
                for c in args_node.children:
                    if c.type not in ["(", ")", ","]:
                        a = self._parse_expression(c, code_bytes)
                        if a:
                            args.append(a)

            if fn_name == "len" and len(args) == 1:
                return ArrayLength(array=args[0])
            elif fn_name == "print":
                return FunctionCall(name="print", args=args)
            else:
                return FunctionCall(name=fn_name, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        return None

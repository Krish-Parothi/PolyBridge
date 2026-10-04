from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_javascript as tsjavascript

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class JavaScriptParser:
    def __init__(self):
        self.language = Language(tsjavascript.language())
        self.parser = Parser(self.language)

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []

        for child in root.children:
            if child.type == "function_declaration":
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

        if ntype in ["lexical_declaration", "variable_declaration"]:
            stmts: List[Statement] = []
            for declarator in node.children:
                if declarator.type == "variable_declarator":
                    name_n = declarator.child_by_field_name("name")
                    val_n = declarator.child_by_field_name("value")
                    var_name = self._get_text(name_n, code_bytes) if name_n else ""
                    init_val = self._parse_expression(val_n, code_bytes) if val_n else None
                    stmts.append(VarDecl(name=var_name, var_type=IRType.unknown(), initializer=init_val))
            return stmts

        elif ntype == "expression_statement":
            first_child = node.children[0] if node.children else None
            if not first_child:
                return []
            if first_child.type == "assignment_expression":
                left_n = first_child.child_by_field_name("left")
                right_n = first_child.child_by_field_name("right")
                target = self._parse_expression(left_n, code_bytes)
                value = self._parse_expression(right_n, code_bytes)
                return [Assignment(target=target, value=value)]
            elif first_child.type == "call_expression":
                expr = self._parse_expression(first_child, code_bytes)
                if isinstance(expr, FunctionCall) and expr.name == "print":
                    return [PrintStmt(args=expr.args)]
                return [ExpressionStmt(expr=expr)] if expr else []
            elif first_child.type == "update_expression":
                # e.g., i++ or i--
                text = self._get_text(first_child, code_bytes)
                var_name = text.replace("+", "").replace("-", "").strip()
                op = "+" if "++" in text else "-"
                return [Assignment(
                    target=Identifier(name=var_name),
                    value=BinaryOp(left=Identifier(name=var_name), op=op, right=Literal(1))
                )]
            return []

        elif ntype == "if_statement":
            cond_n = node.child_by_field_name("condition")
            then_n = node.child_by_field_name("consequence")
            else_n = node.child_by_field_name("alternative")

            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            then_body: List[Statement] = []
            if then_n:
                if then_n.type == "statement_block":
                    for c in then_n.children:
                        then_body.extend(self._parse_statement(c, code_bytes))
                else:
                    then_body.extend(self._parse_statement(then_n, code_bytes))

            else_body: List[Statement] = []
            if else_n:
                if else_n.type == "else_clause":
                    for c in else_n.children:
                        if c.type not in ["else", ";"]:
                            if c.type == "statement_block":
                                for sc in c.children:
                                    else_body.extend(self._parse_statement(sc, code_bytes))
                            else:
                                else_body.extend(self._parse_statement(c, code_bytes))
                else:
                    else_body.extend(self._parse_statement(else_n, code_bytes))

            return [IfStmt(condition=cond, then_branch=then_body, else_branch=else_body)]

        elif ntype == "while_statement":
            cond_n = node.child_by_field_name("condition")
            body_n = node.child_by_field_name("body")
            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            body: List[Statement] = []
            if body_n:
                for c in body_n.children:
                    body.extend(self._parse_statement(c, code_bytes))
            return [WhileStmt(condition=cond, body=body)]

        elif ntype == "for_statement":
            return self._parse_for(node, code_bytes)

        elif ntype == "return_statement":
            val = None
            for c in node.children:
                if c.type not in ["return", ";"]:
                    val = self._parse_expression(c, code_bytes)
                    break
            return [ReturnStmt(value=val)]

        elif ntype == "statement_block":
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["{", "}"]:
                    stmts.extend(self._parse_statement(c, code_bytes))
            return stmts

        return []

    def _parse_for(self, node: Node, code_bytes: bytes) -> List[Statement]:
        init_n = node.child_by_field_name("initializer")
        cond_n = node.child_by_field_name("condition")
        body_n = node.child_by_field_name("body")

        var_name = "i"
        start_expr: Expression = Literal(0)
        end_expr: Expression = Literal(0)

        # Inspect initializer: let i = 0
        if init_n:
            if init_n.type in ["lexical_declaration", "variable_declaration"]:
                for d in init_n.children:
                    if d.type == "variable_declarator":
                        name_n = d.child_by_field_name("name")
                        val_n = d.child_by_field_name("value")
                        if name_n:
                            var_name = self._get_text(name_n, code_bytes)
                        if val_n:
                            start_expr = self._parse_expression(val_n, code_bytes) or Literal(0)
            elif init_n.type == "assignment_expression":
                left_n = init_n.child_by_field_name("left")
                right_n = init_n.child_by_field_name("right")
                if left_n:
                    var_name = self._get_text(left_n, code_bytes)
                if right_n:
                    start_expr = self._parse_expression(right_n, code_bytes) or Literal(0)

        # Inspect condition: i < n or i <= n
        if cond_n and cond_n.type == "binary_expression":
            right_n = cond_n.child_by_field_name("right")
            if right_n:
                end_expr = self._parse_expression(right_n, code_bytes) or Literal(0)

        body: List[Statement] = []
        if body_n:
            if body_n.type == "statement_block":
                for c in body_n.children:
                    if c.type not in ["{", "}"]:
                        body.extend(self._parse_statement(c, code_bytes))
            else:
                body.extend(self._parse_statement(body_n, code_bytes))

        return [ForRangeStmt(
            var_name=var_name,
            start=start_expr,
            end=end_expr,
            step=None,
            body=body
        )]

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype == "number":
            text = self._get_text(node, code_bytes)
            if "." in text:
                return Literal(float(text))
            return Literal(int(text))

        elif ntype == "string":
            text = self._get_text(node, code_bytes)
            clean_str = text[1:-1] if len(text) >= 2 and text[0] in ['"', "'", '`'] else text
            return Literal(clean_str)

        elif ntype == "true":
            return Literal(True)

        elif ntype == "false":
            return Literal(False)

        elif ntype == "identifier":
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "binary_expression":
            left_n = node.child_by_field_name("left")
            op_n = node.child_by_field_name("operator")
            right_n = node.child_by_field_name("right")
            op_text = self._get_text(op_n, code_bytes) if op_n else ""
            left = self._parse_expression(left_n, code_bytes)
            right = self._parse_expression(right_n, code_bytes)
            return BinaryOp(left=left, op=op_text, right=right)

        elif ntype == "unary_expression":
            op_n = node.child_by_field_name("operator")
            arg_n = node.child_by_field_name("argument")
            op_text = self._get_text(op_n, code_bytes) if op_n else ""
            arg = self._parse_expression(arg_n, code_bytes)
            return UnaryOp(op=op_text, operand=arg)

        elif ntype == "array":
            elements: List[Expression] = []
            for c in node.children:
                if c.type not in ["[", "]", ","]:
                    elem = self._parse_expression(c, code_bytes)
                    if elem:
                        elements.append(elem)
            return ArrayLiteral(elements=elements)

        elif ntype == "subscript_expression":
            obj_n = node.child_by_field_name("object")
            idx_n = node.child_by_field_name("index")
            return ArrayAccess(
                array=self._parse_expression(obj_n, code_bytes),
                index=self._parse_expression(idx_n, code_bytes)
            )

        elif ntype == "member_expression":
            # Check for arr.length
            obj_n = node.child_by_field_name("object")
            prop_n = node.child_by_field_name("property")
            prop_text = self._get_text(prop_n, code_bytes) if prop_n else ""
            if prop_text == "length":
                return ArrayLength(array=self._parse_expression(obj_n, code_bytes))
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "call_expression":
            fn_n = node.child_by_field_name("function")
            args_n = node.child_by_field_name("arguments")
            fn_text = self._get_text(fn_n, code_bytes) if fn_n else ""

            args: List[Expression] = []
            if args_n:
                for c in args_n.children:
                    if c.type not in ["(", ")", ","]:
                        a = self._parse_expression(c, code_bytes)
                        if a:
                            args.append(a)

            if fn_text == "console.log":
                return FunctionCall(name="print", args=args)
            return FunctionCall(name=fn_text, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        return None

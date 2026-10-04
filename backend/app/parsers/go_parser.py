from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_go as tsgo

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class GoParser:
    def __init__(self):
        self.language = Language(tsgo.language())
        self.parser = Parser(self.language)

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []

        for child in root.children:
            if child.type == "function_declaration":
                name_n = child.child_by_field_name("name")
                fn_name = self._get_text(name_n, code_bytes) if name_n else ""
                if fn_name == "main":
                    body_n = child.child_by_field_name("body")
                    if body_n:
                        for s in body_n.children:
                            if s.type == "statement_list":
                                for sc in s.children:
                                    parsed_s = self._parse_statement(sc, code_bytes)
                                    if parsed_s:
                                        global_statements.extend(parsed_s)
                            elif s.type not in ["{", "}"]:
                                parsed_s = self._parse_statement(s, code_bytes)
                                if parsed_s:
                                    global_statements.extend(parsed_s)
                else:
                    fn = self._parse_function(child, code_bytes)
                    if fn:
                        functions.append(fn)

        return Program(functions=functions, global_statements=global_statements)

    def _get_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _parse_type(self, type_text: str) -> IRType:
        type_text = type_text.strip()
        if type_text.startswith("[]"):
            base = self._parse_type(type_text[2:])
            return IRType.array_of(base)
        if type_text in ["int", "int64", "int32", "uint"]:
            return IRType.int_type()
        if type_text in ["float64", "float32"]:
            return IRType.float_type()
        if type_text in ["string", "rune", "byte"]:
            return IRType.string_type()
        if type_text == "bool":
            return IRType.bool_type()
        return IRType.unknown()

    def _parse_function(self, node: Node, code_bytes: bytes) -> Optional[FunctionDef]:
        name_n = node.child_by_field_name("name")
        params_n = node.child_by_field_name("parameters")
        result_n = node.child_by_field_name("result")
        body_n = node.child_by_field_name("body")

        if not name_n or not body_n:
            return None

        func_name = self._get_text(name_n, code_bytes)
        ret_type = self._parse_type(self._get_text(result_n, code_bytes)) if result_n else IRType.void_type()

        params: List[Parameter] = []
        if params_n:
            for p in params_n.children:
                if p.type == "parameter_declaration":
                    pn = p.child_by_field_name("name")
                    pt = p.child_by_field_name("type")
                    p_name = self._get_text(pn, code_bytes) if pn else ""
                    p_type = self._parse_type(self._get_text(pt, code_bytes)) if pt else IRType.unknown()
                    params.append(Parameter(name=p_name, param_type=p_type))

        body_stmts: List[Statement] = []
        for c in body_n.children:
            if c.type == "statement_list":
                for sc in c.children:
                    s = self._parse_statement(sc, code_bytes)
                    if s:
                        body_stmts.extend(s)
            elif c.type not in ["{", "}"]:
                s = self._parse_statement(c, code_bytes)
                if s:
                    body_stmts.extend(s)

        return FunctionDef(
            name=func_name,
            params=params,
            return_type=ret_type,
            body=body_stmts
        )

    def _parse_statement(self, node: Node, code_bytes: bytes) -> List[Statement]:
        ntype = node.type

        if ntype == "short_var_declaration":
            # left := right
            left_n = node.child_by_field_name("left")
            right_n = node.child_by_field_name("right")
            if left_n and right_n:
                var_name = self._get_text(left_n, code_bytes)
                val_expr = self._parse_expression(right_n, code_bytes)
                return [VarDecl(name=var_name, var_type=IRType.unknown(), initializer=val_expr)]

        elif ntype == "var_declaration":
            # var x int = 10
            stmts: List[Statement] = []
            for spec in node.children:
                if spec.type == "var_spec":
                    name_n = spec.child_by_field_name("name")
                    type_n = spec.child_by_field_name("type")
                    val_n = spec.child_by_field_name("value")
                    var_name = self._get_text(name_n, code_bytes) if name_n else ""
                    var_type = self._parse_type(self._get_text(type_n, code_bytes)) if type_n else IRType.unknown()
                    val_expr = self._parse_expression(val_n, code_bytes) if val_n else None
                    stmts.append(VarDecl(name=var_name, var_type=var_type, initializer=val_expr))
            return stmts

        elif ntype == "assignment_statement":
            left_n = node.child_by_field_name("left")
            right_n = node.child_by_field_name("right")
            target = self._parse_expression(left_n, code_bytes)
            value = self._parse_expression(right_n, code_bytes)
            return [Assignment(target=target, value=value)]

        elif ntype == "inc_statement" or ntype == "dec_statement":
            first_c = node.children[0]
            var_name = self._get_text(first_c, code_bytes)
            op = "+" if ntype == "inc_statement" else "-"
            return [Assignment(
                target=Identifier(name=var_name),
                value=BinaryOp(left=Identifier(name=var_name), op=op, right=Literal(1))
            )]

        elif ntype == "expression_statement":
            expr_n = node.children[0] if node.children else None
            if not expr_n:
                return []
            expr = self._parse_expression(expr_n, code_bytes)
            if isinstance(expr, FunctionCall) and expr.name == "print":
                return [PrintStmt(args=expr.args)]
            return [ExpressionStmt(expr=expr)] if expr else []

        elif ntype == "if_statement":
            cond_n = node.child_by_field_name("condition")
            consequence_n = node.child_by_field_name("consequence")
            alternative_n = node.child_by_field_name("alternative")

            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            then_body = self._parse_block_or_stmt(consequence_n, code_bytes)
            else_body = self._parse_block_or_stmt(alternative_n, code_bytes) if alternative_n else []
            return [IfStmt(condition=cond, then_branch=then_body, else_branch=else_body)]

        elif ntype == "for_statement":
            # Can have for_clause: init; cond; post
            for_clause = None
            for c in node.children:
                if c.type == "for_clause":
                    for_clause = c
                    break

            body_n = node.child_by_field_name("body")
            body = self._parse_block_or_stmt(body_n, code_bytes)

            if for_clause:
                init_n = for_clause.child_by_field_name("initializer")
                cond_n = for_clause.child_by_field_name("condition")
                var_name = "i"
                start_expr = Literal(0)
                end_expr = Literal(0)

                if init_n:
                    if init_n.type == "short_var_declaration":
                        l = init_n.child_by_field_name("left")
                        r = init_n.child_by_field_name("right")
                        if l:
                            var_name = self._get_text(l, code_bytes)
                        if r:
                            start_expr = self._parse_expression(r, code_bytes) or Literal(0)

                if cond_n and cond_n.type == "binary_expression":
                    r = cond_n.child_by_field_name("right")
                    if r:
                        end_expr = self._parse_expression(r, code_bytes) or Literal(0)

                return [ForRangeStmt(var_name=var_name, start=start_expr, end=end_expr, step=None, body=body)]
            else:
                # while-like condition
                cond_n = node.child_by_field_name("condition")
                cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
                return [WhileStmt(condition=cond, body=body)]

        elif ntype == "return_statement":
            val = None
            for c in node.children:
                if c.type != "return":
                    val = self._parse_expression(c, code_bytes)
                    break
            return [ReturnStmt(value=val)]

        elif ntype == "block":
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["{", "}"]:
                    stmts.extend(self._parse_statement(c, code_bytes))
            return stmts

        return []

    def _parse_block_or_stmt(self, node: Optional[Node], code_bytes: bytes) -> List[Statement]:
        if not node:
            return []
        if node.type in ["block", "statement_list"]:
            stmts: List[Statement] = []
            for c in node.children:
                if c.type == "statement_list":
                    for sc in c.children:
                        stmts.extend(self._parse_statement(sc, code_bytes))
                elif c.type not in ["{", "}"]:
                    stmts.extend(self._parse_statement(c, code_bytes))
            return stmts
        return self._parse_statement(node, code_bytes)

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype == "int_literal":
            text = self._get_text(node, code_bytes)
            return Literal(int(text))
        elif ntype == "float_literal":
            text = self._get_text(node, code_bytes)
            return Literal(float(text))
        elif ntype in ["interpreted_string_literal", "raw_string_literal"]:
            text = self._get_text(node, code_bytes)
            clean_str = text[1:-1] if len(text) >= 2 else text
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
            arg_n = node.child_by_field_name("operand")
            op_text = self._get_text(op_n, code_bytes) if op_n else ""
            arg = self._parse_expression(arg_n, code_bytes)
            return UnaryOp(op=op_text, operand=arg)

        elif ntype == "composite_literal":
            # []int{1, 2, 3}
            body_n = node.child_by_field_name("body")
            elements: List[Expression] = []
            if body_n:
                for c in body_n.children:
                    if c.type not in ["{", "}", ","]:
                        elem = self._parse_expression(c, code_bytes)
                        if elem:
                            elements.append(elem)
            return ArrayLiteral(elements=elements)

        elif ntype == "index_expression":
            operand_n = node.child_by_field_name("operand")
            index_n = node.child_by_field_name("index")
            return ArrayAccess(
                array=self._parse_expression(operand_n, code_bytes),
                index=self._parse_expression(index_n, code_bytes)
            )

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

            if fn_text in ["fmt.Println", "fmt.Print", "println", "print"]:
                return FunctionCall(name="print", args=args)
            elif fn_text == "len" and len(args) == 1:
                return ArrayLength(array=args[0])
            return FunctionCall(name=fn_text, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        return None

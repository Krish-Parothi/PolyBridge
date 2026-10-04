from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_java as tsjava

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind
    )

class JavaParser:
    def __init__(self):
        self.language = Language(tsjava.language())
        self.parser = Parser(self.language)

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []

        # Find the class declaration
        class_node = None
        for child in root.children:
            if child.type == "class_declaration":
                class_node = child
                break

        if not class_node:
            # Fallback if bare statements
            for child in root.children:
                stmts = self._parse_statement(child, code_bytes)
                if stmts:
                    global_statements.extend(stmts)
            return Program(functions=functions, global_statements=global_statements)

        class_body = class_node.child_by_field_name("body")
        if not class_body:
            return Program()

        for child in class_body.children:
            if child.type == "method_declaration":
                name_n = child.child_by_field_name("name")
                method_name = self._get_text(name_n, code_bytes) if name_n else ""
                if method_name == "main":
                    # Extract body of main() as global statements
                    body_n = child.child_by_field_name("body")
                    if body_n:
                        for s in body_n.children:
                            if s.type not in ["{", "}"]:
                                parsed_s = self._parse_statement(s, code_bytes)
                                if parsed_s:
                                    global_statements.extend(parsed_s)
                else:
                    fn = self._parse_method(child, code_bytes)
                    if fn:
                        functions.append(fn)

        return Program(functions=functions, global_statements=global_statements)

    def _get_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _parse_type(self, type_text: str) -> IRType:
        type_text = type_text.strip()
        if type_text.endswith("[]"):
            base = self._parse_type(type_text[:-2])
            return IRType.array_of(base)
        if type_text in ["int", "long", "short", "byte", "Integer"]:
            return IRType.int_type()
        if type_text in ["double", "float", "Double", "Float"]:
            return IRType.float_type()
        if type_text in ["String", "char"]:
            return IRType.string_type()
        if type_text in ["boolean", "Boolean"]:
            return IRType.bool_type()
        if type_text == "void":
            return IRType.void_type()
        return IRType.unknown()

    def _parse_method(self, node: Node, code_bytes: bytes) -> Optional[FunctionDef]:
        name_n = node.child_by_field_name("name")
        params_n = node.child_by_field_name("parameters")
        type_n = node.child_by_field_name("type")
        body_n = node.child_by_field_name("body")

        if not name_n or not body_n:
            return None

        func_name = self._get_text(name_n, code_bytes)
        ret_type = self._parse_type(self._get_text(type_n, code_bytes)) if type_n else IRType.void_type()

        params: List[Parameter] = []
        if params_n:
            for p in params_n.children:
                if p.type == "formal_parameter":
                    pn = p.child_by_field_name("name")
                    pt = p.child_by_field_name("type")
                    p_name = self._get_text(pn, code_bytes) if pn else ""
                    p_type = self._parse_type(self._get_text(pt, code_bytes)) if pt else IRType.unknown()
                    params.append(Parameter(name=p_name, param_type=p_type))

        body_stmts: List[Statement] = []
        for c in body_n.children:
            if c.type not in ["{", "}"]:
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

        if ntype == "local_variable_declaration":
            type_n = node.child_by_field_name("type")
            var_type = self._parse_type(self._get_text(type_n, code_bytes)) if type_n else IRType.unknown()
            stmts: List[Statement] = []
            for c in node.children:
                if c.type == "variable_declarator":
                    name_n = c.child_by_field_name("name")
                    val_n = c.child_by_field_name("value")
                    var_name = self._get_text(name_n, code_bytes) if name_n else ""
                    init_expr = self._parse_expression(val_n, code_bytes) if val_n else None
                    stmts.append(VarDecl(name=var_name, var_type=var_type, initializer=init_expr))
            return stmts

        elif ntype == "expression_statement":
            expr_n = node.children[0] if node.children else None
            if not expr_n:
                return []
            if expr_n.type == "assignment_expression":
                left_n = expr_n.child_by_field_name("left")
                right_n = expr_n.child_by_field_name("right")
                target = self._parse_expression(left_n, code_bytes)
                value = self._parse_expression(right_n, code_bytes)
                return [Assignment(target=target, value=value)]
            elif expr_n.type == "method_invocation":
                expr = self._parse_expression(expr_n, code_bytes)
                if isinstance(expr, FunctionCall) and expr.name == "print":
                    return [PrintStmt(args=expr.args)]
                return [ExpressionStmt(expr=expr)] if expr else []
            elif expr_n.type == "update_expression":
                text = self._get_text(expr_n, code_bytes)
                var_name = text.replace("+", "").replace("-", "").strip()
                op = "+" if "++" in text else "-"
                return [Assignment(
                    target=Identifier(name=var_name),
                    value=BinaryOp(left=Identifier(name=var_name), op=op, right=Literal(1))
                )]
            return []

        elif ntype == "if_statement":
            cond_n = node.child_by_field_name("condition")
            consequence_n = node.child_by_field_name("consequence")
            alternative_n = node.child_by_field_name("alternative")

            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            then_body = self._parse_block_or_stmt(consequence_n, code_bytes)
            else_body = self._parse_block_or_stmt(alternative_n, code_bytes) if alternative_n else []
            return [IfStmt(condition=cond, then_branch=then_body, else_branch=else_body)]

        elif ntype == "while_statement":
            cond_n = node.child_by_field_name("condition")
            body_n = node.child_by_field_name("body")
            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            body = self._parse_block_or_stmt(body_n, code_bytes)
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
        if node.type == "block":
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["{", "}"]:
                    stmts.extend(self._parse_statement(c, code_bytes))
            return stmts
        return self._parse_statement(node, code_bytes)

    def _parse_for(self, node: Node, code_bytes: bytes) -> List[Statement]:
        init_n = node.child_by_field_name("init")
        cond_n = node.child_by_field_name("condition")
        body_n = node.child_by_field_name("body")

        var_name = "i"
        start_expr: Expression = Literal(0)
        end_expr: Expression = Literal(0)

        if init_n:
            if init_n.type == "local_variable_declaration":
                for d in init_n.children:
                    if d.type == "variable_declarator":
                        name_n = d.child_by_field_name("name")
                        val_n = d.child_by_field_name("value")
                        if name_n:
                            var_name = self._get_text(name_n, code_bytes)
                        if val_n:
                            start_expr = self._parse_expression(val_n, code_bytes) or Literal(0)

        if cond_n and cond_n.type == "binary_expression":
            right_n = cond_n.child_by_field_name("right")
            if right_n:
                end_expr = self._parse_expression(right_n, code_bytes) or Literal(0)

        body = self._parse_block_or_stmt(body_n, code_bytes)
        return [ForRangeStmt(var_name=var_name, start=start_expr, end=end_expr, step=None, body=body)]

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype in ["decimal_integer_literal", "hex_integer_literal"]:
            text = self._get_text(node, code_bytes).replace("_", "").rstrip("lL")
            return Literal(int(text))
        elif ntype == "decimal_floating_point_literal":
            text = self._get_text(node, code_bytes).replace("_", "").rstrip("fFdD")
            return Literal(float(text))
        elif ntype == "string_literal":
            text = self._get_text(node, code_bytes)
            clean_str = text[1:-1] if len(text) >= 2 and text[0] == '"' else text
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

        elif ntype in ["array_initializer", "array_creation_expression"]:
            # {1, 2, 3} or new int[]{1, 2, 3}
            elements: List[Expression] = []
            for c in node.children:
                if c.type == "array_initializer":
                    for sc in c.children:
                        if sc.type not in ["{", "}", ","]:
                            elem = self._parse_expression(sc, code_bytes)
                            if elem:
                                elements.append(elem)
                    return ArrayLiteral(elements=elements)
                elif c.type not in ["{", "}", ",", "new", "int", "[", "]"]:
                    elem = self._parse_expression(c, code_bytes)
                    if elem:
                        elements.append(elem)
            return ArrayLiteral(elements=elements)

        elif ntype == "array_access":
            arr_n = node.child_by_field_name("array")
            idx_n = node.child_by_field_name("index")
            return ArrayAccess(
                array=self._parse_expression(arr_n, code_bytes),
                index=self._parse_expression(idx_n, code_bytes)
            )

        elif ntype == "field_access":
            # arr.length
            field_n = node.child_by_field_name("field")
            target_n = node.child_by_field_name("object")
            f_text = self._get_text(field_n, code_bytes) if field_n else ""
            if f_text == "length":
                return ArrayLength(array=self._parse_expression(target_n, code_bytes))
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "method_invocation":
            target_n = node.child_by_field_name("object")
            name_n = node.child_by_field_name("name")
            args_n = node.child_by_field_name("arguments")

            full_target = self._get_text(target_n, code_bytes) if target_n else ""
            method_name = self._get_text(name_n, code_bytes) if name_n else ""

            args: List[Expression] = []
            if args_n:
                for c in args_n.children:
                    if c.type not in ["(", ")", ","]:
                        a = self._parse_expression(c, code_bytes)
                        if a:
                            args.append(a)

            if "System.out.print" in full_target or full_target == "System.out":
                return FunctionCall(name="print", args=args)
            return FunctionCall(name=method_name, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        return None

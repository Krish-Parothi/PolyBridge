from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
        ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind, ImportStmt
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
        imports: List[ImportStmt] = []

        for child in root.children:
            if child.type == "function_definition":
                fn = self._parse_function(child, code_bytes)
                if fn:
                    functions.append(fn)
            elif child.type == "class_definition":
                body = child.child_by_field_name("body")
                if body:
                    for c in body.children:
                        if c.type == "function_definition":
                            fn = self._parse_function(c, code_bytes)
                            if fn:
                                fn.params = [p for p in fn.params if p.name != "self"]
                                functions.append(fn)
                        else:
                            stmts = self._parse_statement(c, code_bytes)
                            if stmts:
                                global_statements.extend(stmts)
            elif child.type in ["import_statement", "import_from_statement"]:
                imp = self._parse_import(child, code_bytes)
                if imp:
                    imports.append(imp)
            else:
                stmts = self._parse_statement(child, code_bytes)
                if stmts:
                    global_statements.extend(stmts)

        return Program(functions=functions, global_statements=global_statements, imports=imports)

    def _parse_import(self, node: Node, code_bytes: bytes) -> Optional[ImportStmt]:
        if node.type == "import_statement":
            for c in node.children:
                if c.type == "dotted_name":
                    return ImportStmt(module=self._get_text(c, code_bytes))
                elif c.type == "aliased_import":
                    name_n = c.child_by_field_name("name") or (c.children[0] if len(c.children) > 0 else None)
                    alias_n = c.child_by_field_name("alias") or (c.children[2] if len(c.children) > 2 else None)
                    mod_name = self._get_text(name_n, code_bytes) if name_n else ""
                    alias_name = self._get_text(alias_n, code_bytes) if alias_n else None
                    return ImportStmt(module=mod_name, alias=alias_name)
        elif node.type == "import_from_statement":
            mod_name = ""
            for c in node.children:
                if c.type == "dotted_name":
                    mod_name = self._get_text(c, code_bytes)
                    break
            items = []
            after_import = False
            for c in node.children:
                if c.type == "import":
                    after_import = True
                    continue
                if after_import and c.type in ["dotted_name", "identifier"]:
                    items.append(self._get_text(c, code_bytes))
            return ImportStmt(module=mod_name, imported_names=items)
        return None

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
                elif p.type in ["typed_parameter", "default_parameter", "typed_default_parameter"]:
                    id_node = None
                    for c in p.children:
                        if c.type == "identifier":
                            id_node = c
                            break
                    if id_node:
                        type_node = p.child_by_field_name("type")
                        ptype = IRType.unknown()
                        if type_node:
                            t_text = self._get_text(type_node, code_bytes).strip()
                            if t_text == "int":
                                ptype = IRType.int_type()
                            elif t_text == "float":
                                ptype = IRType.float_type()
                            elif t_text == "str":
                                ptype = IRType.string_type()
                            elif t_text == "bool":
                                ptype = IRType.bool_type()
                            elif "list[list[" in t_text or "[][]" in t_text:
                                ptype = IRType(TypeKind.ARRAY, element_type=IRType.array_of(IRType.int_type()))
                            elif "list" in t_text or "[]" in t_text:
                                ptype = IRType.array_of(IRType.int_type())
                        params.append(Parameter(name=self._get_text(id_node, code_bytes), param_type=ptype))

        ret_type = IRType.unknown()
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            t_text = self._get_text(ret_node, code_bytes).strip()
            if t_text == "int":
                ret_type = IRType.int_type()
            elif t_text == "float":
                ret_type = IRType.float_type()
            elif t_text == "str":
                ret_type = IRType.string_type()
            elif t_text == "bool":
                ret_type = IRType.bool_type()
            elif "list[list[" in t_text or "[][]" in t_text:
                ret_type = IRType(TypeKind.ARRAY, element_type=IRType.array_of(IRType.int_type()))
            elif "list" in t_text or "[]" in t_text:
                ret_type = IRType.array_of(IRType.int_type())

        body_stmts: List[Statement] = []
        for child in body_node.children:
            stmts = self._parse_statement(child, code_bytes)
            if stmts:
                body_stmts.extend(stmts)

        return FunctionDef(
            name=func_name,
            params=params,
            return_type=ret_type,
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

        elif ntype == "break_statement":
            return [BreakStmt()]

        elif ntype == "continue_statement":
            return [ContinueStmt()]

        elif ntype == "block":
            stmts: List[Statement] = []
            for c in node.children:
                s = self._parse_statement(c, code_bytes)
                if s:
                    stmts.extend(s)
            return stmts

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

        cond = self._parse_expression(cond_node, code_bytes) if cond_node else Literal(True)
        then_branch: List[Statement] = []
        if consequence_node:
            for c in consequence_node.children:
                s = self._parse_statement(c, code_bytes)
                if s:
                    then_branch.extend(s)

        else_branch: List[Statement] = []
        clauses = [c for c in node.children if c.type in ["elif_clause", "else_clause"]]
        if clauses:
            else_branch = self._parse_clause_chain(clauses, code_bytes)

        return [IfStmt(condition=cond, then_branch=then_branch, else_branch=else_branch)]

    def _parse_clause_chain(self, clauses: List[Node], code_bytes: bytes) -> List[Statement]:
        if not clauses:
            return []
        first = clauses[0]
        rest = clauses[1:]
        if first.type == "else_clause":
            body = first.child_by_field_name("body")
            stmts: List[Statement] = []
            if body:
                for c in body.children:
                    s = self._parse_statement(c, code_bytes)
                    if s:
                        stmts.extend(s)
            return stmts
        elif first.type == "elif_clause":
            cond_node = first.child_by_field_name("condition") or (first.children[1] if len(first.children) > 1 else None)
            consequence_node = first.child_by_field_name("consequence")
            if not consequence_node:
                for c in first.children:
                    if c.type == "block":
                        consequence_node = c
                        break
            cond = self._parse_expression(cond_node, code_bytes) if cond_node else Literal(True)
            then_branch: List[Statement] = []
            if consequence_node:
                for c in consequence_node.children:
                    s = self._parse_statement(c, code_bytes)
                    if s:
                        then_branch.extend(s)
            nested_else = self._parse_clause_chain(rest, code_bytes)
            return [IfStmt(condition=cond, then_branch=then_branch, else_branch=nested_else)]
        return []

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
            if fn_node and fn_node.type == "attribute":
                attr_node = fn_node.child_by_field_name("attribute")
                obj_node = fn_node.child_by_field_name("object")
                obj_text = self._get_text(obj_node, code_bytes) if obj_node else ""
                if attr_node and (obj_text in ["self", "this", "sol", "solution", "Solution"] or obj_text.startswith("Solution(")):
                    fn_name = self._get_text(attr_node, code_bytes)

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

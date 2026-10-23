from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_python as tspython

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt, ForEachStmt,
        ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind, ImportStmt, AugmentedAssignment,
        TernaryOp, CastExpr, MethodCall
    )

CAST_FUNCTIONS = {"int", "float", "str", "bool"}

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
                            ptype = self._parse_type_annotation(t_text)
                        params.append(Parameter(name=self._get_text(id_node, code_bytes), param_type=ptype))

        ret_type = IRType.unknown()
        ret_node = node.child_by_field_name("return_type")
        if ret_node:
            t_text = self._get_text(ret_node, code_bytes).strip()
            ret_type = self._parse_type_annotation(t_text)

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

    def _parse_type_annotation(self, t_text: str) -> IRType:
        t_text = t_text.strip()
        if t_text == "int":
            return IRType.int_type()
        elif t_text == "float":
            return IRType.float_type()
        elif t_text == "str":
            return IRType.string_type()
        elif t_text == "bool":
            return IRType.bool_type()
        elif t_text == "None":
            return IRType.void_type()
        elif "list[list[" in t_text.lower() or "[][]" in t_text:
            return IRType(TypeKind.ARRAY, element_type=IRType.array_of(IRType.int_type()))
        elif "list[str" in t_text.lower():
            return IRType.array_of(IRType.string_type())
        elif "list[float" in t_text.lower():
            return IRType.array_of(IRType.float_type())
        elif "list[bool" in t_text.lower():
            return IRType.array_of(IRType.bool_type())
        elif "list" in t_text.lower() or "[]" in t_text:
            return IRType.array_of(IRType.int_type())
        return IRType.unknown()

    def _parse_statement(self, node: Node, code_bytes: bytes) -> List[Statement]:
        ntype = node.type

        if ntype == "expression_statement":
            first_child = node.children[0] if node.children else None
            if not first_child:
                return []
            if first_child.type == "assignment":
                return self._parse_assignment(first_child, code_bytes)
            elif first_child.type == "augmented_assignment":
                return self._parse_augmented_assignment(first_child, code_bytes)
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

        elif ntype == "pass_statement":
            return []

        return []

    def _parse_augmented_assignment(self, node: Node, code_bytes: bytes) -> List[Statement]:
        left_node = node.child_by_field_name("left")
        right_node = node.child_by_field_name("right")

        if not left_node or not right_node:
            return []

        target = self._parse_expression(left_node, code_bytes)
        value = self._parse_expression(right_node, code_bytes)

        # Extract operator from the node
        op = ""
        for c in node.children:
            t = self._get_text(c, code_bytes).strip()
            if t in ["+=", "-=", "*=", "/=", "%=", "**=", "//=", "&=", "|=", "^=", "<<=", ">>="]:
                op = t
                break

        if op:
            return [AugmentedAssignment(target=target, op=op, value=value)]

        # Fallback: expand to target = target op value
        return [Assignment(target=target, value=value)]

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

        body: List[Statement] = []
        if body_node:
            for c in body_node.children:
                s = self._parse_statement(c, code_bytes)
                if s:
                    body.extend(s)

        # Check if right side is range()
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

                start_expr: Expression = Literal(0)
                end_expr: Expression = Literal(0)
                step_expr: Optional[Expression] = None

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

                return [ForRangeStmt(
                    var_name=var_name,
                    start=start_expr,
                    end=end_expr,
                    step=step_expr,
                    body=body
                )]
            elif fn_name == "enumerate":
                # for i, x in enumerate(arr) -> ForRangeStmt over len(arr) with arr[i] access
                # Simplified: treat as for-each with index
                args_node = right_node.child_by_field_name("arguments")
                args = []
                if args_node:
                    for a in args_node.children:
                        if a.type not in ["(", ")", ","]:
                            args.append(self._parse_expression(a, code_bytes))
                if args:
                    iterable_expr = args[0]
                    # If var_name is "i, x" style tuple, parse both
                    if left_node and left_node.type == "pattern_list":
                        parts = [self._get_text(c, code_bytes) for c in left_node.children if c.type not in [",", "(", ")"]]
                        if len(parts) == 2:
                            idx_name, elem_name = parts[0], parts[1]
                            # Emit as for idx_name in range(len(iterable))
                            # with elem_name = iterable[idx_name] at the start of body
                            body.insert(0, Assignment(
                                target=Identifier(name=elem_name),
                                value=ArrayAccess(array=iterable_expr, index=Identifier(name=idx_name))
                            ))
                            return [ForRangeStmt(
                                var_name=idx_name,
                                start=Literal(0),
                                end=ArrayLength(array=iterable_expr),
                                step=None,
                                body=body
                            )]
                    # Fallback: single variable enumerate
                    return [ForRangeStmt(
                        var_name=var_name,
                        start=Literal(0),
                        end=ArrayLength(array=iterable_expr),
                        step=None,
                        body=body
                    )]

        # Not range() -> for-each over iterable
        if right_node:
            iterable_expr = self._parse_expression(right_node, code_bytes)
            if iterable_expr:
                return [ForEachStmt(
                    var_name=var_name,
                    iterable=iterable_expr,
                    body=body
                )]

        # Fallback
        return [ForRangeStmt(
            var_name=var_name,
            start=Literal(0),
            end=Literal(0),
            step=None,
            body=body
        )]

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype == "integer":
            text = self._get_text(node, code_bytes)
            try:
                return Literal(int(text, 0))  # Support 0x, 0o, 0b prefixes
            except ValueError:
                return Literal(int(text))
        elif ntype == "float":
            text = self._get_text(node, code_bytes)
            return Literal(float(text))
        elif ntype == "string":
            text = self._get_text(node, code_bytes)
            # Handle f-strings, triple quotes, etc.
            if text.startswith('f"') or text.startswith("f'"):
                text = text[1:]
            if text.startswith('"""') or text.startswith("'''"):
                clean_str = text[3:-3]
            elif len(text) >= 2 and text[0] in ['"', "'"]:
                clean_str = text[1:-1]
            else:
                clean_str = text
            return Literal(clean_str)
        elif ntype == "concatenated_string":
            # Handle "hello" " world" concatenation
            parts = []
            for c in node.children:
                if c.type == "string":
                    text = self._get_text(c, code_bytes)
                    if len(text) >= 2 and text[0] in ['"', "'"]:
                        parts.append(text[1:-1])
                    else:
                        parts.append(text)
            return Literal("".join(parts))
        elif ntype == "true":
            return Literal(True)
        elif ntype == "false":
            return Literal(False)
        elif ntype == "none":
            return Literal(None)
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
            elif op_norm == "**":
                # Convert power operator to function call
                left = self._parse_expression(left_node, code_bytes)
                right = self._parse_expression(right_node, code_bytes)
                return FunctionCall(name="pow", args=[left, right])
            elif op_norm == "in":
                # x in arr -> array contains check - emit as function call
                left = self._parse_expression(left_node, code_bytes)
                right = self._parse_expression(right_node, code_bytes)
                return FunctionCall(name="__contains__", args=[right, left])
            elif op_norm == "not" and ntype == "comparison_operator":
                # "not in" operator
                # Check if there's a "not" followed by "in"
                ops = [self._get_text(c, code_bytes).strip() for c in node.children if c != left_node and c != right_node]
                if "not" in ops and "in" in ops:
                    left = self._parse_expression(left_node, code_bytes)
                    right = self._parse_expression(right_node, code_bytes)
                    return UnaryOp(op="!", operand=FunctionCall(name="__contains__", args=[right, left]))

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

        elif ntype == "tuple":
            # Treat tuples as arrays for transpilation
            elements: List[Expression] = []
            for c in node.children:
                if c.type not in ["(", ")", ","]:
                    elem = self._parse_expression(c, code_bytes)
                    if elem:
                        elements.append(elem)
            return ArrayLiteral(elements=elements)

        elif ntype == "dictionary":
            # Not fully supported in procedural scope, but don't crash
            return Literal("<dict>")

        elif ntype == "subscript":
            val_node = node.child_by_field_name("value")
            sub_node = node.child_by_field_name("subscript")
            array_expr = self._parse_expression(val_node, code_bytes)
            idx_expr = self._parse_expression(sub_node, code_bytes)
            return ArrayAccess(array=array_expr, index=idx_expr)

        elif ntype == "call":
            fn_node = node.child_by_field_name("function")
            fn_name = self._get_text(fn_node, code_bytes) if fn_node else ""

            # Handle attribute calls like self.method(), obj.method()
            if fn_node and fn_node.type == "attribute":
                attr_node = fn_node.child_by_field_name("attribute")
                obj_node = fn_node.child_by_field_name("object")
                obj_text = self._get_text(obj_node, code_bytes) if obj_node else ""

                # self.method() or Solution().method() -> treat as plain function call
                if attr_node and (obj_text in ["self", "this", "sol", "solution", "Solution"] or obj_text.startswith("Solution(")):
                    fn_name = self._get_text(attr_node, code_bytes)
                else:
                    method_name = self._get_text(attr_node, code_bytes) if attr_node else ""
                    fn_name = f"{obj_text}.{method_name}"

            args_node = node.child_by_field_name("arguments")
            args: List[Expression] = []
            if args_node:
                for c in args_node.children:
                    if c.type not in ["(", ")", ",", "**"]:
                        # Skip keyword arguments
                        if c.type == "keyword_argument":
                            continue
                        a = self._parse_expression(c, code_bytes)
                        if a:
                            args.append(a)

            # Type cast functions
            if fn_name in CAST_FUNCTIONS and len(args) == 1:
                target_type = {
                    "int": IRType.int_type(),
                    "float": IRType.float_type(),
                    "str": IRType.string_type(),
                    "bool": IRType.bool_type()
                }[fn_name]
                return CastExpr(target_type=target_type, operand=args[0])

            if fn_name == "len" and len(args) == 1:
                return ArrayLength(array=args[0])
            elif fn_name == "print":
                return FunctionCall(name="print", args=args)
            elif fn_name == "input":
                return FunctionCall(name="input", args=args)
            elif fn_name == "type":
                return FunctionCall(name="type", args=args)
            elif fn_name == "max" and len(args) >= 2:
                return FunctionCall(name="max", args=args)
            elif fn_name == "min" and len(args) >= 2:
                return FunctionCall(name="min", args=args)
            elif fn_name == "sorted":
                return FunctionCall(name="sorted", args=args)
            elif fn_name == "reversed":
                return FunctionCall(name="reversed", args=args)
            elif fn_name == "list":
                return FunctionCall(name="list", args=args)
            elif fn_name == "sum":
                return FunctionCall(name="sum", args=args)
            elif fn_name == "map":
                return FunctionCall(name="map", args=args)
            elif fn_name == "filter":
                return FunctionCall(name="filter", args=args)
            elif fn_name == "zip":
                return FunctionCall(name="zip", args=args)
            else:
                return FunctionCall(name=fn_name, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        elif ntype == "conditional_expression":
            # Python ternary: value_if_true if condition else value_if_false
            body_node = node.child_by_field_name("body") or (node.children[0] if node.children else None)
            condition_node = None
            else_node = None
            # Find the condition (after 'if') and alternative (after 'else')
            saw_if = False
            saw_else = False
            for c in node.children:
                t = self._get_text(c, code_bytes).strip()
                if t == "if":
                    saw_if = True
                    continue
                if t == "else":
                    saw_else = True
                    continue
                if saw_else and else_node is None:
                    else_node = c
                elif saw_if and condition_node is None:
                    condition_node = c

            cond = self._parse_expression(condition_node, code_bytes) if condition_node else Literal(True)
            then_e = self._parse_expression(body_node, code_bytes) if body_node else Literal(None)
            else_e = self._parse_expression(else_node, code_bytes) if else_node else Literal(None)
            return TernaryOp(condition=cond, then_expr=then_e, else_expr=else_e)

        elif ntype == "attribute":
            obj_node = node.child_by_field_name("object")
            attr_node = node.child_by_field_name("attribute")
            obj_text = self._get_text(obj_node, code_bytes) if obj_node else ""
            attr_text = self._get_text(attr_node, code_bytes) if attr_node else ""
            return Identifier(name=f"{obj_text}.{attr_text}")

        elif ntype == "list_comprehension":
            # List comprehensions are complex; convert to a simplified form
            # For now, return as a function call placeholder
            return FunctionCall(name="__list_comp__", args=[])

        elif ntype == "lambda":
            # Lambda expressions - convert to a placeholder
            return FunctionCall(name="__lambda__", args=[])

        elif ntype == "slice":
            # arr[start:end:step] - for now treat as function call
            children_exprs = []
            for c in node.children:
                if c.type not in [":", ","]:
                    e = self._parse_expression(c, code_bytes)
                    if e:
                        children_exprs.append(e)
            return FunctionCall(name="__slice__", args=children_exprs)

        return None

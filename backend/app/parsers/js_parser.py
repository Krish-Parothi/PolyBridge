from typing import List, Optional, Any
from tree_sitter import Language, Parser, Node
import tree_sitter_javascript as tsjavascript

from app.ir.nodes import (
        Program, FunctionDef, Parameter, Statement, Expression,
        VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt, ForEachStmt,
        ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt, Literal, Identifier,
        BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess, ArrayLength,
        FunctionCall, IRType, TypeKind, ImportStmt, AugmentedAssignment,
        TernaryOp, CastExpr, MethodCall, DoWhileStmt
)
from app.parsers.diagnostics import attach_tree_diagnostics

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
        imports: List[ImportStmt] = []

        for child in root.children:
            if child.type == "function_declaration":
                fn = self._parse_function(child, code_bytes)
                if fn:
                    functions.append(fn)
            elif child.type == "import_statement":
                imp = self._parse_import(child, code_bytes)
                if imp:
                    imports.append(imp)
            else:
                stmts = self._parse_statement(child, code_bytes)
                if stmts:
                    global_statements.extend(stmts)

        return attach_tree_diagnostics(
            Program(functions=functions, global_statements=global_statements, imports=imports),
            root,
            code_bytes,
        )

    def _parse_import(self, node: Node, code_bytes: bytes) -> Optional[ImportStmt]:
        source_n = node.child_by_field_name("source")
        if source_n:
            mod_text = self._get_text(source_n, code_bytes).strip("'\"")
            return ImportStmt(module=mod_text)
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
                elif p.type == "assignment_pattern":
                    # Default parameter: name = value
                    name_n = p.child_by_field_name("left")
                    if name_n:
                        params.append(Parameter(name=self._get_text(name_n, code_bytes), param_type=IRType.unknown()))

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
            elif first_child.type == "augmented_assignment_expression":
                left_n = first_child.child_by_field_name("left")
                right_n = first_child.child_by_field_name("right")
                op_n = first_child.child_by_field_name("operator")
                target = self._parse_expression(left_n, code_bytes)
                value = self._parse_expression(right_n, code_bytes)
                op = self._get_text(op_n, code_bytes) if op_n else "+="
                return [AugmentedAssignment(target=target, op=op, value=value)]
            elif first_child.type == "call_expression":
                expr = self._parse_expression(first_child, code_bytes)
                if isinstance(expr, FunctionCall) and expr.name == "print":
                    return [PrintStmt(args=expr.args)]
                return [ExpressionStmt(expr=expr)] if expr else []
            elif first_child.type == "update_expression":
                # e.g., i++ or i--
                text = self._get_text(first_child, code_bytes)
                var_name = text.replace("+", "").replace("-", "").strip()
                op = "+=" if "++" in text else "-="
                return [AugmentedAssignment(
                    target=Identifier(name=var_name),
                    op=op,
                    value=Literal(1)
                )]
            else:
                expr = self._parse_expression(first_child, code_bytes)
                return [ExpressionStmt(expr=expr)] if expr else []

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

        elif ntype == "do_statement":
            body_n = node.child_by_field_name("body")
            cond_n = node.child_by_field_name("condition")
            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            body: List[Statement] = []
            if body_n:
                for c in body_n.children:
                    body.extend(self._parse_statement(c, code_bytes))
            return [DoWhileStmt(condition=cond, body=body)]

        elif ntype == "for_statement":
            return self._parse_for(node, code_bytes)

        elif ntype == "for_in_statement":
            return self._parse_for_in(node, code_bytes)

        elif ntype == "return_statement":
            val = None
            for c in node.children:
                if c.type not in ["return", ";"]:
                    val = self._parse_expression(c, code_bytes)
                    break
            return [ReturnStmt(value=val)]

        elif ntype == "break_statement":
            return [BreakStmt()]

        elif ntype == "continue_statement":
            return [ContinueStmt()]

        elif ntype == "statement_block":
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["{", "}"]:
                    stmts.extend(self._parse_statement(c, code_bytes))
            return stmts

        elif ntype == "switch_statement":
            return self._parse_switch(node, code_bytes)

        elif ntype == "empty_statement":
            return []

        return []

    def _parse_switch(self, node: Node, code_bytes: bytes) -> List[Statement]:
        """Convert switch to if-else chain."""
        val_n = node.child_by_field_name("value")
        body_n = node.child_by_field_name("body")
        val_expr = self._parse_expression(val_n, code_bytes) if val_n else Identifier(name="__switch__")

        if not body_n:
            return []

        cases = []
        default_body = []
        for c in body_n.children:
            if c.type == "switch_case":
                val_case_n = c.child_by_field_name("value")
                case_val = self._parse_expression(val_case_n, code_bytes) if val_case_n else None
                case_body: List[Statement] = []
                for sc in c.children:
                    if sc.type not in ["case", ":", ";"]:
                        if sc != val_case_n:
                            stmts = self._parse_statement(sc, code_bytes)
                            case_body.extend(stmts)
                # Remove trailing break
                case_body = [s for s in case_body if not isinstance(s, BreakStmt)]
                cases.append((case_val, case_body))
            elif c.type == "switch_default":
                for sc in c.children:
                    if sc.type not in ["default", ":", ";"]:
                        stmts = self._parse_statement(sc, code_bytes)
                        default_body.extend(stmts)
                default_body = [s for s in default_body if not isinstance(s, BreakStmt)]

        # Build if-else chain
        if not cases:
            return default_body

        result = None
        for i in range(len(cases) - 1, -1, -1):
            case_val, case_body = cases[i]
            if case_val:
                cond = BinaryOp(left=val_expr, op="==", right=case_val)
            else:
                cond = Literal(True)
            else_branch = [result] if result else default_body
            result = IfStmt(condition=cond, then_branch=case_body, else_branch=else_branch)

        return [result] if result else default_body

    def _parse_for(self, node: Node, code_bytes: bytes) -> List[Statement]:
        init_n = node.child_by_field_name("initializer")
        cond_n = node.child_by_field_name("condition")
        update_n = node.child_by_field_name("increment")
        body_n = node.child_by_field_name("body")

        var_name = "i"
        start_expr: Expression = Literal(0)
        end_expr: Expression = Literal(0)
        step_expr: Optional[Expression] = None

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

        # Inspect update: i++, i += 2, etc.
        if update_n:
            if update_n.type == "update_expression":
                text = self._get_text(update_n, code_bytes)
                if "--" in text:
                    step_expr = Literal(-1)
            elif update_n.type == "augmented_assignment_expression":
                right_n = update_n.child_by_field_name("right")
                op_n = update_n.child_by_field_name("operator")
                op = self._get_text(op_n, code_bytes) if op_n else "+="
                val = self._parse_expression(right_n, code_bytes) if right_n else Literal(1)
                if op == "-=":
                    if isinstance(val, Literal) and isinstance(val.value, int):
                        step_expr = Literal(-val.value)
                    else:
                        step_expr = UnaryOp(op="-", operand=val)
                elif op == "+=" and not (isinstance(val, Literal) and val.value == 1):
                    step_expr = val

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
            step=step_expr,
            body=body
        )]

    def _parse_for_in(self, node: Node, code_bytes: bytes) -> List[Statement]:
        """Parse for...in or for...of statements."""
        left_n = node.child_by_field_name("left")
        right_n = node.child_by_field_name("right")
        body_n = node.child_by_field_name("body")

        var_name = "item"
        if left_n:
            # Handle 'let x', 'const x', or just 'x'
            if left_n.type in ["lexical_declaration", "variable_declaration"]:
                for d in left_n.children:
                    if d.type == "variable_declarator":
                        name_n = d.child_by_field_name("name")
                        if name_n:
                            var_name = self._get_text(name_n, code_bytes)
                    elif d.type == "identifier":
                        var_name = self._get_text(d, code_bytes)
            elif left_n.type == "identifier":
                var_name = self._get_text(left_n, code_bytes)

        iterable = self._parse_expression(right_n, code_bytes) if right_n else Identifier(name="[]")

        body: List[Statement] = []
        if body_n:
            if body_n.type == "statement_block":
                for c in body_n.children:
                    if c.type not in ["{", "}"]:
                        body.extend(self._parse_statement(c, code_bytes))
            else:
                body.extend(self._parse_statement(body_n, code_bytes))

        return [ForEachStmt(var_name=var_name, iterable=iterable, body=body)]

    def _parse_expression(self, node: Node, code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None

        ntype = node.type

        if ntype == "number":
            text = self._get_text(node, code_bytes)
            if "." in text:
                return Literal(float(text))
            try:
                return Literal(int(text, 0))
            except ValueError:
                return Literal(int(text))

        elif ntype == "string":
            text = self._get_text(node, code_bytes)
            clean_str = text[1:-1] if len(text) >= 2 and text[0] in ['"', "'", '`'] else text
            return Literal(clean_str)

        elif ntype == "template_string":
            text = self._get_text(node, code_bytes)
            # Simple template string handling - strip backticks
            clean_str = text[1:-1] if len(text) >= 2 else text
            return Literal(clean_str)

        elif ntype == "true":
            return Literal(True)

        elif ntype == "false":
            return Literal(False)

        elif ntype == "null" or ntype == "undefined":
            return Literal(None)

        elif ntype == "identifier":
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "binary_expression":
            left_n = node.child_by_field_name("left")
            op_n = node.child_by_field_name("operator")
            right_n = node.child_by_field_name("right")
            op_text = self._get_text(op_n, code_bytes) if op_n else ""
            left = self._parse_expression(left_n, code_bytes)
            right = self._parse_expression(right_n, code_bytes)

            # Convert ** to pow
            if op_text == "**":
                return FunctionCall(name="pow", args=[left, right])

            return BinaryOp(left=left, op=op_text, right=right)

        elif ntype == "unary_expression":
            op_n = node.child_by_field_name("operator")
            arg_n = node.child_by_field_name("argument")
            op_text = self._get_text(op_n, code_bytes) if op_n else ""
            arg = self._parse_expression(arg_n, code_bytes)
            return UnaryOp(op=op_text, operand=arg)

        elif ntype == "update_expression":
            text = self._get_text(node, code_bytes)
            var_name = text.replace("+", "").replace("-", "").strip()
            return Identifier(name=var_name)

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
            # Check for arr.length, obj.method
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

            # Type cast functions
            if fn_text == "parseInt" and len(args) >= 1:
                return CastExpr(target_type=IRType.int_type(), operand=args[0])
            elif fn_text == "parseFloat" and len(args) >= 1:
                return CastExpr(target_type=IRType.float_type(), operand=args[0])
            elif fn_text == "String" and len(args) == 1:
                return CastExpr(target_type=IRType.string_type(), operand=args[0])
            elif fn_text == "Number" and len(args) == 1:
                return CastExpr(target_type=IRType.float_type(), operand=args[0])
            elif fn_text == "Boolean" and len(args) == 1:
                return CastExpr(target_type=IRType.bool_type(), operand=args[0])

            # Handle method calls on objects
            if fn_n and fn_n.type == "member_expression":
                obj_n = fn_n.child_by_field_name("object")
                prop_n = fn_n.child_by_field_name("property")
                obj_text = self._get_text(obj_n, code_bytes) if obj_n else ""
                method_name = self._get_text(prop_n, code_bytes) if prop_n else ""
                fn_text = f"{obj_text}.{method_name}"

            if fn_text == "console.log":
                return FunctionCall(name="print", args=args)
            elif fn_text == "Math.pow" and len(args) == 2:
                return FunctionCall(name="pow", args=args)
            elif fn_text == "Math.max" and len(args) >= 2:
                return FunctionCall(name="max", args=args)
            elif fn_text == "Math.min" and len(args) >= 2:
                return FunctionCall(name="min", args=args)
            return FunctionCall(name=fn_text, args=args)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        elif ntype == "ternary_expression":
            cond_n = node.child_by_field_name("condition")
            then_n = node.child_by_field_name("consequence")
            else_n = node.child_by_field_name("alternative")
            cond = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(True)
            then_e = self._parse_expression(then_n, code_bytes) if then_n else Literal(None)
            else_e = self._parse_expression(else_n, code_bytes) if else_n else Literal(None)
            return TernaryOp(condition=cond, then_expr=then_e, else_expr=else_e)

        elif ntype == "arrow_function":
            # Arrow functions: treat as inline function reference
            params_n = node.child_by_field_name("parameters") or node.child_by_field_name("parameter")
            body_n = node.child_by_field_name("body")
            # For simple arrow functions used in callbacks, return as function placeholder
            return FunctionCall(name="__arrow__", args=[])

        elif ntype == "object":
            # Object literal - placeholder
            return Literal("<object>")

        elif ntype == "spread_element":
            # ...arr
            if node.children:
                for c in node.children:
                    if c.type != "...":
                        return self._parse_expression(c, code_bytes)
            return None

        elif ntype == "sequence_expression":
            # Comma expression: a, b -> return last
            last_expr = None
            for c in node.children:
                if c.type != ",":
                    last_expr = self._parse_expression(c, code_bytes)
            return last_expr

        return None

from typing import List, Optional, Any, Union
from tree_sitter import Language, Parser, Node
import tree_sitter_cpp as tscpp

from app.ir.nodes import (
    Program, FunctionDef, Parameter, Statement, Expression,
    VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
    ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, IRType, TypeKind, ImportStmt, ForEachStmt
)
from app.parsers.diagnostics import attach_tree_diagnostics

class CppParser:
    """Parses C++20 code into PolyBridge Universal IR."""

    def __init__(self):
        self.language = Language(tscpp.language())
        self.parser = Parser(self.language)

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []
        imports: List[ImportStmt] = []

        for child in root.children:
            if child.type == "preproc_include":
                imp = self._parse_include(child, code_bytes)
                if imp:
                    imports.append(imp)
            elif child.type == "function_definition":
                decl_n = child.child_by_field_name("declarator")
                fn_name = self._extract_function_name(decl_n, code_bytes)
                if fn_name == "main":
                    body_n = child.child_by_field_name("body")
                    if body_n:
                        for s in body_n.children:
                            if s.type not in ["{", "}"]:
                                parsed_s = self._parse_statement(s, code_bytes)
                                if parsed_s:
                                    # Filter out return 0; in main
                                    for stmt in parsed_s:
                                        if isinstance(stmt, ReturnStmt) and isinstance(stmt.value, Literal) and stmt.value.value == 0:
                                            continue
                                        global_statements.append(stmt)
                elif fn_name == "floorDiv":
                    # Skip generated helper function from previous emitter
                    continue
                else:
                    fn = self._parse_function(child, code_bytes)
                    if fn:
                        functions.append(fn)

        return attach_tree_diagnostics(
            Program(functions=functions, global_statements=global_statements, imports=imports),
            root,
            code_bytes,
        )

    def _get_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _parse_include(self, node: Node, code_bytes: bytes) -> Optional[ImportStmt]:
        path_n = node.child_by_field_name("path")
        if path_n:
            path_text = self._get_text(path_n, code_bytes).strip("<>\"")
            return ImportStmt(module=path_text)
        return None

    def _extract_function_name(self, declarator_node: Optional[Node], code_bytes: bytes) -> str:
        if not declarator_node:
            return ""
        if declarator_node.type == "identifier":
            return self._get_text(declarator_node, code_bytes)
        if declarator_node.type == "function_declarator":
            inner = declarator_node.child_by_field_name("declarator")
            return self._extract_function_name(inner, code_bytes)
        for c in declarator_node.children:
            if c.type == "identifier":
                return self._get_text(c, code_bytes)
        return ""

    def _parse_type(self, type_text: str) -> IRType:
        type_text = type_text.strip()
        if "vector<" in type_text:
            inner_start = type_text.find("<") + 1
            inner_end = type_text.rfind(">")
            if inner_end > inner_start:
                sub_type = self._parse_type(type_text[inner_start:inner_end])
                return IRType.array_of(sub_type)
        if type_text.endswith("[]"):
            sub_type = self._parse_type(type_text[:-2])
            return IRType.array_of(sub_type)
        if type_text in ["int", "long", "short", "int32_t", "int64_t", "size_t", "uint32_t"]:
            return IRType.int_type()
        if type_text in ["float", "double"]:
            return IRType.float_type()
        if type_text in ["string", "std::string", "char*"]:
            return IRType.string_type()
        if type_text in ["bool"]:
            return IRType.bool_type()
        if type_text == "void":
            return IRType.void_type()
        return IRType.unknown()

    def _parse_function(self, node: Node, code_bytes: bytes) -> Optional[FunctionDef]:
        type_n = node.child_by_field_name("type")
        decl_n = node.child_by_field_name("declarator")
        body_n = node.child_by_field_name("body")

        if not decl_n or not body_n:
            return None

        func_name = self._extract_function_name(decl_n, code_bytes)
        ret_type = self._parse_type(self._get_text(type_n, code_bytes)) if type_n else IRType.unknown()

        # Extract parameters from declarator
        params: List[Parameter] = []
        param_list_n = None
        if decl_n.type == "function_declarator":
            param_list_n = decl_n.child_by_field_name("parameters")
        if not param_list_n:
            for c in decl_n.children:
                if c.type == "parameter_list":
                    param_list_n = c
                    break

        if param_list_n:
            for p in param_list_n.children:
                if p.type == "parameter_declaration":
                    p_type_n = p.child_by_field_name("type")
                    p_decl_n = p.child_by_field_name("declarator")
                    p_name = self._get_text(p_decl_n, code_bytes) if p_decl_n else ""
                    # Handle reference/pointer in name or type
                    p_name = p_name.lstrip("&* ")
                    p_type_str = self._get_text(p_type_n, code_bytes) if p_type_n else "int"
                    params.append(Parameter(name=p_name, param_type=self._parse_type(p_type_str)))

        body_stmts: List[Statement] = []
        for c in body_n.children:
            if c.type not in ["{", "}"]:
                parsed_s = self._parse_statement(c, code_bytes)
                if parsed_s:
                    body_stmts.extend(parsed_s)

        return FunctionDef(
            name=func_name,
            params=params,
            return_type=ret_type,
            body=body_stmts
        )

    def _parse_statement(self, node: Node, code_bytes: bytes) -> List[Statement]:
        ntype = node.type

        if ntype == "declaration":
            # Variable declaration
            type_n = node.child_by_field_name("type")
            var_type = self._parse_type(self._get_text(type_n, code_bytes)) if type_n else IRType.unknown()
            stmts: List[Statement] = []
            for c in node.children:
                if c.type == "init_declarator":
                    d_n = c.child_by_field_name("declarator")
                    v_n = c.child_by_field_name("value")
                    var_name = self._get_text(d_n, code_bytes) if d_n else ""
                    val_expr = self._parse_expression(v_n, code_bytes) if v_n else None
                    stmts.append(VarDecl(name=var_name, var_type=var_type, initializer=val_expr))
                elif c.type == "identifier":
                    var_name = self._get_text(c, code_bytes)
                    stmts.append(VarDecl(name=var_name, var_type=var_type, initializer=None))
            return stmts

        elif ntype == "expression_statement":
            expr_child = node.children[0] if node.children else None
            if not expr_child:
                return []
            # Check for std::cout << ... << std::endl
            cout_args = self._extract_cout_args(expr_child, code_bytes)
            if cout_args is not None:
                return [PrintStmt(args=cout_args)]

            # Check for assignment
            if expr_child.type == "assignment_expression":
                left_n = expr_child.child_by_field_name("left")
                op_n = expr_child.child_by_field_name("operator")
                right_n = expr_child.child_by_field_name("right")
                if left_n and right_n:
                    target_expr = self._parse_expression(left_n, code_bytes)
                    val_expr = self._parse_expression(right_n, code_bytes)
                    op_str = self._get_text(op_n, code_bytes) if op_n else "="
                    if op_str == "=":
                        return [Assignment(target=target_expr, value=val_expr)]
                    else:
                        base_op = op_str[:-1]  # += -> +
                        return [Assignment(target=target_expr, value=BinaryOp(left=target_expr, op=base_op, right=val_expr))]

            # Check for update expression (e.g. i++, ++i, i--, --i)
            if expr_child.type == "update_expression":
                arg_n = expr_child.child_by_field_name("argument")
                op_text = self._get_text(expr_child, code_bytes)
                if arg_n:
                    var_expr = self._parse_expression(arg_n, code_bytes)
                    op_sym = "+" if "++" in op_text else "-"
                    return [Assignment(target=var_expr, value=BinaryOp(left=var_expr, op=op_sym, right=Literal(value=1)))]

            parsed_expr = self._parse_expression(expr_child, code_bytes)
            if parsed_expr:
                return [ExpressionStmt(expr=parsed_expr)]
            return []

        elif ntype == "if_statement":
            cond_n = node.child_by_field_name("condition")
            then_n = node.child_by_field_name("consequence")
            else_n = node.child_by_field_name("alternative")

            # Extract condition expression (inside condition_clause or parentheses)
            cond_expr = None
            if cond_n:
                for c in cond_n.children:
                    if c.type not in ["(", ")"]:
                        cond_expr = self._parse_expression(c, code_bytes)
                        break
                if not cond_expr:
                    cond_expr = self._parse_expression(cond_n, code_bytes)

            then_stmts: List[Statement] = []
            if then_n:
                if then_n.type == "compound_statement":
                    for c in then_n.children:
                        if c.type not in ["{", "}"]:
                            s = self._parse_statement(c, code_bytes)
                            if s:
                                then_stmts.extend(s)
                else:
                    s = self._parse_statement(then_n, code_bytes)
                    if s:
                        then_stmts.extend(s)

            else_stmts: List[Statement] = []
            if else_n:
                # else_clause has child "else" and then the statement or compound_statement
                for c in else_n.children:
                    if c.type == "compound_statement":
                        for sc in c.children:
                            if sc.type not in ["{", "}"]:
                                s = self._parse_statement(sc, code_bytes)
                                if s:
                                    else_stmts.extend(s)
                    elif c.type not in ["else"]:
                        s = self._parse_statement(c, code_bytes)
                        if s:
                            else_stmts.extend(s)

            return [IfStmt(
                condition=cond_expr or Literal(value=True),
                then_branch=then_stmts,
                else_branch=else_stmts
            )]

        elif ntype == "while_statement":
            cond_n = node.child_by_field_name("condition")
            body_n = node.child_by_field_name("body")

            cond_expr = None
            if cond_n:
                for c in cond_n.children:
                    if c.type not in ["(", ")"]:
                        cond_expr = self._parse_expression(c, code_bytes)
                        break
                if not cond_expr:
                    cond_expr = self._parse_expression(cond_n, code_bytes)

            body_stmts: List[Statement] = []
            if body_n:
                if body_n.type == "compound_statement":
                    for c in body_n.children:
                        if c.type not in ["{", "}"]:
                            s = self._parse_statement(c, code_bytes)
                            if s:
                                body_stmts.extend(s)
                else:
                    s = self._parse_statement(body_n, code_bytes)
                    if s:
                        body_stmts.extend(s)

            return [WhileStmt(
                condition=cond_expr or Literal(value=True),
                body=body_stmts
            )]

        elif ntype == "for_range_loop":
            # C++ range-for: for (int item : iterable) { ... }
            decl_n = node.child_by_field_name("declarator")
            right_n = node.child_by_field_name("right")
            body_n = node.child_by_field_name("body")
            var_name = self._get_text(decl_n, code_bytes).strip() if decl_n else "item"
            iterable = self._parse_expression(right_n, code_bytes) if right_n else None
            body_stmts: List[Statement] = []
            if body_n:
                if body_n.type == "compound_statement":
                    for c in body_n.children:
                        if c.type not in ["{", "}"]:
                            body_stmts.extend(self._parse_statement(c, code_bytes))
                else:
                    body_stmts.extend(self._parse_statement(body_n, code_bytes))
            return [ForEachStmt(var_name=var_name, iterable=iterable, body=body_stmts)]

        elif ntype == "for_statement":
            # Check if canonical counting for loop: for (int i = 0; i < N; i++)
            init_n = node.child_by_field_name("initializer")
            cond_n = node.child_by_field_name("condition")
            update_n = node.child_by_field_name("update")
            body_n = node.child_by_field_name("body")

            body_stmts: List[Statement] = []
            if body_n:
                if body_n.type == "compound_statement":
                    for c in body_n.children:
                        if c.type not in ["{", "}"]:
                            s = self._parse_statement(c, code_bytes)
                            if s:
                                body_stmts.extend(s)
                else:
                    s = self._parse_statement(body_n, code_bytes)
                    if s:
                        body_stmts.extend(s)

            # Check if we can convert to ForRangeStmt
            range_info = self._detect_for_range(init_n, cond_n, update_n, code_bytes)
            if range_info:
                var_name, start_expr, stop_expr, step_expr = range_info
                return [ForRangeStmt(
                    var_name=var_name,
                    start=start_expr,
                    end=stop_expr,
                    step=step_expr,
                    body=body_stmts
                )]
            else:
                # Fallback to init statement + while loop
                stmts: List[Statement] = []
                if init_n:
                    s = self._parse_statement(init_n, code_bytes)
                    if s:
                        stmts.extend(s)
                cond_expr = self._parse_expression(cond_n, code_bytes) if cond_n else Literal(value=True)
                while_body = list(body_stmts)
                if update_n:
                    up_s = self._parse_statement(update_n, code_bytes)
                    if up_s:
                        while_body.extend(up_s)
                stmts.append(WhileStmt(condition=cond_expr, body=while_body))
                return stmts

        elif ntype == "return_statement":
            val_n = None
            for c in node.children:
                if c.type not in ["return", ";"]:
                    val_n = c
                    break
            val_expr = self._parse_expression(val_n, code_bytes) if val_n else None
            return [ReturnStmt(value=val_expr)]

        elif ntype == "break_statement":
            return [BreakStmt()]

        elif ntype == "continue_statement":
            return [ContinueStmt()]

        return []

    def _detect_for_range(self, init_n: Optional[Node], cond_n: Optional[Node], update_n: Optional[Node], code_bytes: bytes):
        if not init_n or not cond_n or not update_n:
            return None
        # Init: int i = 0 or i = 0
        var_name = None
        start_expr = None
        if init_n.type == "declaration":
            for c in init_n.children:
                if c.type == "init_declarator":
                    d_n = c.child_by_field_name("declarator")
                    v_n = c.child_by_field_name("value")
                    if d_n and v_n:
                        var_name = self._get_text(d_n, code_bytes)
                        start_expr = self._parse_expression(v_n, code_bytes)
        elif init_n.type == "assignment_expression":
            d_n = init_n.child_by_field_name("left")
            v_n = init_n.child_by_field_name("right")
            if d_n and v_n:
                var_name = self._get_text(d_n, code_bytes)
                start_expr = self._parse_expression(v_n, code_bytes)

        if not var_name or not start_expr:
            return None

        # Cond: i < N or i <= N
        stop_expr = None
        if cond_n.type == "binary_expression":
            l_n = cond_n.child_by_field_name("left")
            op_n = cond_n.child_by_field_name("operator")
            r_n = cond_n.child_by_field_name("right")
            if l_n and op_n and r_n and self._get_text(l_n, code_bytes) == var_name:
                op_str = self._get_text(op_n, code_bytes)
                if op_str == "<":
                    stop_expr = self._parse_expression(r_n, code_bytes)
                elif op_str == "<=":
                    raw_stop = self._parse_expression(r_n, code_bytes)
                    stop_expr = BinaryOp(left=raw_stop, op="+", right=Literal(value=1))

        if not stop_expr:
            return None

        # Update: i++ or i += 1 or ++i
        step_expr = Literal(value=1)
        up_text = self._get_text(update_n, code_bytes).strip()
        if up_text in [f"{var_name}++", f"++{var_name}"]:
            step_expr = Literal(value=1)
        elif up_text in [f"{var_name}--", f"--{var_name}"]:
            step_expr = Literal(value=-1)
        elif "+=" in up_text:
            parts = up_text.split("+=")
            if len(parts) == 2 and parts[0].strip() == var_name:
                try:
                    step_expr = Literal(value=int(parts[1].strip().rstrip(";")))
                except ValueError:
                    pass

        return var_name, start_expr, stop_expr, step_expr

    def _extract_cout_args(self, node: Node, code_bytes: bytes) -> Optional[List[Expression]]:
        """If node is a chained << binary expression starting with std::cout or cout, returns args."""
        if node.type != "binary_expression":
            return None

        chain: List[Node] = []
        curr = node
        while curr.type == "binary_expression":
            op = curr.child_by_field_name("operator")
            if op and self._get_text(op, code_bytes) == "<<":
                right = curr.child_by_field_name("right")
                if right:
                    chain.append(right)
                curr = curr.child_by_field_name("left")
            else:
                break

        # Base should be std::cout or cout
        base_text = self._get_text(curr, code_bytes).strip()
        if base_text not in ["std::cout", "cout"]:
            return None

        # Chain was appended in reverse (outermost right first)
        chain.reverse()
        args: List[Expression] = []
        for n in chain:
            txt = self._get_text(n, code_bytes).strip()
            # Skip endl, "\n", '\n'
            if txt in ["std::endl", "endl", '"\\n"', "'\\n'"]:
                continue
            parsed = self._parse_expression(n, code_bytes)
            if parsed:
                args.append(parsed)

        return args

    def _parse_expression(self, node: Optional[Node], code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None
        ntype = node.type

        if ntype == "number_literal":
            txt = self._get_text(node, code_bytes)
            try:
                if "." in txt or "e" in txt.lower():
                    return Literal(value=float(txt))
                return Literal(value=int(txt))
            except ValueError:
                return Literal(value=int(txt, 0))

        elif ntype in ["string_literal", "raw_string_literal"]:
            txt = self._get_text(node, code_bytes)
            return Literal(value=txt.strip('"'))

        elif ntype == "char_literal":
            txt = self._get_text(node, code_bytes)
            return Literal(value=txt.strip("'"))

        elif ntype == "true":
            return Literal(value=True)

        elif ntype == "false":
            return Literal(value=False)

        elif ntype in ["identifier", "type_identifier"]:
            return Identifier(name=self._get_text(node, code_bytes))

        elif ntype == "qualified_identifier":
            # e.g. std::max or std::string
            txt = self._get_text(node, code_bytes)
            if txt.startswith("std::"):
                return Identifier(name=txt[5:])
            return Identifier(name=txt)

        elif ntype == "parenthesized_expression":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_expression(c, code_bytes)

        elif ntype == "binary_expression":
            left_n = node.child_by_field_name("left")
            op_n = node.child_by_field_name("operator")
            right_n = node.child_by_field_name("right")
            left_expr = self._parse_expression(left_n, code_bytes)
            right_expr = self._parse_expression(right_n, code_bytes)
            op_str = self._get_text(op_n, code_bytes) if op_n else "+"

            # Translate C++ logical operators to universal IR
            if op_str == "&&":
                op_str = "and"
            elif op_str == "||":
                op_str = "or"

            return BinaryOp(left=left_expr, op=op_str, right=right_expr)

        elif ntype == "unary_expression":
            op_n = node.child_by_field_name("operator")
            arg_n = node.child_by_field_name("argument")
            op_str = self._get_text(op_n, code_bytes) if op_n else "-"
            arg_expr = self._parse_expression(arg_n, code_bytes)
            if op_str == "!":
                op_str = "not"
            return UnaryOp(op=op_str, operand=arg_expr)

        elif ntype == "subscript_expression":
            arg_n = node.child_by_field_name("argument")
            index_n = node.child_by_field_name("index")
            if not index_n:
                # May be in subscript_argument_list
                for c in node.children:
                    if c.type == "subscript_argument_list":
                        for sc in c.children:
                            if sc.type not in ["[", "]"]:
                                index_n = sc
                                break
            arr_expr = self._parse_expression(arg_n, code_bytes)
            idx_expr = self._parse_expression(index_n, code_bytes)
            return ArrayAccess(array=arr_expr, index=idx_expr)

        elif ntype == "initializer_list":
            elems: List[Expression] = []
            for c in node.children:
                if c.type not in ["{", "}", ","]:
                    e = self._parse_expression(c, code_bytes)
                    if e:
                        elems.append(e)
            return ArrayLiteral(elements=elems)

        elif ntype == "call_expression":
            func_n = node.child_by_field_name("function")
            args_n = node.child_by_field_name("arguments")

            args: List[Expression] = []
            if args_n:
                for c in args_n.children:
                    if c.type not in ["(", ")", ","]:
                        e = self._parse_expression(c, code_bytes)
                        if e:
                            args.append(e)

            # Check if method call like arr.size() or arr.push_back(x)
            if func_n and func_n.type == "field_expression":
                obj_n = func_n.child_by_field_name("argument")
                field_n = func_n.child_by_field_name("field")
                obj_expr = self._parse_expression(obj_n, code_bytes)
                field_name = self._get_text(field_n, code_bytes) if field_n else ""

                if field_name in ["size", "length"]:
                    return ArrayLength(array=obj_expr)
                elif field_name == "push_back":
                    obj_name = obj_expr.name if isinstance(obj_expr, Identifier) else "arr"
                    return FunctionCall(name=f"{obj_name}.append", args=args)
                else:
                    obj_name = obj_expr.name if isinstance(obj_expr, Identifier) else ""
                    return FunctionCall(name=f"{obj_name}.{field_name}", args=args)

            fn_name = self._get_text(func_n, code_bytes) if func_n else ""
            if fn_name.startswith("std::"):
                fn_name = fn_name[5:]

            # Map floorDiv(a, b) back to floor division operator //
            if fn_name == "floorDiv" and len(args) == 2:
                return BinaryOp(left=args[0], op="//", right=args[1])

            return FunctionCall(name=fn_name, args=args)

        return None

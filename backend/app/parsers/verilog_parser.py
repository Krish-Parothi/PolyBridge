from typing import List, Optional, Any, Set, Dict, Tuple
from tree_sitter import Language, Parser, Node
import tree_sitter_verilog as tsverilog

from app.ir.nodes import (
    Program, FunctionDef, Parameter, Statement, Expression,
    VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
    ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, IRType, TypeKind
)
from app.parsers.diagnostics import attach_tree_diagnostics

class VerilogParser:
    """Parses IEEE 1364-2001 Verilog RTL and testbenches into PolyBridge Universal IR."""

    def __init__(self):
        self.language = Language(tsverilog.language())
        self.parser = Parser(self.language)
        self.diagnostics: List[str] = []

    def parse(self, code: str) -> Program:
        self.diagnostics = []
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []

        modules: List[Node] = []
        for child in root.children:
            if child.type == "module_declaration":
                modules.append(child)

        # Distinguish RTL modules from testbench modules
        rtl_modules: List[Node] = []
        tb_modules: List[Node] = []

        for m in modules:
            name = self._get_module_name(m, code_bytes)
            if name.endswith("_tb") or self._has_initial_block(m):
                tb_modules.append(m)
            else:
                rtl_modules.append(m)

        # 1. Parse RTL modules into FunctionDefs
        for m in rtl_modules:
            fn = self._parse_module_as_function(m, code_bytes)
            if fn:
                functions.append(fn)

        # 2. Parse Testbench modules into global_statements
        for m in tb_modules:
            tb_stmts = self._parse_testbench(m, code_bytes, rtl_modules)
            global_statements.extend(tb_stmts)

        # If no testbench found, but we have an RTL function, create a default call in globals
        if not global_statements and functions:
            main_fn = functions[0]
            args = [Literal(value=0) for _ in main_fn.params]
            call = FunctionCall(name=main_fn.name, args=args)
            global_statements.append(PrintStmt(args=[call]))

        return attach_tree_diagnostics(
            Program(functions=functions, global_statements=global_statements),
            root,
            code_bytes,
        )

    def _get_text(self, node: Node, code_bytes: bytes) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode("utf-8")

    def _get_module_name(self, node: Node, code_bytes: bytes) -> str:
        for c in node.children:
            if c.type == "module_header":
                for hc in c.children:
                    if hc.type in ["simple_identifier", "identifier"]:
                        return self._get_text(hc, code_bytes)
        return ""

    def _has_initial_block(self, node: Node) -> bool:
        for c in node.children:
            if c.type == "module_or_generate_item":
                for gc in c.children:
                    if gc.type == "initial_construct":
                        return True
        return False

    def _parse_module_as_function(self, node: Node, code_bytes: bytes) -> Optional[FunctionDef]:
        module_name = self._get_module_name(node, code_bytes)
        if not module_name:
            return None

        params: List[Parameter] = []
        output_name: Optional[str] = None

        # Extract ports
        for c in node.children:
            if c.type == "module_ansi_header":
                for ac in c.children:
                    if ac.type == "list_of_port_declarations":
                        for port in ac.children:
                            if port.type == "ansi_port_declaration":
                                p_dir, p_name = self._extract_port_info(port, code_bytes)
                                if p_dir == "inout":
                                    self.diagnostics.append(f"Scope violation: inout bidirectional tri-state port '{p_name}' not supported in procedural IR.")
                                elif p_dir == "input":
                                    # Filter clock / reset / handshake pins
                                    if p_name not in ["clk", "rst", "reset", "start"]:
                                        params.append(Parameter(name=p_name, param_type=IRType.int_type()))
                                elif p_dir == "output":
                                    if p_name not in ["done", "ready"]:
                                        output_name = p_name

        body_stmts: List[Statement] = []
        local_vars: Set[str] = set()

        for c in node.children:
            if c.type == "module_or_generate_item":
                for gc in c.children:
                    if gc.type == "package_or_generate_item_declaration":
                        # reg / wire declaration
                        for dc in gc.children:
                            if dc.type == "data_declaration":
                                for vlist in dc.children:
                                    if vlist.type == "list_of_variable_decl_assignments":
                                        for va in vlist.children:
                                            if va.type == "variable_decl_assignment":
                                                vname = self._get_text(va, code_bytes)
                                                if vname not in local_vars and vname != output_name:
                                                    local_vars.add(vname)
                                                    body_stmts.append(VarDecl(name=vname, var_type=IRType.int_type(), initializer=Literal(value=0)))

                    elif gc.type == "continuous_assign":
                        # assign result = a + b;
                        assign_stmt = self._parse_continuous_assign(gc, code_bytes, output_name)
                        if assign_stmt:
                            body_stmts.extend(assign_stmt)

                    elif gc.type == "always_construct":
                        stmts = self._parse_statement_recursive(gc, code_bytes, output_name)
                        # Filter duplicate initial default assignments like result = 0 if followed by assignment
                        filtered_stmts: List[Statement] = []
                        for s in stmts:
                            # If assigning 0 to output at line 1, skip if next assign exists
                            if isinstance(s, Assignment) and isinstance(s.target, Identifier) and s.target.name == output_name:
                                if isinstance(s.value, Literal) and s.value.value == 0 and len(stmts) > 1:
                                    continue
                            filtered_stmts.append(s)
                        body_stmts.extend(filtered_stmts)

        # Ensure return statement exists
        has_return = any(isinstance(s, ReturnStmt) for s in body_stmts)
        if not has_return:
            if output_name:
                body_stmts.append(ReturnStmt(value=Identifier(name=output_name)))
            else:
                body_stmts.append(ReturnStmt(value=Literal(value=0)))

        return FunctionDef(
            name=module_name,
            params=params,
            return_type=IRType.int_type(),
            body=body_stmts
        )

    def _extract_port_info(self, port_node: Node, code_bytes: bytes) -> Tuple[str, str]:
        p_dir = "input"
        p_name = ""
        for c in port_node.children:
            if c.type in ["net_port_header1", "variable_port_header"]:
                for hc in c.children:
                    if hc.type == "port_direction":
                        p_dir = self._get_text(hc, code_bytes).strip()
            elif c.type == "port_identifier":
                p_name = self._get_text(c, code_bytes).strip()
            elif c.type in ["simple_identifier", "identifier"]:
                p_name = self._get_text(c, code_bytes).strip()
        return p_dir, p_name

    def _parse_continuous_assign(self, node: Node, code_bytes: bytes, output_name: Optional[str]) -> List[Statement]:
        txt = self._get_text(node, code_bytes).strip()
        if txt.startswith("assign "):
            txt = txt[7:].rstrip(";")
        if "=" in txt:
            left_s, right_s = txt.split("=", 1)
            left_name = left_s.strip()
            sub_tree = self.parser.parse(right_s.strip().encode("utf-8"))
            val_expr = self._parse_verilog_expr(sub_tree.root_node, right_s.strip().encode("utf-8"))
            if not val_expr:
                val_expr = Identifier(name=right_s.strip())
            if left_name == output_name:
                return [ReturnStmt(value=val_expr)]
            else:
                return [Assignment(target=Identifier(name=left_name), value=val_expr)]
        return []

    def _parse_statement_recursive(self, node: Optional[Node], code_bytes: bytes, output_name: Optional[str]) -> List[Statement]:
        if not node:
            return []
        ntype = node.type

        if ntype in ["always_construct", "initial_construct", "statement_or_null", "statement", "statement_item", "seq_block"]:
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["always", "initial", "begin", "end", ";"]:
                    stmts.extend(self._parse_statement_recursive(c, code_bytes, output_name))
            return stmts

        elif ntype == "procedural_timing_control_statement":
            # Can be @(*) begin ... end or #10;
            stmts: List[Statement] = []
            for c in node.children:
                if c.type not in ["event_control", "delay_control", ";"]:
                    stmts.extend(self._parse_statement_recursive(c, code_bytes, output_name))
            return stmts

        elif ntype in ["blocking_assignment", "nonblocking_assignment"]:
            return self._parse_assignment_node(node, code_bytes, output_name)

        elif ntype == "conditional_statement":
            # if (cond) then_stmt else else_stmt
            cond_expr = None
            then_node = None
            else_node = None

            children = [c for c in node.children if c.type not in [";"]]
            idx = 0
            while idx < len(children):
                ch = children[idx]
                if ch.type in ["cond_predicate", "expression"]:
                    cond_expr = self._parse_verilog_expr(ch, code_bytes)
                    idx += 1
                elif ch.type == "(":
                    if idx + 1 < len(children):
                        cond_expr = self._parse_verilog_expr(children[idx + 1], code_bytes)
                        idx += 2
                    else:
                        idx += 1
                elif ch.type in ["statement_or_null", "statement", "seq_block"]:
                    if not then_node:
                        then_node = ch
                    else:
                        else_node = ch
                    idx += 1
                elif ch.type == "else":
                    idx += 1
                else:
                    idx += 1

            then_stmts = self._parse_statement_recursive(then_node, code_bytes, output_name) if then_node else []
            else_stmts = self._parse_statement_recursive(else_node, code_bytes, output_name) if else_node else []

            # Check if this conditional was an FSM reset check (if (rst) state <= 0; else case(state)...)
            if cond_expr and isinstance(cond_expr, Identifier) and cond_expr.name in ["rst", "reset"]:
                return else_stmts

            return [IfStmt(
                condition=cond_expr or Literal(value=True),
                then_branch=then_stmts,
                else_branch=else_stmts
            )]

        elif ntype == "loop_statement":
            # while (...) begin ... end
            cond_expr = None
            body_node = None
            for c in node.children:
                if c.type in ["expression", "mintypmax_expression"]:
                    cond_expr = self._parse_verilog_expr(c, code_bytes)
                elif c.type in ["statement_or_null", "statement", "seq_block"]:
                    body_node = c

            body_stmts = self._parse_statement_recursive(body_node, code_bytes, output_name) if body_node else []
            return [WhileStmt(
                condition=cond_expr or Literal(value=True),
                body=body_stmts
            )]

        elif ntype == "system_tf_call":
            return self._parse_system_tf_call(node, code_bytes)

        return []

    def _parse_assignment_node(self, node: Node, code_bytes: bytes, output_name: Optional[str]) -> List[Statement]:
        op_assign = node
        if node.type in ["blocking_assignment", "nonblocking_assignment"]:
            for c in node.children:
                if c.type == "operator_assignment":
                    op_assign = c
                    break

        lval_n = None
        rval_n = None

        for c in op_assign.children:
            if c.type in ["variable_lvalue", "net_lvalue"]:
                lval_n = c
            elif c.type in ["expression", "mintypmax_expression"]:
                rval_n = c

        if not lval_n or not rval_n:
            txt = self._get_text(node, code_bytes).strip().rstrip(";")
            if "<=" in txt:
                lhs, rhs = txt.split("<=", 1)
            elif "=" in txt:
                lhs, rhs = txt.split("=", 1)
            else:
                return []
            lhs = lhs.strip()
            rhs_text = rhs.strip()
            # A standalone sized literal (for example 32'd10) is often
            # exposed by Tree-sitter only as raw text in this fallback path.
            # Preserve it as a numeric IR literal instead of emitting invalid
            # Verilog syntax into software targets.
            if any(ch in rhs_text.lower() for ch in ["'b", "'o", "'d", "'h"]):
                r_expr = Literal(value=self._parse_verilog_number(rhs_text))
            else:
                sub_t = self.parser.parse(rhs_text.encode("utf-8"))
                r_expr = self._parse_verilog_expr(sub_t.root_node, rhs_text.encode("utf-8")) or Identifier(name=rhs_text)
            return [Assignment(target=Identifier(name=lhs), value=r_expr)]

        target_name = self._get_text(lval_n, code_bytes).strip()
        raw_value = self._get_text(rval_n, code_bytes).strip()
        val_expr = self._parse_verilog_expr(rval_n, code_bytes)
        if val_expr is None:
            if any(ch in raw_value.lower() for ch in ["'b", "'o", "'d", "'h"]):
                val_expr = Literal(value=self._parse_verilog_number(raw_value))
            else:
                val_expr = Identifier(name=raw_value)

        # Filter out FSM control signal assignments (e.g. state <= NEXT; done <= 1;)
        if target_name in ["state", "done", "ready"]:
            return []

        return [Assignment(target=Identifier(name=target_name), value=val_expr)]

    def _parse_system_tf_call(self, node: Node, code_bytes: bytes) -> List[Statement]:
        txt = self._get_text(node, code_bytes).strip()
        if "$finish" in txt:
            return []
        if "$display" in txt:
            arg_list_n = None
            for c in node.children:
                if c.type in ["list_of_arguments_parent", "list_of_arguments"]:
                    arg_list_n = c
                    break
            args: List[Expression] = []
            if arg_list_n:
                for c in arg_list_n.children:
                    if c.type not in ["(", ")", ","]:
                        c_text = self._get_text(c, code_bytes).strip()
                        # If string format like "%0d", skip if followed by variables
                        if c_text.startswith('"') and c_text.endswith('"'):
                            inner = c_text.strip('"')
                            # If format string contains RESULT: %0d, extract variable or message
                            if "%" in inner:
                                continue
                            if "simulation" in inner.lower():
                                continue
                            args.append(Literal(value=inner))
                        else:
                            e = self._parse_verilog_expr(c, code_bytes)
                            if e:
                                args.append(e)
            if args:
                return [PrintStmt(args=args)]
        return []

    def _parse_verilog_expr(self, node: Optional[Node], code_bytes: bytes) -> Optional[Expression]:
        if not node:
            return None
        ntype = node.type

        if ntype in ["simple_identifier", "identifier", "port_identifier"]:
            return Identifier(name=self._get_text(node, code_bytes).strip())

        elif ntype == "hierarchical_identifier":
            return Identifier(name=self._get_text(node, code_bytes).strip())

        elif ntype in ["number", "decimal_number", "integral_number"]:
            txt = self._get_text(node, code_bytes).strip()
            return Literal(value=self._parse_verilog_number(txt))

        elif ntype == "string_literal":
            txt = self._get_text(node, code_bytes).strip().strip('"')
            return Literal(value=txt)

        elif ntype == "primary":
            for c in node.children:
                if c.type not in ["(", ")"]:
                    return self._parse_verilog_expr(c, code_bytes)

        elif ntype in ["expression", "mintypmax_expression"]:
            valid_children = [c for c in node.children if c.type not in [";"]]
            if len(valid_children) == 1:
                return self._parse_verilog_expr(valid_children[0], code_bytes)
            elif len(valid_children) == 3 and valid_children[0].type in ["(", "expression", "primary"] and valid_children[2].type in [")", "expression", "primary"]:
                if valid_children[0].type == "(" and valid_children[2].type == ")":
                    return self._parse_verilog_expr(valid_children[1], code_bytes)
                left_e = self._parse_verilog_expr(valid_children[0], code_bytes)
                op_str = self._get_text(valid_children[1], code_bytes).strip()
                right_e = self._parse_verilog_expr(valid_children[2], code_bytes)

                if op_str == "&&":
                    op_str = "and"
                elif op_str == "||":
                    op_str = "or"

                return BinaryOp(left=left_e, op=op_str, right=right_e)
            elif len(valid_children) == 2:
                op_str = self._get_text(valid_children[0], code_bytes).strip()
                arg_e = self._parse_verilog_expr(valid_children[1], code_bytes)
                if op_str == "!":
                    op_str = "not"
                return UnaryOp(op=op_str, operand=arg_e)
            else:
                for c in node.children:
                    e = self._parse_verilog_expr(c, code_bytes)
                    if e:
                        return e

        return None

    def _parse_verilog_number(self, num_str: str) -> int:
        num_str = num_str.strip()
        if "'" in num_str:
            parts = num_str.split("'", 1)
            base_val = parts[1]
            base_char = base_val[0].lower()
            val_str = base_val[1:].replace("_", "")
            try:
                if base_char == 'd':
                    return int(val_str, 10)
                elif base_char == 'h':
                    return int(val_str, 16)
                elif base_char == 'b':
                    return int(val_str, 2)
                elif base_char == 'o':
                    return int(val_str, 8)
            except ValueError:
                return 0
        try:
            return int(num_str)
        except ValueError:
            return 0

    def _parse_testbench(self, node: Node, code_bytes: bytes, rtl_modules: List[Node]) -> List[Statement]:
        stmts: List[Statement] = []
        module_instances: Dict[str, Dict[str, str]] = {}  # mod_name -> {port: var}

        # Scan for module instantiation
        for c in node.children:
            if c.type == "module_or_generate_item":
                for gc in c.children:
                    if gc.type == "module_instantiation":
                        mod_name_n = gc.children[0]
                        mod_name = self._get_text(mod_name_n, code_bytes).strip()
                        connections: Dict[str, str] = {}
                        for h_inst in gc.children[1:]:
                            if h_inst.type == "hierarchical_instance":
                                for pc in h_inst.children:
                                    if pc.type == "list_of_port_connections":
                                        for conn in pc.children:
                                            if conn.type == "named_port_connection":
                                                # .port(var)
                                                port_n = conn.child_by_field_name("port_identifier") or conn.children[1]
                                                conn_port = self._get_text(port_n, code_bytes).strip()
                                                expr_n = conn.child_by_field_name("expression") or conn.children[3]
                                                conn_var = self._get_text(expr_n, code_bytes).strip()
                                                connections[conn_port] = conn_var
                        module_instances[mod_name] = connections

        # Scan for initial construct
        for c in node.children:
            if c.type == "module_or_generate_item":
                for gc in c.children:
                    if gc.type == "initial_construct":
                        raw_stmts = self._parse_statement_recursive(gc, code_bytes, None)
                        stmts.extend(raw_stmts)

        # Connect instantiated module if present
        for mod_name, connections in module_instances.items():
            args: List[Expression] = []
            for p, var in connections.items():
                if p not in ["clk", "rst", "reset", "start", "done", "ready", "result"]:
                    args.append(Identifier(name=var))
            out_var = connections.get("result", "tb_result")
            instantiated_call = FunctionCall(name=mod_name, args=args)
            # Find the position where out_var is first used or printed, and insert the call before it
            insert_idx = len(stmts)
            for i, s in enumerate(stmts):
                if isinstance(s, PrintStmt):
                    insert_idx = i
                    break
            stmts.insert(insert_idx, Assignment(target=Identifier(name=out_var), value=instantiated_call))

        return stmts

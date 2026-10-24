from typing import List, Optional, Any
from tree_sitter import Node

from app.parsers.cpp_parser import CppParser
from app.ir.nodes import (
    Program, FunctionDef, Statement, Expression,
    PrintStmt, ExpressionStmt, FunctionCall, Literal
)
from app.parsers.diagnostics import attach_tree_diagnostics

class ArduinoParser(CppParser):
    """Parses Arduino C++ (.ino) code into PolyBridge Universal IR."""

    def __init__(self):
        super().__init__()

    def parse(self, code: str) -> Program:
        code_bytes = code.encode("utf-8")
        tree = self.parser.parse(code_bytes)
        root = tree.root_node

        functions: List[FunctionDef] = []
        global_statements: List[Statement] = []
        setup_statements: List[Statement] = []
        loop_statements: List[Statement] = []

        for child in root.children:
            if child.type == "function_definition":
                decl_n = child.child_by_field_name("declarator")
                fn_name = self._extract_function_name(decl_n, code_bytes)

                if fn_name == "setup":
                    body_n = child.child_by_field_name("body")
                    if body_n:
                        for s in body_n.children:
                            if s.type not in ["{", "}"]:
                                parsed_s = self._parse_arduino_statement(s, code_bytes)
                                if parsed_s:
                                    setup_statements.extend(parsed_s)

                elif fn_name == "loop":
                    body_n = child.child_by_field_name("body")
                    if body_n:
                        for s in body_n.children:
                            if s.type not in ["{", "}"]:
                                parsed_s = self._parse_arduino_statement(s, code_bytes)
                                if parsed_s:
                                    loop_statements.extend(parsed_s)

                elif fn_name in ["floorDiv", "main"]:
                    # Skip helper or entrypoint
                    continue

                else:
                    fn = self._parse_function(child, code_bytes)
                    if fn:
                        functions.append(fn)

            elif child.type == "struct_specifier" or (child.type == "template_declaration" and "Vector" in self._get_text(child, code_bytes)):
                # Skip embedded Vector container definition
                continue

        # Setup statements take precedence for procedural global statements
        if setup_statements:
            global_statements = setup_statements
        elif loop_statements:
            global_statements = loop_statements

        return attach_tree_diagnostics(
            Program(functions=functions, global_statements=global_statements, imports=[]),
            root,
            code_bytes,
        )

    def _parse_arduino_statement(self, node: Node, code_bytes: bytes) -> List[Statement]:
        # Filter out Arduino boilerplate statements
        txt = self._get_text(node, code_bytes).strip()

        # Serial.begin(9600);
        if "Serial.begin" in txt:
            return []
        # while (!Serial) { delay(10); }
        if "!Serial" in txt:
            return []
        # delay(1000); or idle delay
        if txt.startswith("delay(") and (";" in txt):
            return []

        # Check for Serial.println(...) or Serial.print(...)
        if "Serial.println" in txt or "Serial.print" in txt:
            expr_child = node.children[0] if node.children else None
            if expr_child and expr_child.type == "call_expression":
                args_n = expr_child.child_by_field_name("arguments")
                args: List[Expression] = []
                if args_n:
                    for c in args_n.children:
                        if c.type not in ["(", ")", ","]:
                            e = self._parse_expression(c, code_bytes)
                            if e:
                                args.append(e)
                return [PrintStmt(args=args)]

        # Otherwise parse with standard C++ statement parser
        return self._parse_statement(node, code_bytes)

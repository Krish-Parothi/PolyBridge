from typing import List, Optional, Set, Dict, Any
from app.ir.nodes import (
    Program, FunctionDef, Parameter, Statement, Expression,
    VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
    ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, IRType, TypeKind
)

class ArduinoEmitter:
    """Emits production-grade Arduino C++ (.ino) sketches for AVR (Uno, Nano, Mega) and ESP32."""

    def __init__(self, indent_str: str = "    ", default_baud_rate: int = 9600):
        self.indent_str = indent_str
        self.default_baud_rate = default_baud_rate
        self.declared_vars: Set[str] = set()
        self.var_types: Dict[str, str] = {}
        self.uses_vectors = False
        self.needs_floor_div = False
        self.needs_array_print_helper = False

    def emit(self, program: Program) -> str:
        self.declared_vars.clear()
        self.var_types.clear()
        self.uses_vectors = False
        self.needs_floor_div = False
        self.needs_array_print_helper = False

        # Pre-scan for vector and array print usage
        self._detect_array_usage(program)

        body_lines: List[str] = []

        # Emit functions
        for fn in program.functions:
            body_lines.extend(self._emit_function(fn))
            body_lines.append("")

        # Emit setup()
        setup_lines: List[str] = [
            "void setup() {",
            f"{self._indent(1)}Serial.begin({self.default_baud_rate});",
            f"{self._indent(1)}while (!Serial) {{ delay(10); }}",
            ""
        ]

        for stmt in program.global_statements:
            setup_lines.extend(self._emit_statement(stmt, indent_level=1))

        setup_lines.append("}")
        setup_lines.append("")

        # Emit loop()
        loop_lines: List[str] = [
            "void loop() {",
            f"{self._indent(1)}// Microcontroller idle loop",
            f"{self._indent(1)}delay(1000);",
            "}"
        ]

        # Floor division helper if needed
        helpers: List[str] = []
        if self.needs_floor_div:
            helpers.extend([
                "int floorDiv(int a, int b) {",
                f"{self.indent_str}int d = a / b;",
                f"{self.indent_str}int r = a % b;",
                f"{self.indent_str}if ((r != 0) && ((r < 0) ^ (b < 0))) {{",
                f"{self.indent_str}{self.indent_str}d--;",
                f"{self.indent_str}}}",
                f"{self.indent_str}return d;",
                "}",
                ""
            ])

        helpers.extend([
            "template <typename T>",
            "void printValue(const T& val) {",
            f"{self.indent_str}Serial.print(val);",
            "}",
            "",
            "template <typename T>",
            "void printValue(const std::vector<T>& vec) {",
            f"{self.indent_str}Serial.print(\"[\");",
            f"{self.indent_str}for (size_t i = 0; i < vec.size(); i++) {{",
            f"{self.indent_str}{self.indent_str}Serial.print(vec[i]);",
            f"{self.indent_str}{self.indent_str}if (i + 1 < vec.size()) Serial.print(\", \");",
            f"{self.indent_str}}}",
            f"{self.indent_str}Serial.print(\"]\");",
            "}",
            ""
        ])

        # Header Comments & Includes
        headers: List[str] = [
            "// ============================================================================",
            "// PolyBridge Embedded Synthesis: Arduino C++ (.ino) Sketch",
            "// Target Microcontrollers: Arduino Uno / Nano (ATmega328P), Mega, ESP32, ESP8266",
            "// Baud Rate: 9600 bps | Open Serial Monitor at 9600 baud to view output",
            "// ============================================================================",
            "",
            "#include <Arduino.h>"
        ]
        if self.uses_vectors:
            headers.append("#include <vector>")
        headers.append("")

        lines: List[str] = []
        lines.extend(headers)
        if helpers:
            lines.extend(helpers)
        lines.extend(body_lines)
        lines.extend(setup_lines)
        lines.extend(loop_lines)

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _to_arduino_type(self, t: IRType) -> str:
        if t.kind == TypeKind.INT:
            return "int"
        elif t.kind == TypeKind.FLOAT:
            return "float"
        elif t.kind == TypeKind.STRING:
            return "String"
        elif t.kind == TypeKind.BOOL:
            return "bool"
        elif t.kind == TypeKind.VOID:
            return "void"
        elif t.kind == TypeKind.ARRAY:
            self.uses_vectors = True
            elem = self._to_arduino_type(t.element_type) if t.element_type else "int"
            return f"std::vector<{elem}>"
        return "int"

    def _detect_array_usage(self, program: Program):
        def scan_expr(e: Expression):
            if isinstance(e, ArrayLiteral):
                self.uses_vectors = True
            elif isinstance(e, BinaryOp):
                scan_expr(e.left)
                scan_expr(e.right)
            elif isinstance(e, UnaryOp):
                scan_expr(e.operand)
            elif isinstance(e, FunctionCall):
                for a in e.args: scan_expr(a)

        def scan_stmt(s: Statement):
            if isinstance(s, VarDecl):
                if s.inferred_type and s.inferred_type.kind == TypeKind.ARRAY:
                    self.uses_vectors = True
                if s.initializer:
                    scan_expr(s.initializer)
            elif isinstance(s, Assignment):
                scan_expr(s.value)
            elif isinstance(s, IfStmt):
                scan_expr(s.condition)
                for st in s.then_branch: scan_stmt(st)
                for st in s.else_branch: scan_stmt(st)
            elif isinstance(s, WhileStmt):
                scan_expr(s.condition)
                for st in s.body: scan_stmt(st)
            elif isinstance(s, ForRangeStmt):
                for st in s.body: scan_stmt(st)
            elif isinstance(s, ReturnStmt) and s.value:
                scan_expr(s.value)
            elif isinstance(s, ExpressionStmt):
                scan_expr(s.expr)
            elif isinstance(s, PrintStmt):
                for a in s.args: scan_expr(a)

        for fn in program.functions:
            for st in fn.body: scan_stmt(st)
        for st in program.global_statements: scan_stmt(st)

    def _emit_function(self, fn: FunctionDef) -> List[str]:
        ret_type = self._to_arduino_type(fn.return_type) if fn.return_type else "void"
        params_str = ", ".join(
            f"{self._to_arduino_type(p.param_type) if p.param_type else 'int'} {p.name}"
            for p in fn.params
        )

        lines: List[str] = [f"{ret_type} {fn.name}({params_str}) {{"]
        for p in fn.params:
            self.declared_vars.add(p.name)

        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=1))

        lines.append("}")
        return lines

    def _emit_statement(self, stmt: Statement, indent_level: int = 0) -> List[str]:
        ind = self._indent(indent_level)

        if isinstance(stmt, VarDecl):
            t_str = self._to_arduino_type(stmt.inferred_type) if stmt.inferred_type else "int"
            self.declared_vars.add(stmt.name)
            self.var_types[stmt.name] = t_str

            if stmt.initializer is not None:
                if isinstance(stmt.initializer, ArrayLiteral):
                    # Direct std::vector initialization or initializer list
                    init_expr = self._emit_expr(stmt.initializer)
                    return [f"{ind}{t_str} {stmt.name} = {init_expr};"]
                else:
                    init_str = self._emit_expr(stmt.initializer)
                    return [f"{ind}{t_str} {stmt.name} = {init_str};"]
            return [f"{ind}{t_str} {stmt.name};"]

        elif isinstance(stmt, Assignment):
            target_str = self._emit_expr(stmt.target)
            val_str = self._emit_expr(stmt.value)
            return [f"{ind}{target_str} = {val_str};"]

        elif isinstance(stmt, IfStmt):
            cond_str = self._emit_expr(stmt.condition)
            lines = [f"{ind}if ({cond_str}) {{"]
            for s in stmt.then_branch:
                lines.extend(self._emit_statement(s, indent_level + 1))
            if stmt.else_branch:
                lines.append(f"{ind}}} else {{")
                for s in stmt.else_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, WhileStmt):
            cond_str = self._emit_expr(stmt.condition)
            lines = [f"{ind}while ({cond_str}) {{"]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ForRangeStmt):
            start = self._emit_expr(stmt.start)
            end = self._emit_expr(stmt.end)
            step = self._emit_expr(stmt.step) if stmt.step else "1"
            lines = [
                f"{ind}for (int {stmt.var_name} = {start}; {stmt.var_name} < {end}; {stmt.var_name} += {step}) {{"
            ]
            for s in stmt.body:
                lines.extend(self._emit_statement(s, indent_level + 1))
            lines.append(f"{ind}}}")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                return [f"{ind}return {self._emit_expr(stmt.value)};"]
            return [f"{ind}return;"]

        elif isinstance(stmt, BreakStmt):
            return [f"{ind}break;"]

        elif isinstance(stmt, ContinueStmt):
            return [f"{ind}continue;"]

        elif isinstance(stmt, ExpressionStmt):
            return [f"{ind}{self._emit_expr(stmt.expr)};"]

        elif isinstance(stmt, PrintStmt):
            lines: List[str] = []
            for i, arg in enumerate(stmt.args):
                arg_expr = self._emit_expr(arg)
                lines.append(f"{ind}printValue({arg_expr});")
                if i + 1 < len(stmt.args):
                    lines.append(f'{ind}Serial.print(" ");')
            lines.append(f"{ind}Serial.println();")
            return lines

        return [f"{ind}// Unsupported statement: {type(stmt).__name__}"]

    def _emit_expr(self, expr: Expression) -> str:
        if isinstance(expr, Literal):
            if expr.value is None:
                return "0"
            elif isinstance(expr.value, bool):
                return "true" if expr.value else "false"
            elif isinstance(expr.value, str):
                escaped = expr.value.replace('"', '\\"')
                return f'"{escaped}"'
            return str(expr.value)

        elif isinstance(expr, Identifier):
            return expr.name

        elif isinstance(expr, BinaryOp):
            left_str = self._emit_expr(expr.left)
            right_str = self._emit_expr(expr.right)
            op = expr.op

            if op == "//":
                self.needs_floor_div = True
                return f"floorDiv({left_str}, {right_str})"
            elif op == "and":
                op = "&&"
            elif op == "or":
                op = "||"

            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand)
            op = "!" if expr.op in ["!", "not"] else expr.op
            return f"{op}({operand_str})"

        elif isinstance(expr, ArrayLiteral):
            elements = [self._emit_expr(e) for e in expr.elements]
            return "{" + ", ".join(elements) + "}"

        elif isinstance(expr, ArrayAccess):
            arr_str = self._emit_expr(expr.array)
            idx_str = self._emit_expr(expr.index)
            return f"{arr_str}[{idx_str}]"

        elif isinstance(expr, ArrayLength):
            arr_str = self._emit_expr(expr.array)
            return f"{arr_str}.size()"

        elif isinstance(expr, FunctionCall):
            name = expr.name
            args_str = ", ".join(self._emit_expr(a) for a in expr.args)
            return f"{name}({args_str})"

        return "0"

from typing import List, Optional, Set, Dict, Any, Tuple
from app.ir.nodes import (
    Program, FunctionDef, Parameter, Statement, Expression,
    VarDecl, Assignment, IfStmt, WhileStmt, ForRangeStmt,
    ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, IRType, TypeKind
)

class VerilogEmitter:
    """Emits synthesizable IEEE 1364-2001 Verilog RTL and automated testbenches from Universal IR."""

    def __init__(self, indent_str: str = "    ", default_bit_width: int = 32):
        self.indent_str = indent_str
        self.default_bit_width = default_bit_width
        self.declared_regs: Set[str] = set()
        self.function_params: Set[str] = set()

    def emit(self, program: Program) -> str:
        self.declared_regs.clear()
        self.function_params.clear()

        lines: List[str] = [
            "// ============================================================================",
            "// PolyBridge HLS (High-Level Synthesis) - Automated Hardware RTL Generation",
            "// Target: IEEE 1364-2001 Synthesizable Verilog",
            "// ============================================================================",
            ""
        ]

        # Emit modules for each function in the program
        for fn in program.functions:
            module_code, tb_code = self._emit_module_and_testbench(fn, program.global_statements)
            lines.extend(module_code)
            lines.append("")
            lines.extend(tb_code)
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _indent(self, level: int) -> str:
        return self.indent_str * level

    def _has_loops(self, stmts: List[Statement]) -> bool:
        """Determines if a statement list contains loops (requiring a clocked FSM)."""
        for stmt in stmts:
            if isinstance(stmt, (WhileStmt, ForRangeStmt)):
                return True
            if isinstance(stmt, IfStmt):
                if self._has_loops(stmt.then_branch) or self._has_loops(stmt.else_branch):
                    return True
        return False

    def _collect_local_vars(self, stmts: List[Statement]) -> Set[str]:
        """Collects all local variable names declared or assigned in the function."""
        vars_found: Set[str] = set()
        for stmt in stmts:
            if isinstance(stmt, VarDecl):
                vars_found.add(stmt.name)
            elif isinstance(stmt, Assignment) and isinstance(stmt.target, Identifier):
                vars_found.add(stmt.target.name)
            elif isinstance(stmt, IfStmt):
                vars_found.update(self._collect_local_vars(stmt.then_branch))
                vars_found.update(self._collect_local_vars(stmt.else_branch))
            elif isinstance(stmt, (WhileStmt, ForRangeStmt)):
                if isinstance(stmt, ForRangeStmt):
                    vars_found.add(stmt.var_name)
                vars_found.update(self._collect_local_vars(stmt.body))
        return vars_found

    def _emit_module_and_testbench(self, fn: FunctionDef, globals_stmts: List[Statement]) -> Tuple[List[str], List[str]]:
        is_sequential = self._has_loops(fn.body)
        self.function_params = {p.name for p in fn.params}
        # `result` is already the module output port.  Verilog source parsed
        # back into IR may contain an assignment to that name; it must not be
        # redeclared as an internal register.
        local_vars = self._collect_local_vars(fn.body) - self.function_params - {"result", "done", "ready", "state"}

        module_lines: List[str] = []
        tb_lines: List[str] = []

        if is_sequential:
            module_lines = self._emit_sequential_fsm(fn, local_vars)
            tb_lines = self._emit_sequential_testbench(fn, globals_stmts)
        else:
            module_lines = self._emit_combinational_module(fn, local_vars)
            tb_lines = self._emit_combinational_testbench(fn, globals_stmts)

        return module_lines, tb_lines

    # --------------------------------------------------------------------------
    # A. Combinational Logic Module (Zero-Clock Latency, e.g. ALU, Adders, Math)
    # --------------------------------------------------------------------------
    def _emit_combinational_module(self, fn: FunctionDef, local_vars: Set[str]) -> List[str]:
        ind = self._indent(1)
        bw = self.default_bit_width - 1
        lines: List[str] = [
            f"// Module: {fn.name} (Combinational Hardware Logic)",
            f"module {fn.name} ("
        ]

        port_decls: List[str] = []
        for p in fn.params:
            port_decls.append(f"{ind}input  wire [{bw}:0] {p.name}")
        port_decls.append(f"{ind}output reg  [{bw}:0] result")

        lines.append(",\n".join(port_decls))
        lines.append(");")
        lines.append("")

        # Internal registers for local variables
        for var in sorted(local_vars):
            lines.append(f"{ind}reg [{bw}:0] {var};")
        if local_vars:
            lines.append("")

        lines.append(f"{ind}always @(*) begin")
        # Default assignment to prevent latch creation
        lines.append(f"{self._indent(2)}result = {self.default_bit_width}'d0;")
        for var in sorted(local_vars):
            lines.append(f"{self._indent(2)}{var} = {self.default_bit_width}'d0;")

        for stmt in fn.body:
            lines.extend(self._emit_statement(stmt, indent_level=2, is_sequential=False))

        lines.append(f"{ind}end")
        lines.append("")
        lines.append("endmodule")
        return lines

    def _emit_combinational_testbench(self, fn: FunctionDef, globals_stmts: List[Statement]) -> List[str]:
        ind = self._indent(1)
        bw = self.default_bit_width - 1
        lines: List[str] = [
            f"// Testbench for {fn.name}",
            f"module {fn.name}_tb;",
            ""
        ]

        for p in fn.params:
            lines.append(f"{ind}reg  [{bw}:0] tb_{p.name};")
        lines.append(f"{ind}wire [{bw}:0] tb_result;")
        lines.append("")

        # Instantiate UUT
        lines.append(f"{ind}// Instantiate Unit Under Test (UUT)")
        lines.append(f"{ind}{fn.name} uut (")
        port_maps: List[str] = []
        for p in fn.params:
            port_maps.append(f"{self._indent(2)}.{p.name}(tb_{p.name})")
        port_maps.append(f"{self._indent(2)}.result(tb_result)")
        lines.append(",\n".join(port_maps))
        lines.append(f"{ind});")
        lines.append("")

        # Initial stimulus
        lines.append(f"{ind}initial begin")
        # Extract arguments from global call if available, or generate standard test vectors
        sample_args = self._extract_call_args(fn.name, globals_stmts)
        if sample_args and len(sample_args) == len(fn.params):
            for p, val in zip(fn.params, sample_args):
                lines.append(f"{self._indent(2)}tb_{p.name} = {val};")
        else:
            for i, p in enumerate(fn.params):
                default_val = (i + 1) * 10
                lines.append(f"{self._indent(2)}tb_{p.name} = {self.default_bit_width}'d{default_val};")

        lines.append(f"{self._indent(2)}#10;")
        # Keep the simulation contract comparable with software targets: the
        # testbench emits the observable result, not a diagnostic banner.
        lines.append(f"{self._indent(2)}$display(\"%0d\", tb_result);")
        lines.append(f"{self._indent(2)}$finish;")
        lines.append(f"{ind}end")
        lines.append("")
        lines.append("endmodule")
        return lines

    # --------------------------------------------------------------------------
    # B. Sequential FSM Module (Clocked Hardware for Loops: GCD, Fibonacci, etc.)
    # --------------------------------------------------------------------------
    def _emit_sequential_fsm(self, fn: FunctionDef, local_vars: Set[str]) -> List[str]:
        ind = self._indent(1)
        bw = self.default_bit_width - 1
        lines: List[str] = [
            f"// Module: {fn.name} (Sequential Finite State Machine)",
            f"module {fn.name} ("
        ]

        port_decls: List[str] = [
            f"{ind}input  wire        clk",
            f"{ind}input  wire        rst",
            f"{ind}input  wire        start"
        ]
        for p in fn.params:
            port_decls.append(f"{ind}input  wire [{bw}:0] {p.name}")
        port_decls.append(f"{ind}output reg  [{bw}:0] result")
        port_decls.append(f"{ind}output reg         done")

        lines.append(",\n".join(port_decls))
        lines.append(");")
        lines.append("")

        # State declarations
        lines.append(f"{ind}// FSM States")
        lines.append(f"{ind}localparam STATE_IDLE  = 2'b00;")
        lines.append(f"{ind}localparam STATE_EXEC  = 2'b01;")
        lines.append(f"{ind}localparam STATE_DONE  = 2'b10;")
        lines.append("")
        lines.append(f"{ind}reg [1:0]  state;")

        # Internal registers for parameters and locals
        for p in fn.params:
            lines.append(f"{ind}reg [{bw}:0] reg_{p.name};")
        for var in sorted(local_vars):
            lines.append(f"{ind}reg [{bw}:0] reg_{var};")
        lines.append("")

        # Clocked sequential process
        lines.append(f"{ind}always @(posedge clk or posedge rst) begin")
        lines.append(f"{self._indent(2)}if (rst) begin")
        lines.append(f"{self._indent(3)}state  <= STATE_IDLE;")
        lines.append(f"{self._indent(3)}done   <= 1'b0;")
        lines.append(f"{self._indent(3)}result <= {self.default_bit_width}'d0;")
        for p in fn.params:
            lines.append(f"{self._indent(3)}reg_{p.name} <= {self.default_bit_width}'d0;")
        for var in sorted(local_vars):
            lines.append(f"{self._indent(3)}reg_{var} <= {self.default_bit_width}'d0;")
        lines.append(f"{self._indent(2)}end else begin")
        lines.append(f"{self._indent(3)}case (state)")

        # IDLE state
        lines.append(f"{self._indent(4)}STATE_IDLE: begin")
        lines.append(f"{self._indent(5)}done <= 1'b0;")
        lines.append(f"{self._indent(5)}if (start) begin")
        for p in fn.params:
            lines.append(f"{self._indent(6)}reg_{p.name} <= {p.name};")
        # Initialize locals before loop
        for stmt in fn.body:
            if not isinstance(stmt, (WhileStmt, ForRangeStmt, ReturnStmt)):
                lines.extend(self._emit_fsm_init_stmt(stmt, indent_level=6))
            elif isinstance(stmt, ForRangeStmt):
                start = self._emit_expr(stmt.start, use_reg_prefix=True)
                lines.append(f"{self._indent(6)}reg_{stmt.var_name} <= {start};")
        lines.append(f"{self._indent(6)}state <= STATE_EXEC;")
        lines.append(f"{self._indent(5)}end")
        lines.append(f"{self._indent(4)}end")

        # EXEC state (Loop execution)
        lines.append(f"{self._indent(4)}STATE_EXEC: begin")
        loop_stmt = next((s for s in fn.body if isinstance(s, (WhileStmt, ForRangeStmt))), None)
        if isinstance(loop_stmt, WhileStmt):
            cond_str = self._emit_expr(loop_stmt.condition, use_reg_prefix=True)
            lines.append(f"{self._indent(5)}if ({cond_str}) begin")
            for s in loop_stmt.body:
                lines.extend(self._emit_statement(s, indent_level=6, is_sequential=True, use_reg_prefix=True))
            lines.append(f"{self._indent(5)}end else begin")
            # Extract return expression
            ret_stmt = next((s for s in fn.body if isinstance(s, ReturnStmt)), None)
            if ret_stmt and ret_stmt.value:
                ret_val = self._emit_expr(ret_stmt.value, use_reg_prefix=True)
                lines.append(f"{self._indent(6)}result <= {ret_val};")
            lines.append(f"{self._indent(6)}done   <= 1'b1;")
            lines.append(f"{self._indent(6)}state  <= STATE_DONE;")
            lines.append(f"{self._indent(5)}end")
        elif isinstance(loop_stmt, ForRangeStmt):
            start = self._emit_expr(loop_stmt.start, use_reg_prefix=True) if loop_stmt.start else "0"
            end = self._emit_expr(loop_stmt.end, use_reg_prefix=True) if loop_stmt.end else "0"
            step = f"reg_{loop_stmt.var_name} + {self._emit_expr(loop_stmt.step, use_reg_prefix=True)}" if loop_stmt.step else f"reg_{loop_stmt.var_name} + 1"
            lines.append(f"{self._indent(5)}if (reg_{loop_stmt.var_name} < {end}) begin")
            for s in loop_stmt.body:
                lines.extend(self._emit_statement(s, indent_level=6, is_sequential=True, use_reg_prefix=True))
            lines.append(f"{self._indent(6)}reg_{loop_stmt.var_name} <= {step};")
            lines.append(f"{self._indent(5)}end else begin")
            ret_stmt = next((s for s in fn.body if isinstance(s, ReturnStmt)), None)
            if ret_stmt and ret_stmt.value:
                ret_val = self._emit_expr(ret_stmt.value, use_reg_prefix=True)
                lines.append(f"{self._indent(6)}result <= {ret_val};")
            lines.append(f"{self._indent(6)}done   <= 1'b1;")
            lines.append(f"{self._indent(6)}state  <= STATE_DONE;")
            lines.append(f"{self._indent(5)}end")
        lines.append(f"{self._indent(4)}end")

        # DONE state
        lines.append(f"{self._indent(4)}STATE_DONE: begin")
        lines.append(f"{self._indent(5)}done  <= 1'b1;")
        lines.append(f"{self._indent(5)}state <= STATE_IDLE;")
        lines.append(f"{self._indent(4)}end")

        lines.append(f"{self._indent(3)}endcase")
        lines.append(f"{self._indent(2)}end")
        lines.append(f"{ind}end")
        lines.append("")
        lines.append("endmodule")
        return lines

    def _emit_sequential_testbench(self, fn: FunctionDef, globals_stmts: List[Statement]) -> List[str]:
        ind = self._indent(1)
        bw = self.default_bit_width - 1
        lines: List[str] = [
            f"// Testbench for {fn.name} FSM",
            f"module {fn.name}_tb;",
            ""
        ]

        lines.append(f"{ind}reg         clk;")
        lines.append(f"{ind}reg         rst;")
        lines.append(f"{ind}reg         start;")
        for p in fn.params:
            lines.append(f"{ind}reg  [{bw}:0] tb_{p.name};")
        lines.append(f"{ind}wire [{bw}:0] tb_result;")
        lines.append(f"{ind}wire        tb_done;")
        lines.append("")

        # Clock generator (100MHz, 10ns period)
        lines.append(f"{ind}// Clock Generator (10ns period / 100MHz)")
        lines.append(f"{ind}always #5 clk = ~clk;")
        lines.append("")

        # UUT instantiation
        lines.append(f"{ind}// Instantiate Unit Under Test (UUT)")
        lines.append(f"{ind}{fn.name} uut (")
        port_maps: List[str] = [
            f"{self._indent(2)}.clk(clk)",
            f"{self._indent(2)}.rst(rst)",
            f"{self._indent(2)}.start(start)"
        ]
        for p in fn.params:
            port_maps.append(f"{self._indent(2)}.{p.name}(tb_{p.name})")
        port_maps.append(f"{self._indent(2)}.result(tb_result)")
        port_maps.append(f"{self._indent(2)}.done(tb_done)")
        lines.append(",\n".join(port_maps))
        lines.append(f"{ind});")
        lines.append("")

        # Stimulus
        lines.append(f"{ind}initial begin")
        lines.append(f"{self._indent(2)}clk = 0; rst = 1; start = 0;")

        sample_args = self._extract_call_args(fn.name, globals_stmts)
        if sample_args and len(sample_args) == len(fn.params):
            for p, val in zip(fn.params, sample_args):
                lines.append(f"{self._indent(2)}tb_{p.name} = {val};")
        else:
            for i, p in enumerate(fn.params):
                default_val = (i + 1) * 12
                lines.append(f"{self._indent(2)}tb_{p.name} = {self.default_bit_width}'d{default_val};")

        lines.append(f"{self._indent(2)}#20 rst = 0;")
        lines.append(f"{self._indent(2)}#10 start = 1;")
        lines.append(f"{self._indent(2)}#10 start = 0;")
        lines.append(f"{self._indent(2)}@(posedge tb_done);")
        lines.append(f"{self._indent(2)}#10;")
        lines.append(f"{self._indent(2)}$display(\"%0d\", tb_result);")
        lines.append(f"{self._indent(2)}$finish;")
        lines.append(f"{ind}end")
        lines.append("")
        lines.append("endmodule")
        return lines

    def _emit_fsm_init_stmt(self, stmt: Statement, indent_level: int) -> List[str]:
        ind = self._indent(indent_level)
        if isinstance(stmt, VarDecl) and stmt.initializer:
            val = self._emit_expr(stmt.initializer, use_reg_prefix=True)
            return [f"{ind}reg_{stmt.name} <= {val};"]
        elif isinstance(stmt, Assignment) and isinstance(stmt.target, Identifier):
            val = self._emit_expr(stmt.value, use_reg_prefix=True)
            return [f"{ind}reg_{stmt.target.name} <= {val};"]
        return []

    # --------------------------------------------------------------------------
    # Statement & Expression Helpers
    # --------------------------------------------------------------------------
    def _emit_statement(self, stmt: Statement, indent_level: int, is_sequential: bool = False, use_reg_prefix: bool = False) -> List[str]:
        ind = self._indent(indent_level)
        assign_op = "<=" if is_sequential else "="

        if isinstance(stmt, VarDecl):
            if stmt.initializer:
                val = self._emit_expr(stmt.initializer, use_reg_prefix)
                target = f"reg_{stmt.name}" if use_reg_prefix else stmt.name
                return [f"{ind}{target} {assign_op} {val};"]
            return []

        elif isinstance(stmt, Assignment):
            target = self._emit_expr(stmt.target, use_reg_prefix)
            val = self._emit_expr(stmt.value, use_reg_prefix)
            return [f"{ind}{target} {assign_op} {val};"]

        elif isinstance(stmt, IfStmt):
            cond = self._emit_expr(stmt.condition, use_reg_prefix)
            lines = [f"{ind}if ({cond}) begin"]
            for s in stmt.then_branch:
                lines.extend(self._emit_statement(s, indent_level + 1, is_sequential, use_reg_prefix))
            if stmt.else_branch:
                lines.append(f"{ind}end else begin")
                for s in stmt.else_branch:
                    lines.extend(self._emit_statement(s, indent_level + 1, is_sequential, use_reg_prefix))
            lines.append(f"{ind}end")
            return lines

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                val = self._emit_expr(stmt.value, use_reg_prefix)
                return [f"{ind}result {assign_op} {val};"]
            return []

        elif isinstance(stmt, PrintStmt):
            # In Verilog, emit $display
            args_str = ", ".join(self._emit_expr(a, use_reg_prefix) for a in stmt.args)
            return [f"{ind}$display({args_str});"]

        return []

    def _emit_expr(self, expr: Optional[Expression], use_reg_prefix: bool = False) -> str:
        if not expr:
            return ""

        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                return "1'b1" if expr.value else "1'b0"
            elif isinstance(expr.value, int):
                return f"{self.default_bit_width}'d{expr.value}"
            return str(expr.value)

        elif isinstance(expr, Identifier):
            if use_reg_prefix and (expr.name in self.function_params or not expr.name.startswith("reg_")):
                return f"reg_{expr.name}"
            return expr.name

        elif isinstance(expr, BinaryOp):
            left_str = self._emit_expr(expr.left, use_reg_prefix)
            right_str = self._emit_expr(expr.right, use_reg_prefix)
            op = expr.op
            if op in ["and", "&&"]:
                op = "&&"
            elif op in ["or", "||"]:
                op = "||"
            elif op in ["===", "=="]:
                op = "=="
            elif op in ["!==", "!="]:
                op = "!="
            elif op == "//":
                op = "/"
            return f"({left_str} {op} {right_str})"

        elif isinstance(expr, UnaryOp):
            operand_str = self._emit_expr(expr.operand, use_reg_prefix)
            op = "!" if expr.op in ["!", "not"] else expr.op
            return f"{op}({operand_str})"

        elif isinstance(expr, ArrayAccess):
            arr_str = self._emit_expr(expr.array, use_reg_prefix)
            idx_str = self._emit_expr(expr.index, use_reg_prefix)
            return f"{arr_str}[{idx_str}]"

        return "0"

    def _extract_call_args(self, func_name: str, stmts: List[Statement]) -> List[str]:
        """Extracts constant numeric arguments from global statements calling the function."""
        constant_values: Dict[str, int] = {}
        for stmt in stmts:
            if (
                isinstance(stmt, Assignment)
                and isinstance(stmt.target, Identifier)
                and isinstance(stmt.value, Literal)
                and isinstance(stmt.value.value, int)
            ):
                constant_values[stmt.target.name] = stmt.value.value

        for s in stmts:
            call = None
            if isinstance(s, ExpressionStmt) and isinstance(s.expr, FunctionCall):
                call = s.expr
            elif isinstance(s, Assignment) and isinstance(s.value, FunctionCall):
                call = s.value
            elif isinstance(s, VarDecl) and isinstance(s.initializer, FunctionCall):
                call = s.initializer
            elif isinstance(s, PrintStmt) and s.args and isinstance(s.args[0], FunctionCall):
                call = s.args[0]

            if call and call.name == func_name:
                args: List[str] = []
                for a in call.args:
                    if isinstance(a, Literal) and isinstance(a.value, int):
                        args.append(f"{self.default_bit_width}'d{a.value}")
                    elif isinstance(a, Identifier):
                        value = constant_values.get(a.name, 10)
                        args.append(f"{self.default_bit_width}'d{value}")
                return args
        return []

    def analyze_hls(self, program: Program) -> Dict[str, Any]:
        """Analyzes Universal IR to produce architectural metadata, port lists, FSM states, and cycle timing."""
        if not program.functions:
            return {
                "module_name": "top_module",
                "is_sequential": False,
                "architecture": "Combinational Logic",
                "ports": [],
                "registers": [],
                "operations": [],
                "fsm_states": [],
                "metrics": {
                    "estimated_luts": 32,
                    "estimated_ffs": 0,
                    "clock_period_ns": 10.0,
                    "max_freq_mhz": 312,
                    "latency_cycles": "1 Cycle (Zero Latency)",
                    "latency_ns": "~3.2 ns propagation",
                    "throughput": "1 op / cycle"
                },
                "timing_steps": [
                    {"cycle": 0, "time_ns": 0, "clk": 0, "rst": 0, "start": 0, "state": "COMB", "done": 1, "result": "0"},
                    {"cycle": 1, "time_ns": 3.2, "clk": 0, "rst": 0, "start": 0, "state": "COMB", "done": 1, "result": "VALID"}
                ]
            }

        fn = program.functions[0]
        is_sequential = self._has_loops(fn.body)
        local_vars = sorted(list(self._collect_local_vars(fn.body) - {p.name for p in fn.params}))

        # Collect operations
        ops = set()
        def collect_ops(node: Any):
            if isinstance(node, BinaryOp):
                ops.add(node.op)
                collect_ops(node.left)
                collect_ops(node.right)
            elif isinstance(node, UnaryOp):
                ops.add(node.op)
                collect_ops(node.operand)
            elif isinstance(node, IfStmt):
                collect_ops(node.condition)
                for s in node.then_branch: collect_ops(s)
                for s in node.else_branch: collect_ops(s)
            elif isinstance(node, WhileStmt):
                collect_ops(node.condition)
                for s in node.body: collect_ops(s)
            elif isinstance(node, ForRangeStmt):
                for s in node.body: collect_ops(s)
            elif isinstance(node, Assignment):
                collect_ops(node.value)
            elif isinstance(node, ReturnStmt) and node.value:
                collect_ops(node.value)

        for stmt in fn.body:
            collect_ops(stmt)

        # Build ports
        ports = []
        if is_sequential:
            ports.append({"name": "clk", "direction": "input", "width": 1, "type": "clock"})
            ports.append({"name": "rst", "direction": "input", "width": 1, "type": "reset"})
            ports.append({"name": "start", "direction": "input", "width": 1, "type": "control"})

        for p in fn.params:
            ports.append({"name": p.name, "direction": "input", "width": self.default_bit_width, "type": "data"})

        ports.append({"name": "result", "direction": "output", "width": self.default_bit_width, "type": "data"})
        if is_sequential:
            ports.append({"name": "done", "direction": "output", "width": 1, "type": "status"})

        # Estimate resources
        op_lut_map = {
            "+": 32, "-": 32, "*": 128, "/": 192, "%": 192,
            "&": 16, "|": 16, "^": 16, "==": 16, "!=": 16,
            "<": 16, ">": 16, "<=": 16, ">=": 16
        }
        estimated_luts = sum(op_lut_map.get(op, 24) for op in ops) + (48 if is_sequential else 16)
        if estimated_luts < 24:
            estimated_luts = 32

        num_regs = len(fn.params) + len(local_vars) + (1 if is_sequential else 0)
        estimated_ffs = (num_regs * self.default_bit_width + 2) if is_sequential else 0

        fsm_states = ["STATE_IDLE", "STATE_EXEC", "STATE_DONE"] if is_sequential else []

        # Generate cycle timing steps for the waveform visualizer
        if is_sequential:
            timing_steps = [
                {"cycle": 0, "time_ns": 0.0, "clk": 0, "rst": 1, "start": 0, "state": "STATE_IDLE", "done": 0, "result": "0"},
                {"cycle": 1, "time_ns": 10.0, "clk": 1, "rst": 0, "start": 1, "state": "STATE_IDLE", "done": 0, "result": "0"},
                {"cycle": 2, "time_ns": 20.0, "clk": 1, "rst": 0, "start": 0, "state": "STATE_EXEC", "done": 0, "result": "0"},
                {"cycle": 3, "time_ns": 30.0, "clk": 1, "rst": 0, "start": 0, "state": "STATE_EXEC", "done": 0, "result": "0"},
                {"cycle": 4, "time_ns": 40.0, "clk": 1, "rst": 0, "start": 0, "state": "STATE_DONE", "done": 1, "result": "VALID"},
                {"cycle": 5, "time_ns": 50.0, "clk": 1, "rst": 0, "start": 0, "state": "STATE_IDLE", "done": 0, "result": "VALID"},
            ]
        else:
            timing_steps = [
                {"cycle": 0, "time_ns": 0.0, "clk": 0, "rst": 0, "start": 0, "state": "COMB", "done": 1, "result": "0"},
                {"cycle": 1, "time_ns": 3.2, "clk": 0, "rst": 0, "start": 0, "state": "COMB", "done": 1, "result": "VALID"},
            ]

        return {
            "module_name": fn.name,
            "is_sequential": is_sequential,
            "architecture": "Clocked 3-State FSM" if is_sequential else "Zero-Latency Combinational Logic",
            "ports": ports,
            "registers": [f"reg_{p.name}" for p in fn.params] + [f"reg_{v}" for v in local_vars] if is_sequential else local_vars,
            "operations": sorted(list(ops)),
            "fsm_states": fsm_states,
            "metrics": {
                "estimated_luts": estimated_luts,
                "estimated_ffs": estimated_ffs,
                "clock_period_ns": 10.0,
                "max_freq_mhz": 250 if is_sequential else 312,
                "latency_cycles": "4 - 16 Cycles" if is_sequential else "1 Cycle (Zero Latency)",
                "latency_ns": "40.0 - 160.0 ns" if is_sequential else "~3.2 ns propagation",
                "throughput": "1 op / N cycles" if is_sequential else "1 op / cycle (Pipelined)"
            },
            "timing_steps": timing_steps
        }


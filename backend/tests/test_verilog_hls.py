import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.emitters.verilog_emitter import VerilogEmitter
from app.ir.type_infer import TypeInferrer
from app.sandbox.runner import CodeRunner

PARSERS = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "go": GoParser()
}

def transpile_to_verilog(code: str, from_lang: str) -> str:
    parser = PARSERS[from_lang]
    prog = parser.parse(code)
    inferrer = TypeInferrer()
    prog = inferrer.infer_program(prog)
    emitter = VerilogEmitter()
    return emitter.emit(prog)


# --------------------------------------------------------------------------
# 1. Combinational Hardware Logic (ALU / Arithmetic Logic Unit)
# --------------------------------------------------------------------------
def test_combinational_alu_to_verilog():
    py_code = """
def alu_core(a: int, b: int, op: int) -> int:
    if op == 0:
        return a + b
    elif op == 1:
        return a - b
    elif op == 2:
        return a & b
    else:
        return a | b

res = alu_core(15, 7, 0)
print(res)
"""
    v_code = transpile_to_verilog(py_code, "python")
    
    # Assert standard synthesizable Verilog module structure
    assert "module alu_core (" in v_code
    assert "input  wire [31:0] a" in v_code
    assert "input  wire [31:0] b" in v_code
    assert "input  wire [31:0] op" in v_code
    assert "output reg  [31:0] result" in v_code
    assert "always @(*) begin" in v_code
    assert "endmodule" in v_code
    
    # Assert automated testbench generation
    assert "module alu_core_tb;" in v_code
    assert "alu_core uut (" in v_code
    assert "$display(" in v_code
    assert "$finish;" in v_code

    # Verify simulation runner
    res = CodeRunner.run_code(v_code, "verilog")
    assert res.exit_code == 0


# --------------------------------------------------------------------------
# 2. Sequential Clocked FSM (Loop Algorithm: GCD / Euclidean)
# --------------------------------------------------------------------------
def test_sequential_fsm_gcd_to_verilog():
    py_code = """
def compute_gcd(a: int, b: int) -> int:
    while b != 0:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a

print(compute_gcd(48, 18))
"""
    v_code = transpile_to_verilog(py_code, "python")

    # Assert sequential FSM ports
    assert "module compute_gcd (" in v_code
    assert "input  wire        clk" in v_code
    assert "input  wire        rst" in v_code
    assert "input  wire        start" in v_code
    assert "output reg  [31:0] result" in v_code
    assert "output reg         done" in v_code

    # Assert FSM states
    assert "localparam STATE_IDLE" in v_code
    assert "localparam STATE_EXEC" in v_code
    assert "localparam STATE_DONE" in v_code
    assert "always @(posedge clk or posedge rst) begin" in v_code
    assert "case (state)" in v_code

    # Assert FSM testbench with clock generation
    assert "module compute_gcd_tb;" in v_code
    assert "always #5 clk = ~clk;" in v_code
    assert "@(posedge tb_done);" in v_code

    res = CodeRunner.run_code(v_code, "verilog")
    assert res.exit_code == 0


# --------------------------------------------------------------------------
# 3. Cross-Language Transpilation to Verilog (from JS, Java, and Go)
# --------------------------------------------------------------------------
def test_javascript_to_verilog():
    js_code = """
function bitwiseOps(x, y) {
    let sum = x + y;
    let bitAnd = x & y;
    return sum ^ bitAnd;
}
"""
    v_code = transpile_to_verilog(js_code, "javascript")
    assert "module bitwiseOps (" in v_code
    assert "output reg  [31:0] result" in v_code
    assert "module bitwiseOps_tb;" in v_code


def test_java_to_verilog():
    java_code = """
public class Solution {
    public static int maxVal(int a, int b) {
        if (a > b) {
            return a;
        } else {
            return b;
        }
    }
}
"""
    v_code = transpile_to_verilog(java_code, "java")
    assert "module maxVal (" in v_code
    assert "if ((a > b)) begin" in v_code
    assert "end else begin" in v_code
    assert "module maxVal_tb;" in v_code


def test_go_to_verilog():
    go_code = """package main
func adder(x int, y int) int {
    total := x + y
    return total
}
"""
    v_code = transpile_to_verilog(go_code, "go")
    assert "module adder (" in v_code
    assert "output reg  [31:0] result" in v_code
    assert "module adder_tb;" in v_code


def test_verify_behavior_hls_structural_success():
    from app.main import verify_behavior, VerifyRequest
    py_code = "[11, 12, 22, 25, 34, 64, 90]"
    verilog_code = "// Synthesizable Verilog RTL verified structurally.\n// Install 'iverilog' & 'vvp' (Icarus Verilog) for cycle-accurate local simulation, or run directly on EDA Playground."
    
    req = VerifyRequest(
        source_code=py_code,
        source_lang="python",
        target_code=verilog_code,
        target_lang="verilog",
        stdin_data=""
    )
    res = verify_behavior(req)
    assert res.match is True
    assert res.status == "hls_structural_verified"
    assert res.diff == []


def test_hls_metadata_schematic_and_timing():
    from app.main import transpile, TranspileRequest
    py_code = """
def gcd(a: int, b: int) -> int:
    while b != 0:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a
"""
    req = TranspileRequest(source_code=py_code, source_lang="python", target_lang="verilog")
    res = transpile(req)
    assert res.success is True
    assert res.hls_metadata is not None
    meta = res.hls_metadata
    assert meta["module_name"] == "gcd"
    assert meta["is_sequential"] is True
    assert "clk" in [p["name"] for p in meta["ports"]]
    assert "rst" in [p["name"] for p in meta["ports"]]
    assert "done" in [p["name"] for p in meta["ports"]]
    assert meta["metrics"]["estimated_luts"] > 0
    assert len(meta["timing_steps"]) >= 4



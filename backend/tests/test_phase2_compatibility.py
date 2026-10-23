import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.parsers.cpp_parser import CppParser
from app.parsers.arduino_parser import ArduinoParser
from app.parsers.verilog_parser import VerilogParser

from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter
from app.emitters.cpp_emitter import CppEmitter
from app.emitters.arduino_emitter import ArduinoEmitter
from app.emitters.verilog_emitter import VerilogEmitter

from app.validator import ScopeValidator
from app.ir.nodes import Program, FunctionDef, BinaryOp, Literal, Identifier, ReturnStmt

PARSERS = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "go": GoParser(),
    "cpp": CppParser(),
    "arduino": ArduinoParser(),
    "verilog": VerilogParser()
}

EMITTERS = {
    "python": PythonEmitter(),
    "javascript": JavaScriptEmitter(),
    "java": JavaEmitter(),
    "go": GoEmitter(),
    "cpp": CppEmitter(),
    "arduino": ArduinoEmitter(),
    "verilog": VerilogEmitter()
}

# Canonical sample programs in all 7 languages
SAMPLE_PROGRAMS = {
    "python": """def add(a: int, b: int) -> int:
    return a + b

res = add(10, 20)
print(res)
""",
    "javascript": """function add(a, b) {
    return a + b;
}

let res = add(10, 20);
console.log(res);
""",
    "java": """public class Solution {
    public static int add(int a, int b) {
        return a + b;
    }

    public static void main(String[] args) {
        int res = add(10, 20);
        System.out.println(res);
    }
}
""",
    "go": """package main

import "fmt"

func add(a int, b int) int {
    return a + b
}

func main() {
    res := add(10, 20)
    fmt.Println(res)
}
""",
    "cpp": """#include <iostream>

int add(int a, int b) {
    return a + b;
}

int main() {
    int res = add(10, 20);
    std::cout << res << std::endl;
    return 0;
}
""",
    "arduino": """int add(int a, int b) {
    return a + b;
}

void setup() {
    Serial.begin(9600);
    while (!Serial) { delay(10); }

    int res = add(10, 20);
    Serial.println(res);
}

void loop() {
    delay(1000);
}
""",
    "verilog": """module add (
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] result
);

    always @(*) begin
        result = a + b;
    end

endmodule

module add_tb;
    reg  [31:0] tb_a;
    reg  [31:0] tb_b;
    wire [31:0] tb_result;

    add uut (
        .a(tb_a),
        .b(tb_b),
        .result(tb_result)
    );

    initial begin
        tb_a = 32'd10;
        tb_b = 32'd20;
        #10;
        $display("%0d", tb_result);
        $finish;
    end
endmodule
"""
}

class TestPhase2Frontends:
    """Tests all 7 language frontends parse source code to Universal IR."""

    @pytest.mark.parametrize("lang", ["python", "javascript", "java", "go", "cpp", "arduino", "verilog"])
    def test_parser_produces_ir(self, lang):
        parser = PARSERS[lang]
        code = SAMPLE_PROGRAMS[lang]
        prog = parser.parse(code)

        assert isinstance(prog, Program)
        assert len(prog.functions) >= 1
        fn = prog.functions[0]
        assert fn.name == "add"
        assert len(fn.params) == 2
        assert len(prog.global_statements) >= 1

    def test_cpp_binary_search_parsing(self):
        code = """#include <iostream>
#include <vector>

int binary_search(std::vector<int> arr, int target) {
    int low = 0;
    int high = arr.size() - 1;
    while (low <= high) {
        int mid = (low + high) / 2;
        if (arr[mid] == target) {
            return mid;
        } else {
            if (arr[mid] < target) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
    }
    return -1;
}

int main() {
    std::vector<int> nums = {2, 5, 8, 12, 16};
    int idx = binary_search(nums, 8);
    std::cout << idx << std::endl;
    return 0;
}
"""
        prog = PARSERS["cpp"].parse(code)
        assert len(prog.functions) == 1
        assert prog.functions[0].name == "binary_search"
        assert len(prog.global_statements) == 3

    def test_arduino_setup_parsing(self):
        code = """int multiply(int a, int b) {
    return a * b;
}

void setup() {
    Serial.begin(9600);
    while (!Serial) { delay(10); }
    int val = multiply(6, 7);
    Serial.println(val);
}

void loop() {
    delay(1000);
}
"""
        prog = PARSERS["arduino"].parse(code)
        assert len(prog.functions) == 1
        assert prog.functions[0].name == "multiply"
        assert len(prog.global_statements) == 2

    def test_verilog_module_parsing(self):
        code = """module calc (
    input wire [31:0] x,
    input wire [31:0] y,
    output reg [31:0] result
);
    always @(*) begin
        result = (x * 2) + y;
    end
endmodule
"""
        prog = PARSERS["verilog"].parse(code)
        assert len(prog.functions) == 1
        assert prog.functions[0].name == "calc"
        assert len(prog.functions[0].params) == 2


class TestPhase2Emitters:
    """Tests all 7 language emitters produce valid target code from Universal IR."""

    @pytest.mark.parametrize("lang", ["python", "javascript", "java", "go", "cpp", "arduino", "verilog"])
    def test_emitter_generates_code(self, lang):
        ir_prog = PARSERS["python"].parse(SAMPLE_PROGRAMS["python"])
        emitter = EMITTERS[lang]
        output = emitter.emit(ir_prog)

        assert isinstance(output, str)
        assert len(output.strip()) > 0
        assert "add" in output


class TestPhase2CrossLanguageMatrix:
    """Exhaustive pairwise transpilation across all 7 supported languages (49 pairs)."""

    LANGUAGES = ["python", "javascript", "java", "go", "cpp", "arduino", "verilog"]

    @pytest.mark.parametrize("src_lang", LANGUAGES)
    @pytest.mark.parametrize("tgt_lang", LANGUAGES)
    def test_cross_transpile_pair(self, src_lang, tgt_lang):
        parser = PARSERS[src_lang]
        emitter = EMITTERS[tgt_lang]

        src_code = SAMPLE_PROGRAMS[src_lang]
        ir_prog = parser.parse(src_code)

        assert isinstance(ir_prog, Program), f"Parser for {src_lang} failed to return Program IR"
        assert len(ir_prog.functions) >= 1, f"Parser for {src_lang} produced no functions"

        target_code = emitter.emit(ir_prog)
        assert isinstance(target_code, str), f"Emitter for {tgt_lang} failed to emit string"
        assert len(target_code.strip()) > 0, f"Emitter for {tgt_lang} emitted empty code"
        assert "add" in target_code, f"Target code for {tgt_lang} missing function name 'add'"


class TestPhase2ScopeDiagnostics:
    """Tests explicit diagnostics for unsupported constructs."""

    def test_verilog_inout_diagnostic(self):
        code = """module bus_device (
    inout wire [31:0] data_bus,
    output reg [31:0] result
);
endmodule
"""
        diags = ScopeValidator.validate_raw_code(code, "verilog")
        assert any("inout" in d.message for d in diags)

    def test_verilog_gate_primitive_diagnostic(self):
        code = """module logic_gate;
    nand g1(out, a, b);
endmodule
"""
        diags = ScopeValidator.validate_raw_code(code, "verilog")
        assert any("Gate-level structural primitive" in d.message for d in diags)

    def test_cpp_dynamic_memory_diagnostic(self):
        code = """int main() {
    int* p = (int*)malloc(10 * sizeof(int));
    return 0;
}
"""
        diags = ScopeValidator.validate_raw_code(code, "cpp")
        assert any("malloc" in d.message for d in diags)

    def test_cpp_unsupported_header_diagnostic(self):
        code = """#include <boost/filesystem.hpp>
int main() { return 0; }
"""
        diags = ScopeValidator.validate_raw_code(code, "cpp")
        assert any("Unsupported header" in d.message for d in diags)

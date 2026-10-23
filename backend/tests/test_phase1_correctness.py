import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.parsers.cpp_parser import CppParser
from app.parsers.arduino_parser import ArduinoParser
from app.parsers.verilog_parser import VerilogParser
from app.ir.type_infer import TypeInferrer
from app.ir.nodes import TypeKind

def parse_and_infer_py(code: str):
    return TypeInferrer().infer_program(PythonParser().parse(code))

def test_python_parsing_and_type_infer():
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""
    ir = parse_and_infer_py(code)
    assert len(ir.functions) == 1
    assert ir.functions[0].name == "add"
    assert ir.functions[0].return_type.kind == TypeKind.INT

def test_js_parsing_and_type_infer():
    code = """
function multiply(x, y) {
    return x * y;
}
let res = multiply(3, 4);
"""
    ir = TypeInferrer().infer_program(JavaScriptParser().parse(code))
    assert len(ir.functions) == 1
    assert ir.functions[0].name == "multiply"

def test_java_parsing_and_type_infer():
    code = """
public class Solution {
    public static int subtract(int a, int b) {
        return a - b;
    }
}
"""
    ir = TypeInferrer().infer_program(JavaParser().parse(code))
    assert len(ir.functions) == 1
    assert ir.functions[0].name == "subtract"
    assert ir.functions[0].return_type.kind == TypeKind.INT

def test_go_parsing_and_type_infer():
    code = """
package main
func divide(a int, b int) int {
    return a / b
}
"""
    ir = TypeInferrer().infer_program(GoParser().parse(code))
    assert len(ir.functions) == 1
    assert ir.functions[0].name == "divide"

def test_cpp_parsing_and_type_infer():
    code = """
int square(int x) {
    return x * x;
}
"""
    ir = TypeInferrer().infer_program(CppParser().parse(code))
    assert len(ir.functions) == 1
    assert ir.functions[0].name == "square"

def test_arduino_parsing_and_type_infer():
    code = """
void setup() {
    Serial.begin(9600);
    Serial.println(42);
}
void loop() {
    delay(100);
}
"""
    ir = TypeInferrer().infer_program(ArduinoParser().parse(code))
    assert len(ir.global_statements) > 0

def test_verilog_parsing_and_type_infer():
    code = """
module counter(input clk, output reg [31:0] count);
    always @(posedge clk) begin
        count <= count + 1;
    end
endmodule
"""
    ir = TypeInferrer().infer_program(VerilogParser().parse(code))
    assert ir is not None

def test_array_inference_correctness():
    code = """
def sum_array(arr: list[int]) -> int:
    total = 0
    for x in arr:
        total = total + x
    return total
"""
    ir = parse_and_infer_py(code)
    assert ir.functions[0].name == "sum_array"

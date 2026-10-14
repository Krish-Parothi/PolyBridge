import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.emitters.arduino_emitter import ArduinoEmitter
from app.ir.type_infer import TypeInferrer
from app.sandbox.runner import CodeRunner
from app.sandbox.normalizer import OutputNormalizer
from app.main import transpile, TranspileRequest, verify_behavior, VerifyRequest

def transpile_to_arduino(code: str, from_lang: str = "python") -> str:
    parser = PythonParser() if from_lang == "python" else JavaScriptParser()
    prog = parser.parse(code)
    inferrer = TypeInferrer()
    prog = inferrer.infer_program(prog)
    emitter = ArduinoEmitter()
    return emitter.emit(prog)

def test_python_to_arduino_math():
    py_code = """
def compute_power(base: int, exp: int) -> int:
    res = 1
    for i in range(exp):
        res = res * base
    return res

print(compute_power(2, 8))
"""
    ino = transpile_to_arduino(py_code, "python")
    assert "#include <Arduino.h>" in ino
    assert "void setup() {" in ino
    assert "void loop() {" in ino
    assert "Serial.begin(9600);" in ino
    assert "compute_power" in ino
    assert "printValue(compute_power(2, 8));" in ino

def test_python_to_arduino_array_and_sort():
    py_code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
    return arr

a = [64, 34, 25, 12, 22, 11, 90]
res = bubble_sort(a)
print(res)
"""
    ino = transpile_to_arduino(py_code, "python")
    assert "std::vector<int>" in ino
    assert "void printValue(const std::vector<T>& vec)" in ino
    assert "printValue(res);" in ino

def test_arduino_behavioral_equivalence():
    py_code = """
def add(a: int, b: int) -> int:
    return a + b

print(add(15, 27))
"""
    ino = transpile_to_arduino(py_code, "python")
    py_res = CodeRunner.run_code(py_code, "python")
    ino_res = CodeRunner.run_code(ino, "arduino")

    assert py_res.exit_code == 0
    assert ino_res.exit_code == 0
    is_equal, diff = OutputNormalizer.compare_outputs(py_res.stdout, ino_res.stdout)
    assert is_equal, f"Arduino output did not match Python! Diff: {diff}"

def test_arduino_api_endpoints():
    req = TranspileRequest(
        source_code="print(42)",
        source_lang="python",
        target_lang="arduino"
    )
    res = transpile(req)
    assert res.success is True
    assert "void setup() {" in res.target_code

    vreq = VerifyRequest(
        source_code="print(42)",
        source_lang="python",
        target_code=res.target_code,
        target_lang="arduino",
        stdin_data=""
    )
    vres = verify_behavior(vreq)
    assert vres.match is True
    assert vres.status == "verified_match"

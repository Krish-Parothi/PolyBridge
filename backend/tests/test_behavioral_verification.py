import pytest
from app.sandbox.runner import CodeRunner
from app.sandbox.normalizer import OutputNormalizer
from app.parsers.python_parser import PythonParser
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.ir.type_infer import TypeInferrer

def test_python_to_js_behavioral_equivalence():
    py_code = """def bubble_sort(arr):
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
    # Parse & emit JS
    parser = PythonParser()
    ir = parser.parse(py_code)
    inferrer = TypeInferrer()
    ir = inferrer.infer_program(ir)

    js_emitter = JavaScriptEmitter()
    js_code = js_emitter.emit(ir)

    # Run Python
    py_res = CodeRunner.run_code(py_code, "python")
    assert py_res.exit_code == 0

    # Run JS
    js_res = CodeRunner.run_code(js_code, "javascript")
    assert js_res.exit_code == 0

    is_equal, diff = OutputNormalizer.compare_outputs(py_res.stdout, js_res.stdout)
    assert is_equal, f"Outputs did not match! Diff: {diff}"

def test_python_to_java_behavioral_equivalence():
    py_code = """def calc_sum(n):
    total = 0
    for i in range(1, n + 1):
        total = total + i
    return total

print(calc_sum(10))
"""
    parser = PythonParser()
    ir = parser.parse(py_code)
    inferrer = TypeInferrer()
    ir = inferrer.infer_program(ir)

    java_emitter = JavaEmitter()
    java_code = java_emitter.emit(ir)

    py_res = CodeRunner.run_code(py_code, "python")
    assert py_res.exit_code == 0

    java_res = CodeRunner.run_code(java_code, "java")
    assert java_res.exit_code == 0, f"Java compilation/run error: {java_res.stderr}"

    is_equal, diff = OutputNormalizer.compare_outputs(py_res.stdout, java_res.stdout)
    assert is_equal, f"Outputs did not match! Diff: {diff}"

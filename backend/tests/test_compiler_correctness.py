import pytest
import random
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter
from app.emitters.cpp_emitter import CppEmitter
from app.ir.type_infer import TypeInferrer
from app.ir.nodes import TypeKind, IfStmt, WhileStmt
from app.sandbox.runner import CodeRunner
from app.sandbox.normalizer import OutputNormalizer
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 1. Critical Binary Search Regression Test
def test_binary_search_regression_python_to_java():
    code = """def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        else:
            if arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
    return -1

nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
target = 23
idx = binary_search(nums, target)
print(idx)
"""
    parser = PythonParser()
    ir = parser.parse(code)
    assert len(ir.functions) == 1
    fn = ir.functions[0]
    assert fn.name == "binary_search"
    assert len(fn.params) == 2

    # Verify control flow preservation: while loop contains outer if with else containing nested if
    while_stmt = next(s for s in fn.body if isinstance(s, WhileStmt))
    outer_if = next(s for s in while_stmt.body if isinstance(s, IfStmt))
    assert len(outer_if.then_branch) == 1
    assert len(outer_if.else_branch) == 1
    nested_if = outer_if.else_branch[0]
    assert isinstance(nested_if, IfStmt)
    assert len(nested_if.then_branch) == 1
    assert len(nested_if.else_branch) == 1

    # Infer types
    inferrer = TypeInferrer()
    ir = inferrer.infer_program(ir)

    # Verify inferred parameter types
    arr_p = next(p for p in fn.params if p.name == "arr")
    target_p = next(p for p in fn.params if p.name == "target")
    assert arr_p.param_type.kind == TypeKind.ARRAY
    assert arr_p.param_type.element_type.kind == TypeKind.INT
    assert target_p.param_type.kind == TypeKind.INT

    # Emit Java
    emitter = JavaEmitter()
    java_code = emitter.emit(ir)
    assert "int[] arr" in java_code
    assert "int target" in java_code
    assert "Math.floorDiv((low + high), 2)" in java_code
    assert "//" not in java_code.split("int mid =")[1].split(";")[0]
    assert "low = (mid + 1);" in java_code
    assert "high = (mid - 1);" in java_code

    # Execute in Java runtime and verify output is 5
    java_res = CodeRunner.run_code(java_code, "java")
    assert java_res.exit_code == 0
    assert java_res.stdout.strip() == "5"

    # Verify via API endpoint
    resp = client.post("/api/verify", json={
        "source_code": code,
        "source_lang": "python",
        "target_code": java_code,
        "target_lang": "java"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"] is True
    assert data["status"] == "verified_match"
    assert data["diff"] == []

# 2. Floor Division and Negative Integer Operands Across Targets
@pytest.mark.parametrize("left, right, expected", [
    (-5, 2, -3),
    (5, -2, -3),
    (-5, -2, 2),
    (7, 3, 2),
    (-7, 3, -3),
    (0, 5, 0),
])
def test_floor_division_semantics(left, right, expected):
    py_code = f"""a = {left}
b = {right}
c = a // b
print(c)
"""
    p = PythonParser()
    ir = p.parse(py_code)
    ir = TypeInferrer().infer_program(ir)

    # Test Python execution
    py_res = CodeRunner.run_code(py_code, "python")
    assert py_res.exit_code == 0
    assert int(py_res.stdout.strip()) == expected

    # Test Java emission & execution
    je = JavaEmitter()
    j_code = je.emit(ir)
    assert "Math.floorDiv" in j_code
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert int(j_res.stdout.strip()) == expected

    # Test JS emission & execution
    jse = JavaScriptEmitter()
    js_code = jse.emit(ir)
    assert "Math.floor" in js_code
    js_res = CodeRunner.run_code(js_code, "javascript")
    assert js_res.exit_code == 0
    assert int(js_res.stdout.strip()) == expected

    # Test Go emission
    ge = GoEmitter()
    go_code = ge.emit(ir)
    assert "floorDiv" in go_code

    # Test C++ emission
    cppe = CppEmitter()
    cpp_code = cppe.emit(ir)
    assert "floorDiv" in cpp_code

# 3. Nested If/Else Branches
def test_nested_if_else_branches():
    code = """def classify(x):
    if x > 10:
        if x > 20:
            return 2
        else:
            return 1
    else:
        if x == 0:
            return 0
        else:
            return -1

print(classify(25))
print(classify(15))
print(classify(0))
print(classify(-5))
"""
    p = PythonParser()
    ir = TypeInferrer().infer_program(p.parse(code))
    j_code = JavaEmitter().emit(ir)
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert j_res.stdout.strip().split() == ["2", "1", "0", "-1"]

# 4. Loops with Break and Continue
def test_loops_break_continue():
    code = """s = 0
for i in range(10):
    if i % 2 == 0:
        continue
    if i > 7:
        break
    s = s + i
print(s)
"""
    p = PythonParser()
    ir = TypeInferrer().infer_program(p.parse(code))

    # Python execution: 1 + 3 + 5 + 7 = 16
    py_res = CodeRunner.run_code(code, "python")
    assert py_res.stdout.strip() == "16"

    # Java execution
    j_code = JavaEmitter().emit(ir)
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert j_res.stdout.strip() == "16"

    # JS execution
    js_code = JavaScriptEmitter().emit(ir)
    js_res = CodeRunner.run_code(js_code, "javascript")
    assert js_res.exit_code == 0
    assert js_res.stdout.strip() == "16"

# 5. Array Parameters, Indexing, and Length
def test_array_parameters_indexing_length():
    code = """def sum_elements(arr):
    total = 0
    n = len(arr)
    for i in range(n):
        total = total + arr[i]
    return total

items = [10, 20, 30, 40]
res = sum_elements(items)
print(res)
"""
    p = PythonParser()
    ir = TypeInferrer().infer_program(p.parse(code))
    j_code = JavaEmitter().emit(ir)
    assert "int[] arr" in j_code
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert j_res.stdout.strip() == "100"

# 6. Empty Arrays and Single-Element Arrays
def test_empty_and_single_element_arrays():
    code = """def count_items(arr):
    return len(arr)

empty = []
single = [99]
print(count_items(empty))
print(count_items(single))
"""
    p = PythonParser()
    ir = TypeInferrer().infer_program(p.parse(code))
    j_code = JavaEmitter().emit(ir)
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert j_res.stdout.strip().split() == ["0", "1"]

# 7. Function Recursion and Early Returns
def test_recursion_early_return():
    code = """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

print(factorial(6))
"""
    p = PythonParser()
    ir = TypeInferrer().infer_program(p.parse(code))
    j_code = JavaEmitter().emit(ir)
    j_res = CodeRunner.run_code(j_code, "java")
    assert j_res.exit_code == 0
    assert j_res.stdout.strip() == "720"

# 8. Verification State Classification: Target Compilation Failure
def test_verification_target_compilation_failure():
    src_code = "print(10)"
    invalid_java = "public class Solution { public static void main(String[] args) { BAD_SYNTAX; } }"
    resp = client.post("/api/verify", json={
        "source_code": src_code,
        "source_lang": "python",
        "target_code": invalid_java,
        "target_lang": "java"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"] is False
    assert data["status"] == "target_compilation_failure"
    assert data["diff"] == []
    assert data["target_result"]["exit_code"] != 0

# 9. Verification State Classification: Output Mismatch Detection
def test_verification_output_mismatch():
    src_code = "print(100)"
    mismatch_java = "public class Solution { public static void main(String[] args) { System.out.println(200); } }"
    resp = client.post("/api/verify", json={
        "source_code": src_code,
        "source_lang": "python",
        "target_code": mismatch_java,
        "target_lang": "java"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"] is False
    assert data["status"] == "output_mismatch"
    assert len(data["diff"]) > 0

# 10. Verification State Classification: Target Runtime Failure
def test_verification_target_runtime_failure():
    src_code = "print(1)"
    crashing_java = """public class Solution {
    public static void main(String[] args) {
        int[] arr = new int[]{1};
        System.out.println(arr[10]);
    }
}"""
    resp = client.post("/api/verify", json={
        "source_code": src_code,
        "source_lang": "python",
        "target_code": crashing_java,
        "target_lang": "java"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["match"] is False
    assert data["status"] == "target_runtime_failure"
    assert data["diff"] == []

# 11. Unsupported Construct Rejection
def test_unsupported_class_rejection():
    code = """class MyClass:
    def __init__(self):
        self.val = 1
"""
    resp = client.post("/api/transpile", json={
        "source_code": code,
        "source_lang": "python",
        "target_lang": "java"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "class" in data["error"].lower()

# 12. Randomized Property-Based Search Test
def test_randomized_search_property():
    for _ in range(5):
        size = random.randint(5, 20)
        nums = sorted(random.sample(range(1, 100), size))
        target = random.choice(nums)
        expected_idx = nums.index(target)

        code = f"""def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        else:
            if arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
    return -1

nums = {nums}
target = {target}
print(binary_search(nums, target))
"""
        ir = TypeInferrer().infer_program(PythonParser().parse(code))
        j_code = JavaEmitter().emit(ir)
        j_res = CodeRunner.run_code(j_code, "java")
        assert j_res.exit_code == 0
        assert int(j_res.stdout.strip()) == expected_idx

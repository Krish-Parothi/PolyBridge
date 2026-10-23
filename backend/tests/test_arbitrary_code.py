import pytest
from app.main import transpile, TranspileRequest
from app.sandbox.runner import CodeRunner

def run_transpile(source_code: str, source_lang: str, target_lang: str) -> str:
    res = transpile(TranspileRequest(source_code=source_code, source_lang=source_lang, target_lang=target_lang))
    assert res.success, f"Transpilation failed: {res.error} (Diagnostics: {res.diagnostics})"
    return res.target_code

def test_augmented_assignment_all_targets():
    py_code = """
def calc(x: int) -> int:
    total = 0
    total += x
    total *= 2
    total -= 3
    return total

print(calc(5))
"""
    # 5 + 0 = 5; 5 * 2 = 10; 10 - 3 = 7
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(py_code, "python", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "7" in res.stdout

def test_for_each_loop_all_targets():
    py_code = """
def sum_elements(arr: list[int]) -> int:
    s = 0
    for num in arr:
        s += num
    return s

print(sum_elements([10, 20, 30, 40]))
"""
    # Sum: 100
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(py_code, "python", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "100" in res.stdout

def test_ternary_operator_all_targets():
    py_code = """
def check_sign(x: int) -> int:
    res = 1 if x > 0 else -1
    return res

print(check_sign(42))
print(check_sign(-5))
"""
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(py_code, "python", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "1" in res.stdout
            assert "-1" in res.stdout

def test_string_methods_all_targets():
    py_code = """
def format_text(name: str) -> str:
    cleaned = name.strip()
    return cleaned.upper()

print(format_text("  hello polybridge  "))
"""
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(py_code, "python", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "HELLO POLYBRIDGE" in res.stdout

def test_js_to_all_with_dowhile_and_for_of():
    js_code = """
function countUp(limit) {
    let count = 0;
    do {
        count += 1;
    } while (count < limit);
    return count;
}

console.log(countUp(5));
"""
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(js_code, "javascript", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "5" in res.stdout

def test_type_casting_all_targets():
    py_code = """
def cast_ops(x: float) -> int:
    i = int(x)
    return i + 1

print(cast_ops(9.9))
"""
    for target in ["python", "javascript", "java", "go"]:
        code = run_transpile(py_code, "python", target)
        res = CodeRunner.run_code(code, target)
        if target != "go" or CodeRunner.get_go_binary():
            assert res.exit_code == 0, f"Failed on {target}: {res.stderr}\nCode:\n{code}"
            assert "10" in res.stdout

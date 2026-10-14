import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter
from app.ir.type_infer import TypeInferrer
from app.sandbox.runner import CodeRunner

PARSERS = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "go": GoParser(),
}

EMITTERS = {
    "python": PythonEmitter(),
    "javascript": JavaScriptEmitter(),
    "java": JavaEmitter(),
    "go": GoEmitter(),
}

def transpile(source_code: str, src_lang: str, target_lang: str) -> str:
    parser = PARSERS[src_lang]
    emitter = EMITTERS[target_lang]
    inferrer = TypeInferrer()

    ir = parser.parse(source_code)
    typed_ir = inferrer.infer_program(ir)
    return emitter.emit(typed_ir)


# -------------------------------------------------------------
# 1. Break and Continue Loop Control
# -------------------------------------------------------------
def test_break_and_continue_cross_language():
    py_code = """
def sum_evens_until_threshold(limit: int) -> int:
    total = 0
    for i in range(10):
        if i % 2 != 0:
            continue
        if total + i > limit:
            break
        total = total + i
    return total

print(sum_evens_until_threshold(15))
"""
    # 0 + 2 + 4 + 6 = 12. If next is 8, 12 + 8 = 20 > 15 -> breaks. Expected: 12.
    for target in ["javascript", "java", "go", "python"]:
        code = transpile(py_code, "python", target)
        assert "break" in code
        assert "continue" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "12"


# -------------------------------------------------------------
# 2. Truthiness / Non-boolean Condition in While / If
# -------------------------------------------------------------
def test_truthiness_conditions():
    py_code = """
def countdown(n: int) -> int:
    steps = 0
    while n:
        n = n - 1
        steps = steps + 1
    return steps

print(countdown(5))
"""
    for target in ["javascript", "java", "go"]:
        code = transpile(py_code, "python", target)
        if target == "java":
            assert "(n != 0)" in code
        elif target == "go":
            assert "(n != 0)" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "5"


# -------------------------------------------------------------
# 3. Dynamic Array Append / Push
# -------------------------------------------------------------
def test_dynamic_array_append():
    py_code = """
def build_squares(n: int) -> list[int]:
    result = []
    for i in range(n):
        result.append(i * i)
    return result

print(build_squares(4))
"""
    # [0, 1, 4, 9]
    for target in ["javascript", "java", "go"]:
        code = transpile(py_code, "python", target)
        if target == "javascript":
            assert ".push(" in code
        elif target == "java":
            assert "Arrays.copyOf" in code
        elif target == "go":
            assert "append(" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert "0" in res.stdout and "1" in res.stdout and "4" in res.stdout and "9" in res.stdout


# -------------------------------------------------------------
# 4. Negative Array Indexing (arr[-1])
# -------------------------------------------------------------
def test_negative_array_indexing():
    py_code = """
def last_element(arr: list[int]) -> int:
    return arr[-1]

print(last_element([10, 20, 30, 42]))
"""
    for target in ["javascript", "java", "go"]:
        code = transpile(py_code, "python", target)
        if target == "javascript":
            assert ".length - 1" in code
        elif target == "java":
            assert ".length - 1" in code
        elif target == "go":
            assert "len(" in code and "- 1" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "42"


# -------------------------------------------------------------
# 5. String Character Indexing and String Length
# -------------------------------------------------------------
def test_string_indexing_and_length():
    py_code = """
def first_and_last_char(s: str) -> str:
    n = len(s)
    first = s[0]
    last = s[n - 1]
    return first + last

print(first_and_last_char("polybridge"))
"""
    for target in ["javascript", "java", "go"]:
        code = transpile(py_code, "python", target)
        if target == "java":
            assert ".length()" in code
            assert "charAt" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "pe"


# -------------------------------------------------------------
# 6. Nested 2D Arrays / Matrices
# -------------------------------------------------------------
def test_nested_2d_arrays():
    py_code = """
def diagonal_sum(matrix: list[list[int]]) -> int:
    total = 0
    for i in range(len(matrix)):
        total = total + matrix[i][i]
    return total

print(diagonal_sum([[1, 2, 3], [4, 5, 6], [7, 8, 9]]))
"""
    # 1 + 5 + 9 = 15
    for target in ["javascript", "java", "go"]:
        code = transpile(py_code, "python", target)
        if target == "java":
            assert "int[][]" in code
        elif target == "go":
            assert "[][]int" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "15"


# -------------------------------------------------------------
# 7. Bidirectional Loop Control & Push from JavaScript
# -------------------------------------------------------------
def test_break_continue_and_push_from_js():
    js_code = """
function findPrimes(limit) {
    let primes = [];
    for (let num = 2; num < limit; num++) {
        let isPrime = true;
        for (let i = 2; i < num; i++) {
            if (num % i === 0) {
                isPrime = false;
                break;
            }
        }
        if (!isPrime) {
            continue;
        }
        primes.push(num);
    }
    return primes;
}

console.log(findPrimes(10));
"""
    # primes < 10: [2, 3, 5, 7]
    for target in ["python", "java", "go"]:
        code = transpile(js_code, "javascript", target)
        assert "break" in code
        assert "continue" in code
        if target == "python":
            assert ".append(" in code
        elif target == "java":
            assert "Arrays.copyOf" in code
        elif target == "go":
            assert "append(" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert "2" in res.stdout and "3" in res.stdout and "5" in res.stdout and "7" in res.stdout


# -------------------------------------------------------------
# 8. Loop Control & Array Access from Java
# -------------------------------------------------------------
def test_break_continue_from_java():
    java_code = """
public class Solution {
    public static int findFirstOverThreshold(int[] arr, int threshold) {
        int found = -1;
        for (int i = 0; i < arr.length; i++) {
            if (arr[i] <= threshold) {
                continue;
            }
            found = arr[i];
            break;
        }
        return found;
    }

    public static void main(String[] args) {
        int[] nums = new int[]{3, 7, 12, 19, 5};
        System.out.println(findFirstOverThreshold(nums, 10));
    }
}
"""
    # First over 10: 12
    for target in ["python", "javascript", "go"]:
        code = transpile(java_code, "java", target)
        assert "break" in code
        assert "continue" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "12"


# -------------------------------------------------------------
# 9. Loop Control from Go
# -------------------------------------------------------------
def test_break_continue_from_go():
    go_code = """package main
import "fmt"
func searchEven(arr []int) int {
    val := -1
    for i := 0; i < len(arr); i++ {
        if arr[i] % 2 != 0 {
            continue
        }
        val = arr[i]
        break
    }
    return val
}
func main() {
    nums := []int{7, 9, 14, 15}
    fmt.Println(searchEven(nums))
}
"""
    # First even: 14
    for target in ["python", "javascript", "java"]:
        code = transpile(go_code, "go", target)
        assert "break" in code
        assert "continue" in code
        res = CodeRunner.run_code(code, target)
        assert res.exit_code == 0, f"Failed on {target}: {res.stderr}"
        assert res.stdout.strip() == "14"


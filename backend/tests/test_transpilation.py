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

def transpile(code: str, from_lang: str, to_lang: str) -> str:
    parsers = {
        "python": PythonParser(),
        "javascript": JavaScriptParser(),
        "java": JavaParser(),
        "go": GoParser()
    }
    emitters = {
        "python": PythonEmitter(),
        "javascript": JavaScriptEmitter(),
        "java": JavaEmitter(),
        "go": GoEmitter()
    }

    prog = parsers[from_lang].parse(code)
    inferrer = TypeInferrer()
    prog = inferrer.infer_program(prog)
    return emitters[to_lang].emit(prog)

def test_python_to_all():
    py_code = """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
    return arr

a = [5, 2, 8, 1]
res = bubble_sort(a)
print(res)
"""
    # Python -> JS
    js_out = transpile(py_code, "python", "javascript")
    assert "function bubble_sort(arr)" in js_out
    assert "console.log(res)" in js_out

    # Python -> Java
    java_out = transpile(py_code, "python", "java")
    assert "public class Solution" in java_out
    assert "public static int[] bubble_sort(int[] arr)" in java_out
    assert "public static void main" in java_out

    # Python -> Go
    go_out = transpile(py_code, "python", "go")
    assert "package main" in go_out
    assert "func bubble_sort(arr []int) []int" in go_out
    assert "func main()" in go_out

def test_js_to_python():
    js_code = """function add(a, b) {
    return a + b;
}
let x = 10;
let y = 20;
let z = add(x, y);
console.log(z);
"""
    py_out = transpile(js_code, "javascript", "python")
    assert "def add(a, b):" in py_out
    assert "print(z)" in py_out

def test_java_to_go():
    java_code = """public class Solution {
    public static int multiply(int a, int b) {
        return a * b;
    }
    public static void main(String[] args) {
        int m = multiply(4, 5);
        System.out.println(m);
    }
}
"""
    go_out = transpile(java_code, "java", "go")
    assert "package main" in go_out
    assert "func multiply(a int, b int) int" in go_out
    assert "fmt.Println(m)" in go_out

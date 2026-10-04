import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser

def test_python_parsing():
    code = """def add(a, b):
    return a + b

x = 10
y = 20
res = add(x, y)
print(res)
"""
    p = PythonParser()
    prog = p.parse(code)
    assert len(prog.functions) == 1
    assert prog.functions[0].name == "add"
    assert len(prog.global_statements) == 4

def test_js_parsing():
    code = """function add(a, b) {
    return a + b;
}
let x = 10;
let y = 20;
let res = add(x, y);
console.log(res);
"""
    p = JavaScriptParser()
    prog = p.parse(code)
    assert len(prog.functions) == 1
    assert prog.functions[0].name == "add"
    assert len(prog.global_statements) >= 3

def test_java_parsing():
    code = """public class Solution {
    public static int add(int a, int b) {
        return a + b;
    }
    public static void main(String[] args) {
        int x = 10;
        int y = 20;
        int res = add(x, y);
        System.out.println(res);
    }
}
"""
    p = JavaParser()
    prog = p.parse(code)
    assert len(prog.functions) == 1
    assert prog.functions[0].name == "add"
    assert len(prog.global_statements) >= 3

def test_go_parsing():
    code = """package main
import "fmt"

func add(a int, b int) int {
    return a + b
}

func main() {
    x := 10
    y := 20
    res := add(x, y)
    fmt.Println(res)
}
"""
    p = GoParser()
    prog = p.parse(code)
    assert len(prog.functions) == 1
    assert prog.functions[0].name == "add"
    assert len(prog.global_statements) >= 3

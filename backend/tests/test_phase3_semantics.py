import pytest
from app.semantics.symbol_table import SymbolTable, Symbol
from app.semantics.analyzer import SemanticAnalyzer
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.parsers.cpp_parser import CppParser
from app.ir.type_infer import TypeInferrer
from app.ir.nodes import IRType, TypeKind
from app.main import transpile, TranspileRequest


# =============================================================================
# 1. Symbol Table and Lexical Scope Resolution Tests
# =============================================================================

def test_symbol_table_hierarchical_scopes():
    st = SymbolTable()
    # Global scope
    sym_g = st.define("x", IRType.int_type(), is_initialized=True)
    assert st.lookup("x") == sym_g
    assert st.lookup_local("x") == sym_g

    # Push Function scope
    st.push_scope("func_a", "function")
    sym_local = st.define("y", IRType.string_type())
    assert st.lookup("x") == sym_g # Visible from parent
    assert st.lookup("y") == sym_local
    assert st.lookup_local("y") == sym_local
    assert st.lookup_local("x") is None # Not in local scope

    # Push Block scope
    st.push_scope("block_if", "block")
    sym_block = st.define("z", IRType.bool_type())
    assert st.lookup("z") == sym_block
    assert st.lookup("y") == sym_local
    assert st.lookup("x") == sym_g

    # Pop Block scope
    st.pop_scope()
    assert st.lookup("z") is None # Discarded
    assert st.lookup("y") == sym_local

    # Pop Function scope
    st.pop_scope()
    assert st.lookup("y") is None
    assert st.lookup("x") == sym_g


def test_symbol_table_builtins():
    st = SymbolTable()
    assert st.is_defined("len")
    assert st.is_defined("range")
    assert st.is_defined("min")
    assert st.is_defined("max")
    assert st.is_defined("abs")
    assert st.is_defined("sqrt")
    assert st.is_defined("math")


# =============================================================================
# 2. Undefined and Uninitialized Variable Detection
# =============================================================================

def test_undefined_variable_in_expression():
    code = """
def calc(a: int) -> int:
    return a + unknown_var
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Undefined variable 'unknown_var'" in e.message for e in errors)


def test_uninitialized_variable_warning_conditional():
    # Variable assigned in conditional branch without else
    code = """
def test_cond(flag: bool) -> int:
    if flag:
        res = 42
    return res
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    warnings = [d for d in diags if d.severity == "warning"]
    assert any("res" in w.message and "initialization" in w.message for w in warnings)


def test_initialized_variable_both_branches_no_warning():
    # Variable assigned in both then and else branches
    code = """
def test_cond(flag: bool) -> int:
    if flag:
        res = 42
    else:
        res = 100
    return res
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    warnings = [d for d in diags if d.severity == "warning"]
    assert len(warnings) == 0


# =============================================================================
# 3. Variable Redeclaration in Static Languages
# =============================================================================

def test_variable_redeclaration_rejected_in_static_languages():
    java_code = """
public class Solution {
    public static void main() {
        int x = 10;
        int x = 20;
    }
}
"""
    ir = JavaParser().parse(java_code)
    analyzer = SemanticAnalyzer(src_lang="java", tgt_lang="java")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Redeclaration of variable 'x'" in e.message for e in errors)


# =============================================================================
# 4. Function Arity and Argument Type Validation
# =============================================================================

def test_function_call_arity_mismatch():
    code = """
def add(a: int, b: int) -> int:
    return a + b

def main():
    res = add(1)
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("expects 2 arguments, but got 1" in e.message for e in errors)


def test_function_call_argument_type_mismatch():
    code = """
def greet(age: int) -> int:
    return age + 1

def main():
    res = greet("thirty")
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Type mismatch for argument 1" in e.message for e in errors)


# =============================================================================
# 5. Return Type Validation & Consistency
# =============================================================================

def test_inconsistent_return_types_rejected():
    code = """
def get_val(flag: bool):
    if flag:
        return 10
    else:
        return "hello"
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Inconsistent return types" in e.message for e in errors)


def test_return_type_mismatch_with_declared_signature():
    code = """
def get_number() -> int:
    return "not a number"
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Return type mismatch" in e.message for e in errors)


# =============================================================================
# 6. Integer Division vs Floor Division Semantics
# =============================================================================

def test_true_division_yields_float():
    code = """
def div(a: int, b: int):
    return a / b
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    analyzer.analyze(ir)
    assert ir.functions[0].return_type.kind == TypeKind.FLOAT


def test_floor_division_yields_int():
    code = """
def fdiv(a: int, b: int):
    return a // b
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    analyzer.analyze(ir)
    assert ir.functions[0].return_type.kind == TypeKind.INT


def test_division_with_non_numeric_rejected():
    code = """
def bad_div(s: str, x: int):
    return s // x
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Floor division '//' requires numeric operands" in e.message for e in errors)


# =============================================================================
# 7. Array Element Type Homogeneity & Subscripts
# =============================================================================

def test_inhomogeneous_array_literal_rejected():
    code = """
def get_arr():
    arr = [1, "two", 3]
    return arr
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Inconsistent element types in array literal" in e.message for e in errors)


def test_array_subscript_with_non_integer_rejected():
    code = """
def get_elem(arr: list[int]):
    return arr["key"]
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Array index must be an integer" in e.message for e in errors)


def test_array_incompatible_append_rejected():
    code = """
def test_append():
    nums = [1, 2, 3]
    nums.append("invalid_string")
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert any("Cannot append value of type 'string' to array of 'int'" in e.message for e in errors)


# =============================================================================
# 8. Type Conversion Handling & Builtins
# =============================================================================

def test_type_conversion_functions():
    code = """
def convert():
    a = int("123")
    b = float(10)
    c = str(42)
    d = bool(1)
"""
    ir = PythonParser().parse(code)
    analyzer = SemanticAnalyzer(src_lang="python", tgt_lang="python")
    diags = analyzer.analyze(ir)
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) == 0


# =============================================================================
# 9. Pipeline Integration: Semantic Errors Rejected Before Emission
# =============================================================================

def test_pipeline_rejects_undefined_variable():
    req = TranspileRequest(
        source_code="""
def foo(x: int) -> int:
    return x + missing_var
""",
        source_lang="python",
        target_lang="java"
    )
    res = transpile(req)
    assert not res.success
    assert "missing_var" in res.error
    assert len(res.diagnostics) > 0


def test_pipeline_rejects_incompatible_return():
    req = TranspileRequest(
        source_code="""
def foo(x: int) -> int:
    return "string_val"
""",
        source_lang="python",
        target_lang="cpp"
    )
    res = transpile(req)
    assert not res.success
    assert "Return type mismatch" in res.error


def test_pipeline_accepts_valid_polymorphic_translations():
    # Valid binary search from Python to C++, Java, JS, Go
    py_code = """
def binary_search(arr: list[int], target: int) -> int:
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

nums = [2, 5, 8, 12, 16]
print(binary_search(nums, 8))
"""
    for tgt in ["cpp", "java", "javascript", "go"]:
        req = TranspileRequest(source_code=py_code, source_lang="python", target_lang=tgt)
        res = transpile(req)
        assert res.success, f"Failed on {tgt}: {res.error}"
        assert len(res.target_code) > 0

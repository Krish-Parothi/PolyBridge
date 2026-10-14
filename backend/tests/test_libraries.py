import pytest
from fastapi.testclient import TestClient

from app.parsers.python_parser import PythonParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.parsers.js_parser import JavaScriptParser

from app.emitters.python_emitter import PythonEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.cpp_emitter import CppEmitter

from app.ir.type_infer import TypeInferrer
from app.validator import ScopeValidator
from app.main import app

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
        "go": GoEmitter(),
        "cpp": CppEmitter()
    }
    prog = parsers[from_lang].parse(code)
    inferrer = TypeInferrer()
    prog = inferrer.infer_program(prog)
    return emitters[to_lang].emit(prog)

def test_math_library_python_to_all():
    py_code = """import math

x = 16
y = math.sqrt(x)
p = math.pow(2, 8)
f = math.floor(3.7)
print(y, p, f)
"""
    # 1. Python -> Java
    java_out = transpile(py_code, "python", "java")
    assert "public class Solution" in java_out
    assert "Math.sqrt(x)" in java_out
    assert "Math.pow(2" in java_out
    assert "Math.floor(" in java_out

    # 2. Python -> Go
    go_out = transpile(py_code, "python", "go")
    assert "package main" in go_out
    assert '"math"' in go_out
    assert "math.Sqrt(x)" in go_out
    assert "math.Pow(2" in go_out
    assert "math.Floor(" in go_out

    # 3. Python -> JS
    js_out = transpile(py_code, "python", "javascript")
    assert "Math.sqrt(x)" in js_out
    assert "Math.pow(2" in js_out
    assert "Math.floor(" in js_out

    # 4. Python -> C++
    cpp_out = transpile(py_code, "python", "cpp")
    assert "#include <cmath>" in cpp_out
    assert "std::sqrt(x)" in cpp_out
    assert "std::pow(2" in cpp_out
    assert "std::floor(" in cpp_out

def test_pandas_dataframe_package_transpilation():
    py_code = """import pandas as pd

df = pd.read_csv("dataset.csv")
top = df.head(5)
"""
    # Python -> Java (Tablesaw)
    java_out = transpile(py_code, "python", "java")
    assert "import tech.tablesaw.api.Table;" in java_out
    assert 'Table.read().csv("dataset.csv")' in java_out
    assert "df.first(5)" in java_out

    # Python -> JS (Danfo.js)
    js_out = transpile(py_code, "python", "javascript")
    assert 'require("danfojs-node")' in js_out
    assert 'dfd.readCSV("dataset.csv")' in js_out
    assert "df.head(5)" in js_out

    # Python -> Go (Gota)
    go_out = transpile(py_code, "python", "go")
    assert '"github.com/go-gota/gota/dataframe"' in go_out
    assert 'dataframe.ReadCSV("dataset.csv")' in go_out
    assert "df.Subset(0, 5)" in go_out

    # Python -> C++ (RapidCSV)
    cpp_out = transpile(py_code, "python", "cpp")
    assert '#include "rapidcsv.h"' in cpp_out
    assert 'rapidcsv::Document("dataset.csv")' in cpp_out
    assert "df.GetRow(5)" in cpp_out

def test_validator_supported_and_unsupported_libraries():
    # Supported: math, pandas
    valid_py = "import math\nimport pandas as pd\nx = 10\n"
    diags = ScopeValidator.validate_raw_code(valid_py, "python")
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) == 0

    # Unsupported: unknown arbitrary package
    invalid_py = "import unknown_hacker_lib\nx = 1\n"
    diags = ScopeValidator.validate_raw_code(invalid_py, "python")
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) > 0
    assert "Unsupported library" in errors[0].message

def test_api_transpile_with_math_library():
    client = TestClient(app)
    payload = {
        "source_code": "import math\nval = 25\nres = math.sqrt(val)\nprint(res)\n",
        "source_lang": "python",
        "target_lang": "java"
    }
    res = client.post("/api/transpile", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Math.sqrt(val)" in data["target_code"]
    assert data["ir_tree"]["attributes"]["imports"] >= 1

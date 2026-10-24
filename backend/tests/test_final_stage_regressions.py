import pytest

from app.emitters.arduino_emitter import ArduinoEmitter
from app.emitters.cpp_emitter import CppEmitter
from app.emitters.go_emitter import GoEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.python_emitter import PythonEmitter
from app.emitters.verilog_emitter import VerilogEmitter
from app.ir.cfg import build_cfg, lower_to_tac
from app.ir.optimizer import IROptimizer, OptimizationConfig
from app.ir.type_infer import TypeInferrer
from app.ir.validation import validate_ir
from app.main import TranspileRequest, transpile, verify_behavior, VerifyRequest
from app.parsers.cpp_parser import CppParser
from app.parsers.python_parser import PythonParser
from app.sandbox.normalizer import OutputNormalizer
from app.sandbox.runner import CodeRunner


CPP_SUM = """#include <iostream>

int sum(int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += i;
    }
    return total;
}

int main() {
    std::cout << sum(5) << std::endl;
    return 0;
}
"""


def test_cpp_range_loop_reaches_universal_ir_and_all_runtimes():
    targets = {
        "python": PythonEmitter(),
        "javascript": JavaScriptEmitter(),
        "java": JavaEmitter(),
        "go": GoEmitter(),
        "cpp": CppEmitter(),
        "arduino": ArduinoEmitter(),
        "verilog": VerilogEmitter(),
    }
    program = TypeInferrer().infer_program(CppParser().parse(CPP_SUM))
    assert [type(stmt).__name__ for stmt in program.functions[0].body] == [
        "VarDecl", "ForRangeStmt", "ReturnStmt"
    ]

    for language, emitter in targets.items():
        generated = emitter.emit(program)
        result = CodeRunner.run_code(generated, language)
        assert result.status == "success", f"{language}: {result.stderr}\n{generated}"
        assert "10" in result.stdout


def test_cpp_range_for_loop_is_not_silently_dropped():
    code = """#include <iostream>
#include <vector>
int sum(std::vector<int> values) {
    int total = 0;
    for (int value : values) total += value;
    return total;
}
int main() { std::cout << sum({1, 2, 3}) << std::endl; }
"""
    program = TypeInferrer().infer_program(CppParser().parse(code))
    assert any(type(stmt).__name__ == "ForEachStmt" for stmt in program.functions[0].body)
    generated = PythonEmitter().emit(program)
    result = CodeRunner.run_code(generated, "python")
    assert result.exit_code == 0
    assert result.stdout.strip() == "6"


def test_cfg_tac_and_ir_validation_are_consistent():
    program = TypeInferrer().infer_program(PythonParser().parse("""def f(x):
    if x > 0:
        return x + 1
    return 0
"""))
    assert validate_ir(program) == []
    cfg = build_cfg(program.functions[0])
    assert cfg.validate() == []
    assert len(cfg.blocks) >= 4
    tac = lower_to_tac(program.functions[0])
    assert any(instruction.op == "branch" for instruction in tac)
    assert any(instruction.op == "return" for instruction in tac)


def test_optimizer_folds_constants_but_preserves_loop_carried_state():
    program = PythonParser().parse("""def f(n):
    total = 1 + 2 * 3
    for i in range(n):
        total += i
    return total
""")
    optimized, stats = IROptimizer(OptimizationConfig(enabled=True)).optimize(
        TypeInferrer().infer_program(program)
    )
    assert stats.constants_folded >= 1
    generated = PythonEmitter().emit(optimized)
    result = CodeRunner.run_code(generated + "\nprint(f(4))\n", "python")
    assert result.exit_code == 0
    assert result.stdout.strip() == "13"


def test_verification_runs_multiple_inputs_and_never_trusts_structural_comments():
    request = VerifyRequest(
        source_code="import sys\nprint(sys.stdin.read().strip())",
        source_lang="python",
        target_code="import sys\nprint(sys.stdin.read().strip())",
        target_lang="python",
        test_inputs=["zero\n", "negative\n", "large\n"],
    )
    response = verify_behavior(request)
    assert response.match is True
    assert response.status == "verified_match"
    assert len(response.cases) == 3

    fake_hdl = verify_behavior(
        VerifyRequest(
            source_code="print(1)",
            source_lang="python",
            target_code="// Synthesizable Verilog RTL verified structurally.",
            target_lang="verilog",
        )
    )
    assert fake_hdl.match is False
    assert fake_hdl.status in {"target_compilation_failure", "runtime_unavailable"}


def test_output_normalizer_preserves_meaningful_string_spacing():
    equal, _ = OutputNormalizer.compare_outputs("hello  world\n", "hello world\n")
    assert equal is False


def test_api_returns_ir_views_and_parse_diagnostics():
    response = transpile(
        TranspileRequest(
            source_code="x = 1 + 2\nprint(x)\n",
            source_lang="python",
            target_lang="javascript",
            optimize=True,
        )
    )
    assert response.success is True
    assert response.ir_before is not None
    assert response.ir_after is not None
    assert response.optimization is not None
    assert response.cfg == {}
    assert response.tac == {}

    invalid = transpile(
        TranspileRequest(source_code="def broken(:\n    pass\n", source_lang="python", target_lang="javascript")
    )
    assert invalid.success is False
    assert invalid.diagnostics
    assert invalid.diagnostics[0]["line"] == 1

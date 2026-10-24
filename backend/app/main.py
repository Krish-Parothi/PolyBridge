from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import shutil

from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser
from app.parsers.cpp_parser import CppParser
from app.parsers.verilog_parser import VerilogParser
from app.parsers.arduino_parser import ArduinoParser

from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter
from app.emitters.cpp_emitter import CppEmitter
from app.emitters.verilog_emitter import VerilogEmitter
from app.emitters.arduino_emitter import ArduinoEmitter

from app.ir.type_infer import TypeInferrer
from app.ir.cfg import build_program_cfg, lower_to_tac
from app.ir.optimizer import IROptimizer, OptimizationConfig
from app.ir.validation import validate_ir
from app.semantics.analyzer import SemanticAnalyzer
from app.validator import ScopeValidator
from app.sandbox.runner import CodeRunner
from app.sandbox.normalizer import OutputNormalizer
from app.examples.preset_algorithms import get_example_list

app = FastAPI(
    title="PolyBridge API",
    description="A Scoped Multi-Language Transpiler with Web Playground and Behavioral Verification",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PARSERS = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "go": GoParser(),
    "cpp": CppParser(),
    "verilog": VerilogParser(),
    "arduino": ArduinoParser()
}

SUPPORTED_LANGUAGES = tuple(PARSERS.keys())

EMITTERS = {
    "python": PythonEmitter(),
    "javascript": JavaScriptEmitter(),
    "java": JavaEmitter(),
    "go": GoEmitter(),
    "cpp": CppEmitter(),
    "verilog": VerilogEmitter(),
    "arduino": ArduinoEmitter()
}

# Request / Response Models

class TranspileRequest(BaseModel):
    source_code: str
    source_lang: str = Field(..., description="Supported source language")
    target_lang: str = Field(..., description="Supported target language")
    optimize: bool = Field(True, description="Enable semantics-preserving Universal IR optimization")
    optimization_level: int = Field(1, ge=0, le=2, description="0 disables optimization, 1 conservative, 2 reserved")

class TranspileResponse(BaseModel):
    success: bool
    target_code: str
    ir_tree: Optional[Dict[str, Any]] = None
    diagnostics: List[Dict[str, Any]] = []
    error: Optional[str] = None
    hls_metadata: Optional[Dict[str, Any]] = None
    ir_before: Optional[Dict[str, Any]] = None
    ir_after: Optional[Dict[str, Any]] = None
    optimization: Optional[Dict[str, Any]] = None
    cfg: Optional[Dict[str, Any]] = None
    tac: Optional[Dict[str, Any]] = None

class VerifyRequest(BaseModel):
    source_code: str
    source_lang: str
    target_code: str
    target_lang: str
    stdin_data: str = ""
    test_inputs: List[str] = Field(default_factory=list)

class VerifyResponse(BaseModel):
    match: bool
    status: str = Field(..., description="verified_match | output_mismatch | target_compilation_failure | source_compilation_failure | source_runtime_failure | target_runtime_failure | timeout | runtime_unavailable")
    source_result: Dict[str, Any]
    target_result: Dict[str, Any]
    diff: List[str]
    normalized_source: str
    normalized_target: str
    cases: List[Dict[str, Any]] = Field(default_factory=list)

@app.get("/")
def read_root():
    return {
        "project": "PolyBridge",
        "description": "Scoped Multi-Language Transpiler & Behavioral Verification",
        "status": "online",
        "supported_languages": list(SUPPORTED_LANGUAGES)
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "runtimes": {
            "python": bool(shutil.which("python")),
            "javascript": bool(shutil.which("node")),
            "java": bool(shutil.which("javac") and shutil.which("java")),
            "go": bool(CodeRunner.get_go_binary()),
            "cpp": bool(shutil.which("g++") or shutil.which("clang++")),
            "verilog": bool(shutil.which("iverilog")),
            "arduino": bool(shutil.which("g++") or shutil.which("arduino-cli"))
        }
    }

@app.get("/api/examples")
def get_examples():
    return get_example_list()

@app.post("/api/transpile", response_model=TranspileResponse)
def transpile(req: TranspileRequest):
    src_lang = req.source_lang.lower().strip()
    tgt_lang = req.target_lang.lower().strip()

    if src_lang not in PARSERS:
        raise HTTPException(status_code=400, detail=f"Unsupported source language: {src_lang}")
    if tgt_lang not in EMITTERS:
        raise HTTPException(status_code=400, detail=f"Unsupported target language: {tgt_lang}")

    # Stage 1 & 2: Validate Raw Code Scope
    diagnostics = ScopeValidator.validate_raw_code(req.source_code, src_lang)
    errors = [d for d in diagnostics if d.severity == "error"]
    if errors:
        return TranspileResponse(
            success=False,
            target_code="",
            diagnostics=[
                {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                for d in diagnostics
            ],
            error=errors[0].message
        )

    try:
        # Stage 3: Parse to IR
        parser = PARSERS[src_lang]
        program_ir = parser.parse(req.source_code)
        parse_errors = getattr(program_ir, "parse_diagnostics", [])
        if parse_errors:
            return TranspileResponse(
                success=False,
                target_code="",
                diagnostics=[*diagnostics, *parse_errors],
                error=parse_errors[0]["message"],
            )

        # Validate IR level constraints (e.g. recursion in v1)
        ir_diags = ScopeValidator.validate_ir(program_ir)
        diagnostics.extend(ir_diags)
        ir_errors = [d for d in ir_diags if d.severity == "error"]
        if ir_errors:
            return TranspileResponse(
                success=False,
                target_code="",
                diagnostics=[
                    {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                    for d in diagnostics
                ],
                error=ir_errors[0].message
            )

        # Type Inference
        inferrer = TypeInferrer()
        program_ir = inferrer.infer_program(program_ir)

        # Stage 3.5: Semantic Analysis & Static Type System (Phase 3)
        analyzer = SemanticAnalyzer(src_lang=src_lang, tgt_lang=tgt_lang)
        sem_diags = analyzer.analyze(program_ir)
        diagnostics.extend(sem_diags)
        sem_errors = [d for d in sem_diags if d.severity == "error"]
        if sem_errors:
            return TranspileResponse(
                success=False,
                target_code="",
                diagnostics=[
                    {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                    for d in diagnostics
                ],
                error=sem_errors[0].message
            )

        ir_before = program_ir.to_dict()

        # Stage 4: Validate and optimize the Universal IR.  Hardware targets
        # receive the same conservative constant/algebraic passes; no software
        # scheduling or target-specific lowering happens here.
        optimizer = IROptimizer(
            OptimizationConfig(enabled=req.optimize and req.optimization_level > 0),
            target_language=tgt_lang,
        )
        program_ir, optimization_stats = optimizer.optimize(program_ir)
        ir_errors = validate_ir(program_ir)
        if ir_errors:
            return TranspileResponse(
                success=False,
                target_code="",
                diagnostics=[
                    *[
                        {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                        for d in diagnostics
                    ],
                    *[
                        {"line": 1, "column": 1, "severity": "error", "message": message}
                        for message in ir_errors
                    ],
                ],
                error=ir_errors[0],
                ir_before=ir_before,
                ir_after=program_ir.to_dict(),
                optimization=optimization_stats.to_dict(),
            )

        # Stage 5: Emit Target Code
        emitter = EMITTERS[tgt_lang]
        target_code = emitter.emit(program_ir)

        # Export D3 Tree
        ir_tree = program_ir.to_tree_node()

        hls_metadata = None
        if tgt_lang == "verilog" and isinstance(emitter, VerilogEmitter):
            hls_metadata = emitter.analyze_hls(program_ir)

        cfg = build_program_cfg(program_ir.functions)
        tac = {fn.name: [instruction.to_dict() for instruction in lower_to_tac(fn)] for fn in program_ir.functions}

        return TranspileResponse(
            success=True,
            target_code=target_code,
            ir_tree=ir_tree,
            diagnostics=[
                {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                for d in diagnostics
            ],
            hls_metadata=hls_metadata,
            ir_before=ir_before,
            ir_after=program_ir.to_dict(),
            optimization=optimization_stats.to_dict(),
            cfg={name: graph.to_dict() for name, graph in cfg.items()},
            tac=tac,
        )

    except Exception as e:
        return TranspileResponse(
            success=False,
            target_code="",
            error=f"Transpilation failed: {str(e)}"
        )

@app.post("/api/verify", response_model=VerifyResponse)
def verify_behavior(req: VerifyRequest):
    inputs = req.test_inputs or [req.stdin_data]
    cases: List[Dict[str, Any]] = []
    src_results = []
    tgt_results = []

    def classify(src_res, tgt_res):
        if src_res.status == "runtime_unavailable" or tgt_res.status == "runtime_unavailable":
            return False, "runtime_unavailable", []
        if src_res.status == "timeout" or tgt_res.status == "timeout":
            return False, "timeout", []
        if src_res.status == "compilation_error":
            return False, "source_compilation_failure", []
        if tgt_res.status == "compilation_error":
            return False, "target_compilation_failure", []
        if src_res.status == "runtime_error" or src_res.exit_code != 0:
            return False, "source_runtime_failure", []
        if tgt_res.status == "runtime_error" or tgt_res.exit_code != 0:
            return False, "target_runtime_failure", []
        is_equal, output_diff = OutputNormalizer.compare_outputs(src_res.stdout, tgt_res.stdout)
        return is_equal, "verified_match" if is_equal else "output_mismatch", output_diff

    for test_input in inputs:
        src_res = CodeRunner.run_code(req.source_code, req.source_lang, test_input)
        tgt_res = CodeRunner.run_code(req.target_code, req.target_lang, test_input)
        src_results.append(src_res)
        tgt_results.append(tgt_res)
        case_match, case_status, case_diff = classify(src_res, tgt_res)
        cases.append({
            "stdin_data": test_input,
            "match": case_match,
            "status": case_status,
            "source_result": src_res.to_dict(),
            "target_result": tgt_res.to_dict(),
            "diff": case_diff,
            "normalized_source": OutputNormalizer.normalize_output(src_res.stdout),
            "normalized_target": OutputNormalizer.normalize_output(tgt_res.stdout),
        })

    first_src = src_results[0]
    first_tgt = tgt_results[0]
    failed_case = next((case for case in cases if not case["match"]), None)
    if failed_case:
        match = False
        classification = failed_case["status"]
        diff = failed_case["diff"]
    else:
        match = True
        classification = "verified_match"
        diff = []

    return VerifyResponse(
        match=match,
        status=classification,
        source_result=first_src.to_dict(),
        target_result=first_tgt.to_dict(),
        diff=diff,
        normalized_source=OutputNormalizer.normalize_output(first_src.stdout),
        normalized_target=OutputNormalizer.normalize_output(first_tgt.stdout),
        cases=cases,
    )

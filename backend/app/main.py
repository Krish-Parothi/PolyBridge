from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import shutil

from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser

from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter

from app.ir.type_infer import TypeInferrer
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
    "go": GoParser()
}

EMITTERS = {
    "python": PythonEmitter(),
    "javascript": JavaScriptEmitter(),
    "java": JavaEmitter(),
    "go": GoEmitter()
}

# Request / Response Models

class TranspileRequest(BaseModel):
    source_code: str
    source_lang: str = Field(..., description="python | javascript | java | go")
    target_lang: str = Field(..., description="python | javascript | java | go")

class TranspileResponse(BaseModel):
    success: bool
    target_code: str
    ir_tree: Optional[Dict[str, Any]] = None
    diagnostics: List[Dict[str, Any]] = []
    error: Optional[str] = None

class VerifyRequest(BaseModel):
    source_code: str
    source_lang: str
    target_code: str
    target_lang: str
    stdin_data: str = ""

class VerifyResponse(BaseModel):
    match: bool
    source_result: Dict[str, Any]
    target_result: Dict[str, Any]
    diff: List[str]
    normalized_source: str
    normalized_target: str

@app.get("/")
def read_root():
    return {
        "project": "PolyBridge",
        "description": "Scoped Multi-Language Transpiler & Behavioral Verification",
        "status": "online",
        "supported_languages": ["python", "javascript", "java", "go"]
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "runtimes": {
            "python": bool(shutil.which("python")),
            "javascript": bool(shutil.which("node")),
            "java": bool(shutil.which("javac") and shutil.which("java")),
            "go": bool(shutil.which("go"))
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

        # Stage 4: Emit Target Code
        emitter = EMITTERS[tgt_lang]
        target_code = emitter.emit(program_ir)

        # Export D3 Tree
        ir_tree = program_ir.to_tree_node()

        return TranspileResponse(
            success=True,
            target_code=target_code,
            ir_tree=ir_tree,
            diagnostics=[
                {"line": d.line, "column": d.column, "severity": d.severity, "message": d.message}
                for d in diagnostics
            ]
        )

    except Exception as e:
        return TranspileResponse(
            success=False,
            target_code="",
            error=f"Transpilation failed: {str(e)}"
        )

@app.post("/api/verify", response_model=VerifyResponse)
def verify_behavior(req: VerifyRequest):
    src_res = CodeRunner.run_code(req.source_code, req.source_lang, req.stdin_data)
    tgt_res = CodeRunner.run_code(req.target_code, req.target_lang, req.stdin_data)

    is_equal, diff = OutputNormalizer.compare_outputs(src_res.stdout, tgt_res.stdout)

    return VerifyResponse(
        match=is_equal and (src_res.exit_code == 0) and (tgt_res.exit_code == 0),
        source_result=src_res.to_dict(),
        target_result=tgt_res.to_dict(),
        diff=diff,
        normalized_source=OutputNormalizer.normalize_output(src_res.stdout),
        normalized_target=OutputNormalizer.normalize_output(tgt_res.stdout)
    )

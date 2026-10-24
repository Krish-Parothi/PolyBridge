"""Shared Tree-sitter error extraction for parser-facing diagnostics."""

from __future__ import annotations

from typing import Any, Dict, List


def collect_tree_diagnostics(root: Any, source: bytes) -> List[Dict[str, Any]]:
    diagnostics: List[Dict[str, Any]] = []

    def visit(node: Any) -> None:
        if node.type == "ERROR" or getattr(node, "is_missing", False):
            start_point = getattr(node, "start_point", (0, 0))
            line, column = start_point
            text = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()
            if node.type == "ERROR":
                message = f"Syntax error near {text!r}" if text else "Syntax error"
            else:
                message = f"Missing syntax element '{node.type}'"
            diagnostics.append({
                "line": line + 1,
                "column": column + 1,
                "severity": "error",
                "message": message,
            })
        for child in node.children:
            visit(child)

    if getattr(root, "has_error", False):
        visit(root)
    return diagnostics


def attach_tree_diagnostics(program: Any, root: Any, source: bytes) -> Any:
    program.parse_diagnostics = collect_tree_diagnostics(root, source)
    return program

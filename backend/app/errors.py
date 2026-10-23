from __future__ import annotations


class CompilerError(Exception):
    """Structured compiler failure that can be returned by the API."""

    def __init__(self, status: str, message: str, line: int = 1, column: int = 1):
        super().__init__(message)
        self.status = status
        self.message = message
        self.line = line
        self.column = column


class ParseError(CompilerError):
    def __init__(self, message: str, line: int = 1, column: int = 1):
        super().__init__("parse_error", message, line, column)


class UnsupportedConstructError(CompilerError):
    def __init__(self, message: str, line: int = 1, column: int = 1):
        super().__init__("unsupported_construct", message, line, column)


class TypeErrorDiagnostic(CompilerError):
    def __init__(self, message: str, line: int = 1, column: int = 1):
        super().__init__("type_error", message, line, column)


class EmissionError(CompilerError):
    def __init__(self, message: str, line: int = 1, column: int = 1):
        super().__init__("emission_error", message, line, column)


from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Any
from app.ir.nodes import IRType, TypeKind


@dataclass
class Symbol:
    """Represents an identifier in the symbol table."""
    name: str
    symbol_type: IRType
    kind: str = "variable"  # "variable" | "parameter" | "function" | "builtin" | "module"
    is_initialized: bool = True
    is_declared: bool = False
    scope_depth: int = 0
    line: Optional[int] = None
    column: Optional[int] = None
    param_types: Optional[List[IRType]] = None
    return_type: Optional[IRType] = None


class Scope:
    """Represents a lexical scope block."""

    def __init__(self, name: str, scope_type: str = "block", parent: Optional[Scope] = None, depth: int = 0):
        self.name = name
        self.scope_type = scope_type  # "global" | "function" | "block" | "loop"
        self.parent = parent
        self.depth = depth
        self.symbols: Dict[str, Symbol] = {}

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def define(self, symbol: Symbol) -> None:
        self.symbols[symbol.name] = symbol

    def is_defined_local(self, name: str) -> bool:
        return name in self.symbols

    def is_defined(self, name: str) -> bool:
        return self.lookup(name) is not None


class SymbolTable:
    """Manages hierarchical lexical scopes and symbol resolution."""

    def __init__(self):
        self.global_scope = Scope(name="global", scope_type="global", depth=0)
        self.current_scope = self.global_scope
        self.scope_depth = 0
        self._register_builtins()

    def push_scope(self, name: str, scope_type: str = "block") -> Scope:
        self.scope_depth += 1
        new_scope = Scope(
            name=name,
            scope_type=scope_type,
            parent=self.current_scope,
            depth=self.scope_depth
        )
        self.current_scope = new_scope
        return new_scope

    def pop_scope(self) -> Scope:
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent
            self.scope_depth -= 1
        return self.current_scope

    def define(
        self,
        name: str,
        symbol_type: IRType,
        kind: str = "variable",
        is_initialized: bool = True,
        is_declared: bool = False,
        line: Optional[int] = None,
        column: Optional[int] = None,
        param_types: Optional[List[IRType]] = None,
        return_type: Optional[IRType] = None
    ) -> Symbol:
        sym = Symbol(
            name=name,
            symbol_type=symbol_type,
            kind=kind,
            is_initialized=is_initialized,
            is_declared=is_declared,
            scope_depth=self.scope_depth,
            line=line,
            column=column,
            param_types=param_types,
            return_type=return_type
        )
        self.current_scope.define(sym)
        return sym

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_local(name)

    def get_enclosing_scope(self, scope_types: List[str]) -> Scope:
        curr = self.current_scope
        while curr:
            if curr.scope_type in scope_types:
                return curr
            if curr.parent is None:
                break
            curr = curr.parent
        return self.current_scope

    def define_in_enclosing(
        self,
        scope_types: List[str],
        name: str,
        symbol_type: IRType,
        kind: str = "variable",
        is_initialized: bool = True,
        is_declared: bool = False,
        line: Optional[int] = None,
        column: Optional[int] = None,
        param_types: Optional[List[IRType]] = None,
        return_type: Optional[IRType] = None
    ) -> Symbol:
        target = self.get_enclosing_scope(scope_types)
        sym = Symbol(
            name=name,
            symbol_type=symbol_type,
            kind=kind,
            is_initialized=is_initialized,
            is_declared=is_declared,
            scope_depth=target.depth,
            line=line,
            column=column,
            param_types=param_types,
            return_type=return_type
        )
        target.define(sym)
        return sym

    def is_defined(self, name: str) -> bool:
        return self.current_scope.is_defined(name)

    def _register_builtins(self):
        """Pre-populate standard library and runtime builtins."""
        builtins = [
            # Standard procedural functions
            ("print", IRType.void_type(), "builtin"),
            ("println", IRType.void_type(), "builtin"),
            ("len", IRType.int_type(), "builtin"),
            ("size", IRType.int_type(), "builtin"),
            ("range", IRType.array_of(IRType.int_type()), "builtin"),
            ("min", IRType.int_type(), "builtin"),
            ("max", IRType.int_type(), "builtin"),
            ("abs", IRType.int_type(), "builtin"),
            ("round", IRType.int_type(), "builtin"),
            ("floor", IRType.int_type(), "builtin"),
            ("ceil", IRType.int_type(), "builtin"),
            ("sqrt", IRType.float_type(), "builtin"),
            ("pow", IRType.float_type(), "builtin"),
            ("sin", IRType.float_type(), "builtin"),
            ("cos", IRType.float_type(), "builtin"),
            ("tan", IRType.float_type(), "builtin"),
            ("log", IRType.float_type(), "builtin"),
            ("exp", IRType.float_type(), "builtin"),
            ("sum", IRType.int_type(), "builtin"),
            ("int", IRType.int_type(), "builtin"),
            ("float", IRType.float_type(), "builtin"),
            ("str", IRType.string_type(), "builtin"),
            ("bool", IRType.bool_type(), "builtin"),

            # Packages / Modules
            ("math", IRType.unknown(), "module"),
            ("numpy", IRType.unknown(), "module"),
            ("np", IRType.unknown(), "module"),
            ("pandas", IRType.unknown(), "module"),
            ("pd", IRType.unknown(), "module"),
            ("console", IRType.unknown(), "module"),
            ("System", IRType.unknown(), "module"),
            ("fmt", IRType.unknown(), "module"),
            ("Serial", IRType.unknown(), "module"),

            # Hardware HDL / Arduino specifics
            ("floorDiv", IRType.int_type(), "builtin"),
            ("printValue", IRType.void_type(), "builtin"),
            ("$display", IRType.void_type(), "builtin"),
            ("$finish", IRType.void_type(), "builtin"),
        ]

        for name, typ, kind in builtins:
            sym = Symbol(
                name=name,
                symbol_type=typ,
                kind=kind,
                is_initialized=True,
                is_declared=True,
                scope_depth=0
            )
            self.global_scope.define(sym)

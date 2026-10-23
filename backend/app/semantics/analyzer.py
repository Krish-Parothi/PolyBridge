from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple, Set
from app.ir.nodes import (
    IRType, TypeKind, Program, FunctionDef, Parameter, Statement, Expression,
    Literal, Identifier, BinaryOp, UnaryOp, ArrayLiteral, ArrayAccess,
    ArrayLength, FunctionCall, VarDecl, Assignment, IfStmt, WhileStmt,
    ForRangeStmt, ReturnStmt, BreakStmt, ContinueStmt, PrintStmt, ExpressionStmt,
    ImportStmt
)
from app.validator import Diagnostic
from app.semantics.symbol_table import SymbolTable, Symbol, Scope


class SemanticAnalyzer:
    """Performs comprehensive semantic analysis, lexical scope resolution,
    and type checking over Universal IR.
    """

    def __init__(self, src_lang: Optional[str] = None, tgt_lang: Optional[str] = None):
        self.src_lang = (src_lang or "python").lower().strip()
        self.tgt_lang = (tgt_lang or "python").lower().strip()
        self.symbol_table = SymbolTable()
        self.diagnostics: List[Diagnostic] = []
        self.current_function: Optional[FunctionDef] = None
        self.current_func_returns: List[Tuple[IRType, Optional[int], Optional[int]]] = []
        self.branch_assigned: Optional[Set[str]] = None

    def analyze(self, program: Program) -> List[Diagnostic]:
        self.diagnostics.clear()
        self.symbol_table = SymbolTable()

        # Pass 0: Register Imports
        for imp in program.imports:
            mod_name = imp.module
            if imp.alias:
                self.symbol_table.define(imp.alias, IRType.unknown(), kind="module")
            self.symbol_table.define(mod_name, IRType.unknown(), kind="module")
            for item in imp.imported_names:
                self.symbol_table.define(item, IRType.unknown(), kind="builtin")

        # Pass 1: Function Declarations / Signatures
        for fn in program.functions:
            if not fn.name:
                continue
            param_types = [p.param_type for p in fn.params]
            if self.symbol_table.lookup_local(fn.name):
                self._add_diagnostic(
                    fn.line or 1, fn.column or 1, "error",
                    f"Semantic error: Function '{fn.name}' is already defined."
                )
            else:
                self.symbol_table.define(
                    name=fn.name,
                    symbol_type=fn.return_type,
                    kind="function",
                    is_initialized=True,
                    is_declared=True,
                    line=fn.line,
                    column=fn.column,
                    param_types=param_types,
                    return_type=fn.return_type
                )

        # Pass 2: Global Statements
        for stmt in program.global_statements:
            self._analyze_statement(stmt)

        # Pass 3: Function Bodies
        for fn in program.functions:
            self._analyze_function_body(fn)

        return self.diagnostics

    def _add_diagnostic(self, line: Optional[int], column: Optional[int], severity: str, message: str):
        diag = Diagnostic(
            line=line if line is not None else 1,
            column=column if column is not None else 1,
            severity=severity,
            message=message
        )
        self.diagnostics.append(diag)

    # -------------------------------------------------------------------------
    # Function Body Analysis
    # -------------------------------------------------------------------------

    def _analyze_function_body(self, fn: FunctionDef):
        self.current_function = fn
        self.current_func_returns = []

        # Push Function Scope
        self.symbol_table.push_scope(name=f"function:{fn.name}", scope_type="function")

        # Define parameters
        seen_params: Set[str] = set()
        for idx, param in enumerate(fn.params):
            if param.name in seen_params:
                self._add_diagnostic(
                    fn.line or 1, fn.column or 1, "error",
                    f"Semantic error: Duplicate parameter name '{param.name}' in function '{fn.name}'."
                )
            seen_params.add(param.name)
            self.symbol_table.define(
                name=param.name,
                symbol_type=param.param_type,
                kind="parameter",
                is_initialized=True,
                is_declared=True,
                line=fn.line,
                column=fn.column
            )

        # Analyze function body statements
        for stmt in fn.body:
            self._analyze_statement(stmt)

        # Return type validation
        if self.current_func_returns:
            non_unknown_returns = [
                (t, line, col) for t, line, col in self.current_func_returns
                if t.kind != TypeKind.UNKNOWN
            ]
            if non_unknown_returns:
                first_ret_type, first_line, first_col = non_unknown_returns[0]
                for other_type, o_line, o_col in non_unknown_returns[1:]:
                    if not self._are_types_compatible(first_ret_type, other_type):
                        self._add_diagnostic(
                            o_line or 1, o_col or 1, "error",
                            f"Semantic error: Inconsistent return types in function '{fn.name}': "
                            f"returning '{first_ret_type.to_str()}' and '{other_type.to_str()}'."
                        )

                # Check against declared return type if specified
                if fn.return_type.kind not in [TypeKind.UNKNOWN, TypeKind.VOID]:
                    for r_type, r_line, r_col in self.current_func_returns:
                        if r_type.kind != TypeKind.UNKNOWN and not self._are_types_compatible(fn.return_type, r_type):
                            self._add_diagnostic(
                                r_line or 1, r_col or 1, "error",
                                f"Semantic error: Return type mismatch in function '{fn.name}': "
                                f"expected '{fn.return_type.to_str()}', got '{r_type.to_str()}'."
                            )

                # Update function return type if was unknown
                if fn.return_type.kind == TypeKind.UNKNOWN:
                    fn.return_type = first_ret_type
                    # Update symbol table entry
                    fn_sym = self.symbol_table.lookup(fn.name)
                    if fn_sym:
                        fn_sym.return_type = first_ret_type
                        fn_sym.symbol_type = first_ret_type
        else:
            if fn.return_type.kind == TypeKind.UNKNOWN:
                fn.return_type = IRType.void_type()

        # Pop Function Scope
        self.symbol_table.pop_scope()
        self.current_function = None
        self.current_func_returns = []

    # -------------------------------------------------------------------------
    # Statement Analysis
    # -------------------------------------------------------------------------

    def _analyze_statement(self, stmt: Statement):
        if isinstance(stmt, VarDecl):
            # Check redeclaration in same scope for static languages or explicit declarations
            existing = self.symbol_table.lookup_local(stmt.name)
            if existing and existing.is_declared:
                if self.src_lang in ["java", "go", "cpp", "arduino"]:
                    self._add_diagnostic(
                        stmt.line or 1, stmt.column or 1, "error",
                        f"Semantic error: Redeclaration of variable '{stmt.name}' in the same scope."
                    )
                elif stmt.var_type.kind != TypeKind.UNKNOWN and existing.symbol_type.kind != TypeKind.UNKNOWN:
                    if not self._are_types_compatible(existing.symbol_type, stmt.var_type):
                        self._add_diagnostic(
                            stmt.line or 1, stmt.column or 1, "error",
                            f"Semantic error: Conflicting redeclaration of variable '{stmt.name}': "
                            f"previously '{existing.symbol_type.to_str()}', now '{stmt.var_type.to_str()}'."
                        )

            val_type = IRType.unknown()
            if stmt.initializer:
                val_type = self._analyze_expression(stmt.initializer)
                if stmt.var_type.kind == TypeKind.UNKNOWN:
                    stmt.var_type = val_type
                elif val_type.kind != TypeKind.UNKNOWN:
                    if not self._are_types_compatible(stmt.var_type, val_type):
                        self._add_diagnostic(
                            stmt.line or 1, stmt.column or 1, "error",
                            f"Semantic error: Cannot initialize variable '{stmt.name}' of type "
                            f"'{stmt.var_type.to_str()}' with value of type '{val_type.to_str()}'."
                        )

            self.symbol_table.define(
                name=stmt.name,
                symbol_type=stmt.var_type,
                kind="variable",
                is_initialized=stmt.initializer is not None,
                is_declared=True,
                line=stmt.line,
                column=stmt.column
            )

        elif isinstance(stmt, Assignment):
            val_type = self._analyze_expression(stmt.value)

            if isinstance(stmt.target, Identifier):
                if self.branch_assigned is not None:
                    self.branch_assigned.add(stmt.target.name)
                sym = self.symbol_table.lookup(stmt.target.name)
                if sym is None:
                    # In dynamic languages (Python, JS) or Verilog, assignment defines variable in enclosing scope
                    if self.src_lang in ["python", "javascript", "verilog"] or self.tgt_lang in ["python", "javascript"]:
                        sym = self.symbol_table.define_in_enclosing(
                            scope_types=["function", "global"],
                            name=stmt.target.name,
                            symbol_type=val_type,
                            kind="variable",
                            is_initialized=True,
                            is_declared=False,
                            line=stmt.target.line,
                            column=stmt.target.column
                        )
                        stmt.target.inferred_type = val_type
                    else:
                        # In strict static languages (Java, Go, C++), assignment to undeclared variable is an error
                        self._add_diagnostic(
                            stmt.target.line or 1, stmt.target.column or 1, "error",
                            f"Semantic error: Variable '{stmt.target.name}' is not declared before assignment."
                        )
                else:
                    # Variable exists: check type compatibility
                    stmt.target.inferred_type = sym.symbol_type
                    if sym.symbol_type.kind == TypeKind.UNKNOWN and val_type.kind != TypeKind.UNKNOWN:
                        sym.symbol_type = val_type
                        stmt.target.inferred_type = val_type
                    elif sym.symbol_type.kind != TypeKind.UNKNOWN and val_type.kind != TypeKind.UNKNOWN:
                        if not self._are_types_compatible(sym.symbol_type, val_type):
                            # In statically typed languages, reject type mutation
                            if self.src_lang in ["java", "go", "cpp", "arduino"] or self.tgt_lang in ["java", "go", "cpp", "arduino"]:
                                self._add_diagnostic(
                                    stmt.target.line or 1, stmt.target.column or 1, "error",
                                    f"Semantic error: Cannot assign value of type '{val_type.to_str()}' "
                                    f"to variable '{stmt.target.name}' of type '{sym.symbol_type.to_str()}'."
                                )
                    sym.is_initialized = True

            elif isinstance(stmt.target, ArrayAccess):
                elem_type = self._analyze_expression(stmt.target)
                if elem_type.kind != TypeKind.UNKNOWN and val_type.kind != TypeKind.UNKNOWN:
                    if not self._are_types_compatible(elem_type, val_type):
                        self._add_diagnostic(
                            stmt.target.line or 1, stmt.target.column or 1, "error",
                            f"Semantic error: Cannot assign value of type '{val_type.to_str()}' "
                            f"into array element of type '{elem_type.to_str()}'."
                        )

        elif isinstance(stmt, IfStmt):
            self._analyze_condition(stmt.condition)

            # Then branch scope
            prev_branch = self.branch_assigned
            self.branch_assigned = set()
            self.symbol_table.push_scope(name="block:if_then", scope_type="block")
            for s in stmt.then_branch:
                self._analyze_statement(s)
            self.symbol_table.pop_scope()
            then_assigned = self.branch_assigned

            # Else branch scope
            else_assigned = set()
            if stmt.else_branch:
                self.branch_assigned = set()
                self.symbol_table.push_scope(name="block:if_else", scope_type="block")
                for s in stmt.else_branch:
                    self._analyze_statement(s)
                self.symbol_table.pop_scope()
                else_assigned = self.branch_assigned

            self.branch_assigned = prev_branch
            if self.branch_assigned is not None:
                self.branch_assigned.update(then_assigned.intersection(else_assigned) if stmt.else_branch else set())

            # Track variable initialization across conditional branches
            if stmt.else_branch:
                common = then_assigned.intersection(else_assigned)
                for var_name in common:
                    s_sym = self.symbol_table.lookup(var_name)
                    if s_sym:
                        s_sym.is_initialized = True
                only_one = (then_assigned - else_assigned).union(else_assigned - then_assigned)
                for var_name in only_one:
                    s_sym = self.symbol_table.lookup(var_name)
                    if s_sym and not s_sym.is_declared:
                        s_sym.is_initialized = False
            else:
                for var_name in then_assigned:
                    s_sym = self.symbol_table.lookup(var_name)
                    if s_sym and not s_sym.is_declared:
                        s_sym.is_initialized = False

        elif isinstance(stmt, WhileStmt):
            self._analyze_condition(stmt.condition)
            self.symbol_table.push_scope(name="loop:while", scope_type="loop")
            for s in stmt.body:
                self._analyze_statement(s)
            self.symbol_table.pop_scope()

        elif isinstance(stmt, ForRangeStmt):
            if stmt.start:
                st = self._analyze_expression(stmt.start)
                if st.kind not in [TypeKind.INT, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        stmt.start.line or 1, stmt.start.column or 1, "error",
                        f"Semantic error: Range start must be an integer, got '{st.to_str()}'."
                    )
            if stmt.end:
                et = self._analyze_expression(stmt.end)
                if et.kind not in [TypeKind.INT, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        stmt.end.line or 1, stmt.end.column or 1, "error",
                        f"Semantic error: Range end must be an integer, got '{et.to_str()}'."
                    )
            if stmt.step:
                stept = self._analyze_expression(stmt.step)
                if stept.kind not in [TypeKind.INT, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        stmt.step.line or 1, stmt.step.column or 1, "error",
                        f"Semantic error: Range step must be an integer, got '{stept.to_str()}'."
                    )

            if self.src_lang in ["python", "javascript", "verilog"]:
                self.symbol_table.define_in_enclosing(
                    scope_types=["function", "global"],
                    name=stmt.var_name,
                    symbol_type=IRType.int_type(),
                    kind="variable",
                    is_initialized=True,
                    is_declared=False,
                    line=stmt.line,
                    column=stmt.column
                )

            self.symbol_table.push_scope(name="loop:for", scope_type="loop")
            self.symbol_table.define(
                name=stmt.var_name,
                symbol_type=IRType.int_type(),
                kind="variable",
                is_initialized=True,
                is_declared=True,
                line=stmt.line,
                column=stmt.column
            )
            for s in stmt.body:
                self._analyze_statement(s)
            self.symbol_table.pop_scope()

        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                t = self._analyze_expression(stmt.value)
                self.current_func_returns.append((t, stmt.line, stmt.column))
            else:
                self.current_func_returns.append((IRType.void_type(), stmt.line, stmt.column))

        elif isinstance(stmt, PrintStmt):
            for arg in stmt.args:
                self._analyze_expression(arg)

        elif isinstance(stmt, ExpressionStmt):
            self._analyze_expression(stmt.expr)

    # -------------------------------------------------------------------------
    # Expression Analysis & Type Inference
    # -------------------------------------------------------------------------

    def _analyze_condition(self, expr: Optional[Expression]):
        if not expr:
            return
        t = self._analyze_expression(expr)
        # Truthiness: boolean, integer, float, string, or unknown are allowed in conditions
        # Arrays in condition may be checked for emptiness
        return t

    def _analyze_expression(self, expr: Optional[Expression]) -> IRType:
        if not expr:
            return IRType.unknown()

        if isinstance(expr, Literal):
            if isinstance(expr.value, bool):
                expr.inferred_type = IRType.bool_type()
            elif isinstance(expr.value, int):
                expr.inferred_type = IRType.int_type()
            elif isinstance(expr.value, float):
                expr.inferred_type = IRType.float_type()
            elif isinstance(expr.value, str):
                expr.inferred_type = IRType.string_type()
            return expr.inferred_type

        elif isinstance(expr, Identifier):
            name = expr.name
            sym = self.symbol_table.lookup(name)

            # Check if this is an implicit loop variable or known builtin
            if sym is None:
                # Check for member access or standard library namespace
                is_known_member = any(name.startswith(f"{prefix}.") for prefix in ["math", "np", "pd", "fmt", "System", "Serial", "console"])
                if is_known_member:
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

                # Check if it was imported
                if self._is_imported(name):
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

                self._add_diagnostic(
                    expr.line or 1, expr.column or 1, "error",
                    f"Semantic error: Undefined variable '{name}'."
                )
                expr.inferred_type = IRType.unknown()
                return expr.inferred_type

            # Check uninitialized read
            if not sym.is_initialized and sym.kind == "variable":
                self._add_diagnostic(
                    expr.line or 1, expr.column or 1, "warning",
                    f"Semantic warning: Variable '{name}' may be read before initialization."
                )

            expr.inferred_type = sym.symbol_type
            return expr.inferred_type

        elif isinstance(expr, BinaryOp):
            lt = self._analyze_expression(expr.left)
            rt = self._analyze_expression(expr.right)
            op = expr.op

            # 1. Comparison operations
            if op in ["==", "!=", "<", "<=", ">", ">="]:
                if lt.kind != TypeKind.UNKNOWN and rt.kind != TypeKind.UNKNOWN:
                    if not self._are_types_comparable(lt, rt):
                        self._add_diagnostic(
                            expr.line or 1, expr.column or 1, "error",
                            f"Semantic error: Incompatible types for comparison '{op}': "
                            f"'{lt.to_str()}' and '{rt.to_str()}'."
                        )
                expr.inferred_type = IRType.bool_type()
                return expr.inferred_type

            # 2. Logical operations
            if op in ["&&", "||", "and", "or"]:
                expr.inferred_type = IRType.bool_type()
                return expr.inferred_type

            # 3. Floor division //
            if op in ["//"]:
                if lt.kind not in [TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN] or \
                   rt.kind not in [TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Floor division '//' requires numeric operands, got '{lt.to_str()}' and '{rt.to_str()}'."
                    )
                expr.inferred_type = IRType.int_type()
                return expr.inferred_type

            # 4. True division /
            if op in ["/"]:
                if lt.kind not in [TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN] or \
                   rt.kind not in [TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Division '/' requires numeric operands, got '{lt.to_str()}' and '{rt.to_str()}'."
                    )
                expr.inferred_type = IRType.float_type()
                return expr.inferred_type

            # 5. String concatenation / repetition
            if op == "+":
                if lt.kind == TypeKind.STRING or rt.kind == TypeKind.STRING:
                    # In python/js, string concatenation
                    expr.inferred_type = IRType.string_type()
                    return expr.inferred_type
                if lt.kind == TypeKind.ARRAY or rt.kind == TypeKind.ARRAY:
                    if lt.kind == TypeKind.ARRAY and rt.kind == TypeKind.ARRAY:
                        expr.inferred_type = lt
                        return expr.inferred_type
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Cannot concatenate array with non-array type '{rt.to_str() if lt.kind == TypeKind.ARRAY else lt.to_str()}'."
                    )
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

            if op == "*":
                if (lt.kind == TypeKind.STRING and rt.kind == TypeKind.INT) or \
                   (lt.kind == TypeKind.INT and rt.kind == TypeKind.STRING):
                    expr.inferred_type = IRType.string_type()
                    return expr.inferred_type
                if lt.kind == TypeKind.STRING and rt.kind == TypeKind.STRING:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        "Semantic error: Cannot multiply two string operands."
                    )
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

            # 6. Arithmetic subtraction, multiplication, modulo
            if op in ["-", "*", "%"]:
                if lt.kind == TypeKind.STRING or rt.kind == TypeKind.STRING:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Operator '{op}' cannot be applied to strings."
                    )
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

            # Widening arithmetic: if either is float, result is float, else int
            if lt.kind == TypeKind.FLOAT or rt.kind == TypeKind.FLOAT:
                expr.inferred_type = IRType.float_type()
            elif lt.kind == TypeKind.INT and rt.kind == TypeKind.INT:
                expr.inferred_type = IRType.int_type()
            elif lt.kind != TypeKind.UNKNOWN and rt.kind != TypeKind.UNKNOWN:
                expr.inferred_type = lt
            else:
                expr.inferred_type = IRType.int_type()

            return expr.inferred_type

        elif isinstance(expr, UnaryOp):
            t = self._analyze_expression(expr.operand)
            if expr.op in ["!", "not"]:
                expr.inferred_type = IRType.bool_type()
            elif expr.op in ["-", "+"]:
                if t.kind in [TypeKind.STRING, TypeKind.ARRAY]:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Unary operator '{expr.op}' cannot be applied to type '{t.to_str()}'."
                    )
                expr.inferred_type = t if t.kind in [TypeKind.INT, TypeKind.FLOAT] else IRType.int_type()
            else:
                expr.inferred_type = t
            return expr.inferred_type

        elif isinstance(expr, ArrayLiteral):
            if not expr.elements:
                expr.inferred_type = IRType.array_of(IRType.unknown())
                return expr.inferred_type

            elem_types = [self._analyze_expression(e) for e in expr.elements]
            first_t = elem_types[0]

            for idx, other_t in enumerate(elem_types[1:], start=1):
                if first_t.kind != TypeKind.UNKNOWN and other_t.kind != TypeKind.UNKNOWN:
                    if not self._are_types_compatible(first_t, other_t):
                        elem_node = expr.elements[idx]
                        self._add_diagnostic(
                            elem_node.line or 1, elem_node.column or 1, "error",
                            f"Semantic error: Inconsistent element types in array literal: "
                            f"found '{first_t.to_str()}' and '{other_t.to_str()}'."
                        )
                        break

            # Numeric promotion in array literal if mixed int/float
            has_float = any(t.kind == TypeKind.FLOAT for t in elem_types)
            all_numeric = all(t.kind in [TypeKind.INT, TypeKind.FLOAT, TypeKind.UNKNOWN] for t in elem_types)
            if has_float and all_numeric:
                resolved_elem = IRType.float_type()
            else:
                resolved_elem = first_t

            expr.inferred_type = IRType.array_of(resolved_elem)
            return expr.inferred_type

        elif isinstance(expr, ArrayAccess):
            arr_t = self._analyze_expression(expr.array)
            idx_t = self._analyze_expression(expr.index)

            # Check index type
            if idx_t.kind not in [TypeKind.INT, TypeKind.UNKNOWN]:
                self._add_diagnostic(
                    expr.index.line or 1, expr.index.column or 1, "error",
                    f"Semantic error: Array index must be an integer, got '{idx_t.to_str()}'."
                )

            # Check container type
            if arr_t.kind not in [TypeKind.ARRAY, TypeKind.STRING, TypeKind.UNKNOWN]:
                self._add_diagnostic(
                    expr.array.line or 1, expr.array.column or 1, "error",
                    f"Semantic error: Cannot index into non-subscriptable type '{arr_t.to_str()}'."
                )
                expr.inferred_type = IRType.unknown()
                return expr.inferred_type

            if arr_t.kind == TypeKind.STRING:
                expr.inferred_type = IRType.string_type()
            elif arr_t.kind == TypeKind.ARRAY and arr_t.element_type:
                expr.inferred_type = arr_t.element_type
            else:
                expr.inferred_type = IRType.int_type()

            return expr.inferred_type

        elif isinstance(expr, ArrayLength):
            if expr.array:
                arr_t = self._analyze_expression(expr.array)
                if arr_t.kind not in [TypeKind.ARRAY, TypeKind.STRING, TypeKind.UNKNOWN]:
                    self._add_diagnostic(
                        expr.array.line or 1, expr.array.column or 1, "error",
                        f"Semantic error: Object of type '{arr_t.to_str()}' has no length."
                    )
            expr.inferred_type = IRType.int_type()
            return expr.inferred_type

        elif isinstance(expr, FunctionCall):
            name = expr.name
            arg_types = [self._analyze_expression(a) for a in expr.args]

            # Check method calls like obj.append(x) or str.upper()
            if "." in name:
                parts = name.split(".")
                obj_name, method = parts[0], parts[1]
                obj_sym = self.symbol_table.lookup(obj_name)
                if obj_sym and obj_sym.symbol_type.kind == TypeKind.ARRAY:
                    if method in ["append", "push"] and len(arg_types) >= 1:
                        val_t = arg_types[0]
                        if obj_sym.symbol_type.element_type and obj_sym.symbol_type.element_type.kind != TypeKind.UNKNOWN:
                            if val_t.kind != TypeKind.UNKNOWN and not self._are_types_compatible(obj_sym.symbol_type.element_type, val_t):
                                self._add_diagnostic(
                                    expr.line or 1, expr.column or 1, "error",
                                    f"Semantic error: Cannot append value of type '{val_t.to_str()}' "
                                    f"to array of '{obj_sym.symbol_type.element_type.to_str()}'."
                                )
                        else:
                            obj_sym.symbol_type.element_type = val_t
                    expr.inferred_type = IRType.void_type()
                    return expr.inferred_type

                elif obj_sym and obj_sym.symbol_type.kind == TypeKind.STRING:
                    if method in ["strip", "trim", "upper", "lower", "toUpperCase", "toLowerCase", "replace", "substring", "slice"]:
                        expr.inferred_type = IRType.string_type()
                        return expr.inferred_type
                    elif method in ["split"]:
                        expr.inferred_type = IRType.array_of(IRType.string_type())
                        return expr.inferred_type
                    elif method in ["startsWith", "startswith", "endsWith", "endswith", "contains", "includes"]:
                        expr.inferred_type = IRType.bool_type()
                        return expr.inferred_type
                    elif method in ["indexOf", "find", "length"]:
                        expr.inferred_type = IRType.int_type()
                        return expr.inferred_type

                elif (obj_sym and obj_sym.kind == "module") or obj_name in ["Serial", "System", "Math", "console", "fmt", "math", "np", "pd"]:
                    expr.inferred_type = IRType.unknown()
                    return expr.inferred_type

            sym = self.symbol_table.lookup(name)
            if not sym:
                # Builtin math/utility functions
                if any(name.lower().endswith(f".{fn}") or name.lower() == fn for fn in ["sqrt", "sin", "cos", "tan", "log", "exp", "pow"]):
                    expr.inferred_type = IRType.float_type()
                    return expr.inferred_type
                if any(name.lower().endswith(f".{fn}") or name.lower() == fn for fn in ["floor", "ceil", "round", "abs", "len", "size"]):
                    expr.inferred_type = IRType.int_type()
                    return expr.inferred_type

                self._add_diagnostic(
                    expr.line or 1, expr.column or 1, "error",
                    f"Semantic error: Call to undefined function '{name}'."
                )
                expr.inferred_type = IRType.unknown()
                return expr.inferred_type

            if sym.kind == "function":
                # Arity check
                expected_arity = len(sym.param_types) if sym.param_types is not None else 0
                actual_arity = len(expr.args)
                if expected_arity != actual_arity:
                    self._add_diagnostic(
                        expr.line or 1, expr.column or 1, "error",
                        f"Semantic error: Function '{name}' expects {expected_arity} arguments, but got {actual_arity}."
                    )

                # Argument type compatibility check
                if sym.param_types:
                    for i, (param_t, arg_t) in enumerate(zip(sym.param_types, arg_types)):
                        if param_t.kind != TypeKind.UNKNOWN and arg_t.kind != TypeKind.UNKNOWN:
                            if not self._are_types_compatible(param_t, arg_t):
                                arg_node = expr.args[i]
                                self._add_diagnostic(
                                    arg_node.line or 1, arg_node.column or 1, "error",
                                    f"Semantic error: Type mismatch for argument {i + 1} of function '{name}': "
                                    f"expected '{param_t.to_str()}', got '{arg_t.to_str()}'."
                                )

                expr.inferred_type = sym.return_type or IRType.unknown()
                return expr.inferred_type

            expr.inferred_type = sym.symbol_type
            return expr.inferred_type

        return IRType.unknown()

    # -------------------------------------------------------------------------
    # Type Compatibility & Helper Rules
    # -------------------------------------------------------------------------

    def _are_types_compatible(self, target: IRType, source: IRType) -> bool:
        """Determines if a value of type `source` can be used/assigned where `target` is expected."""
        if target.kind == TypeKind.UNKNOWN or source.kind == TypeKind.UNKNOWN:
            return True

        if target.kind == source.kind:
            if target.kind == TypeKind.ARRAY:
                if target.element_type is None or source.element_type is None:
                    return True
                return self._are_types_compatible(target.element_type, source.element_type)
            return True

        # Numeric implicit widening: int can widen to float
        if target.kind == TypeKind.FLOAT and source.kind == TypeKind.INT:
            return True

        # Allow int to bool truthiness if not strict static target
        if target.kind == TypeKind.BOOL and source.kind == TypeKind.INT and self.tgt_lang in ["python", "javascript"]:
            return True

        return False

    def _are_types_comparable(self, t1: IRType, t2: IRType) -> bool:
        if t1.kind == TypeKind.UNKNOWN or t2.kind == TypeKind.UNKNOWN:
            return True
        if t1.kind == t2.kind:
            return True
        # Numeric comparison is allowed
        if t1.kind in [TypeKind.INT, TypeKind.FLOAT] and t2.kind in [TypeKind.INT, TypeKind.FLOAT]:
            return True
        return False

    def _is_imported(self, name: str) -> bool:
        return self.symbol_table.lookup(name) is not None

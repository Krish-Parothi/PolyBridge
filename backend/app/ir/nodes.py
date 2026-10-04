from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Union, Dict

class TypeKind(str, Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    VOID = "void"
    ARRAY = "array"
    UNKNOWN = "unknown"

@dataclass
class IRType:
    kind: TypeKind
    element_type: Optional[IRType] = None  # for ARRAY

    def to_str(self) -> str:
        if self.kind == TypeKind.ARRAY and self.element_type:
            return f"{self.element_type.to_str()}[]"
        return self.kind.value

    def to_dict(self) -> Dict[str, Any]:
        d = {"kind": self.kind.value}
        if self.element_type:
            d["element_type"] = self.element_type.to_dict()
        return d

    @classmethod
    def int_type(cls) -> IRType:
        return cls(TypeKind.INT)

    @classmethod
    def float_type(cls) -> IRType:
        return cls(TypeKind.FLOAT)

    @classmethod
    def string_type(cls) -> IRType:
        return cls(TypeKind.STRING)

    @classmethod
    def bool_type(cls) -> IRType:
        return cls(TypeKind.BOOL)

    @classmethod
    def void_type(cls) -> IRType:
        return cls(TypeKind.VOID)

    @classmethod
    def unknown(cls) -> IRType:
        return cls(TypeKind.UNKNOWN)

    @classmethod
    def array_of(cls, elem: IRType) -> IRType:
        return cls(TypeKind.ARRAY, element_type=elem)

@dataclass
class IRNode:
    """Base class for all Intermediate Representation nodes."""
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def to_tree_node(self) -> Dict[str, Any]:
        """Convert to hierarchical node for tree visualization (react-d3-tree)."""
        raise NotImplementedError

# Expressions

@dataclass
class Expression(IRNode):
    inferred_type: IRType = field(default_factory=IRType.unknown, kw_only=True)

@dataclass
class Literal(Expression):
    value: Union[int, float, str, bool] = None

    def __post_init__(self):
        if self.inferred_type.kind == TypeKind.UNKNOWN:
            if isinstance(self.value, bool):
                self.inferred_type = IRType.bool_type()
            elif isinstance(self.value, int):
                self.inferred_type = IRType.int_type()
            elif isinstance(self.value, float):
                self.inferred_type = IRType.float_type()
            elif isinstance(self.value, str):
                self.inferred_type = IRType.string_type()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Literal",
            "value": self.value,
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        val_str = repr(self.value)
        return {
            "name": f"Literal: {val_str}",
            "attributes": {"type": self.inferred_type.to_str()},
            "children": []
        }

@dataclass
class Identifier(Expression):
    name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Identifier",
            "name": self.name,
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": f"Id: {self.name}",
            "attributes": {"type": self.inferred_type.to_str()},
            "children": []
        }

@dataclass
class BinaryOp(Expression):
    left: Expression = None
    op: str = ""  # +, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||
    right: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "BinaryOp",
            "op": self.op,
            "left": self.left.to_dict() if self.left else None,
            "right": self.right.to_dict() if self.right else None,
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.left:
            children.append(self.left.to_tree_node())
        if self.right:
            children.append(self.right.to_tree_node())
        return {
            "name": f"BinaryOp ({self.op})",
            "attributes": {"op": self.op, "type": self.inferred_type.to_str()},
            "children": children
        }

@dataclass
class UnaryOp(Expression):
    op: str = ""  # -, !
    operand: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "UnaryOp",
            "op": self.op,
            "operand": self.operand.to_dict() if self.operand else None,
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = [self.operand.to_tree_node()] if self.operand else []
        return {
            "name": f"UnaryOp ({self.op})",
            "attributes": {"op": self.op, "type": self.inferred_type.to_str()},
            "children": children
        }

@dataclass
class ArrayLiteral(Expression):
    elements: List[Expression] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ArrayLiteral",
            "elements": [e.to_dict() for e in self.elements],
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": f"ArrayLiteral [{len(self.elements)}]",
            "attributes": {"type": self.inferred_type.to_str()},
            "children": [e.to_tree_node() for e in self.elements]
        }

@dataclass
class ArrayAccess(Expression):
    array: Expression = None
    index: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ArrayAccess",
            "array": self.array.to_dict() if self.array else None,
            "index": self.index.to_dict() if self.index else None,
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.array:
            children.append(self.array.to_tree_node())
        if self.index:
            children.append(self.index.to_tree_node())
        return {
            "name": "ArrayAccess []",
            "attributes": {"type": self.inferred_type.to_str()},
            "children": children
        }

@dataclass
class ArrayLength(Expression):
    array: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ArrayLength",
            "array": self.array.to_dict() if self.array else None,
            "type": IRType.int_type().to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = [self.array.to_tree_node()] if self.array else []
        return {
            "name": "ArrayLength",
            "attributes": {"type": "int"},
            "children": children
        }

@dataclass
class FunctionCall(Expression):
    name: str = ""
    args: List[Expression] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "FunctionCall",
            "name": self.name,
            "args": [a.to_dict() for a in self.args],
            "type": self.inferred_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": f"Call: {self.name}()",
            "attributes": {"args_count": len(self.args), "type": self.inferred_type.to_str()},
            "children": [a.to_tree_node() for a in self.args]
        }

# Statements

@dataclass
class Statement(IRNode):
    pass

@dataclass
class VarDecl(Statement):
    name: str = ""
    var_type: IRType = field(default_factory=IRType.unknown)
    initializer: Optional[Expression] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "VarDecl",
            "name": self.name,
            "type": self.var_type.to_dict(),
            "initializer": self.initializer.to_dict() if self.initializer else None
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = [self.initializer.to_tree_node()] if self.initializer else []
        return {
            "name": f"VarDecl: {self.name}",
            "attributes": {"type": self.var_type.to_str()},
            "children": children
        }

@dataclass
class Assignment(Statement):
    target: Expression = None  # Identifier or ArrayAccess
    value: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Assignment",
            "target": self.target.to_dict() if self.target else None,
            "value": self.value.to_dict() if self.value else None
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.target:
            children.append(self.target.to_tree_node())
        if self.value:
            children.append(self.value.to_tree_node())
        return {
            "name": "Assignment (=)",
            "attributes": {},
            "children": children
        }

@dataclass
class IfStmt(Statement):
    condition: Expression = None
    then_branch: List[Statement] = field(default_factory=list)
    else_branch: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "IfStmt",
            "condition": self.condition.to_dict() if self.condition else None,
            "then_branch": [s.to_dict() for s in self.then_branch],
            "else_branch": [s.to_dict() for s in self.else_branch]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.condition:
            children.append({
                "name": "Condition",
                "attributes": {},
                "children": [self.condition.to_tree_node()]
            })
        children.append({
            "name": f"Then Branch ({len(self.then_branch)})",
            "attributes": {},
            "children": [s.to_tree_node() for s in self.then_branch]
        })
        if self.else_branch:
            children.append({
                "name": f"Else Branch ({len(self.else_branch)})",
                "attributes": {},
                "children": [s.to_tree_node() for s in self.else_branch]
            })
        return {
            "name": "IfStmt",
            "attributes": {},
            "children": children
        }

@dataclass
class WhileStmt(Statement):
    condition: Expression = None
    body: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "WhileStmt",
            "condition": self.condition.to_dict() if self.condition else None,
            "body": [s.to_dict() for s in self.body]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.condition:
            children.append({
                "name": "Condition",
                "attributes": {},
                "children": [self.condition.to_tree_node()]
            })
        children.append({
            "name": f"Body ({len(self.body)})",
            "attributes": {},
            "children": [s.to_tree_node() for s in self.body]
        })
        return {
            "name": "WhileLoop",
            "attributes": {},
            "children": children
        }

@dataclass
class ForRangeStmt(Statement):
    """Normalized procedural for loop: for var_name in range(start, end, step)."""
    var_name: str = ""
    start: Expression = None
    end: Expression = None
    step: Optional[Expression] = None
    body: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ForRangeStmt",
            "var_name": self.var_name,
            "start": self.start.to_dict() if self.start else None,
            "end": self.end.to_dict() if self.end else None,
            "step": self.step.to_dict() if self.step else None,
            "body": [s.to_dict() for s in self.body]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        range_children = []
        if self.start:
            range_children.append(self.start.to_tree_node())
        if self.end:
            range_children.append(self.end.to_tree_node())
        if self.step:
            range_children.append(self.step.to_tree_node())
        children.append({
            "name": f"Range ({self.var_name})",
            "attributes": {"var": self.var_name},
            "children": range_children
        })
        children.append({
            "name": f"Body ({len(self.body)})",
            "attributes": {},
            "children": [s.to_tree_node() for s in self.body]
        })
        return {
            "name": f"ForRange: {self.var_name}",
            "attributes": {"var": self.var_name},
            "children": children
        }

@dataclass
class ReturnStmt(Statement):
    value: Optional[Expression] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ReturnStmt",
            "value": self.value.to_dict() if self.value else None
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = [self.value.to_tree_node()] if self.value else []
        return {
            "name": "Return",
            "attributes": {},
            "children": children
        }

@dataclass
class PrintStmt(Statement):
    args: List[Expression] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "PrintStmt",
            "args": [a.to_dict() for a in self.args]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": "PrintStmt",
            "attributes": {"args_count": len(self.args)},
            "children": [a.to_tree_node() for a in self.args]
        }

@dataclass
class ExpressionStmt(Statement):
    expr: Expression = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "ExpressionStmt",
            "expr": self.expr.to_dict() if self.expr else None
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": "ExpressionStmt",
            "attributes": {},
            "children": [self.expr.to_tree_node()] if self.expr else []
        }

# Functions & Program

@dataclass
class Parameter(IRNode):
    name: str = ""
    param_type: IRType = field(default_factory=IRType.unknown)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Parameter",
            "name": self.name,
            "type": self.param_type.to_dict()
        }

    def to_tree_node(self) -> Dict[str, Any]:
        return {
            "name": f"Param: {self.name}",
            "attributes": {"type": self.param_type.to_str()},
            "children": []
        }

@dataclass
class FunctionDef(IRNode):
    name: str = ""
    params: List[Parameter] = field(default_factory=list)
    return_type: IRType = field(default_factory=IRType.void_type)
    body: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "FunctionDef",
            "name": self.name,
            "params": [p.to_dict() for p in self.params],
            "return_type": self.return_type.to_dict(),
            "body": [s.to_dict() for s in self.body]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        params_node = {
            "name": f"Parameters ({len(self.params)})",
            "attributes": {},
            "children": [p.to_tree_node() for p in self.params]
        }
        body_node = {
            "name": f"Body ({len(self.body)})",
            "attributes": {},
            "children": [s.to_tree_node() for s in self.body]
        }
        return {
            "name": f"Function: {self.name}",
            "attributes": {
                "returns": self.return_type.to_str(),
                "params": len(self.params)
            },
            "children": [params_node, body_node]
        }

@dataclass
class Program(IRNode):
    functions: List[FunctionDef] = field(default_factory=list)
    global_statements: List[Statement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": "Program",
            "functions": [f.to_dict() for f in self.functions],
            "global_statements": [s.to_dict() for s in self.global_statements]
        }

    def to_tree_node(self) -> Dict[str, Any]:
        children = []
        if self.functions:
            children.append({
                "name": f"Functions ({len(self.functions)})",
                "attributes": {},
                "children": [f.to_tree_node() for f in self.functions]
            })
        if self.global_statements:
            children.append({
                "name": f"Global Statements ({len(self.global_statements)})",
                "attributes": {},
                "children": [s.to_tree_node() for s in self.global_statements]
            })
        return {
            "name": "Program (IR Root)",
            "attributes": {
                "functions": len(self.functions),
                "statements": len(self.global_statements)
            },
            "children": children
        }

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from dtypes import DType, DTypeKind, dtypeInt, pointerTo
from objects import Obj
from tokens import Token


class NodeKind(Enum):
    """Represents the different kinds of abstract syntax tree (AST) nodes.

    Args:
        Enum (Enum): Base enumeration class.
    """

    ADD = auto()  # +
    SUB = auto()  # -
    MUL = auto()  # *
    DIV = auto()  # /
    NEG = auto()  # unary -
    EQ = auto()  # ==
    NE = auto()  # !=
    LT = auto()  # <
    LE = auto()  # <=
    ASSIGN = auto()  # =
    ADDR = auto()  # unary &
    DEREF = auto()  # unary *
    RETURN = auto()  # "return"
    IF = auto()  # "if"
    FOR = auto()  # "for" or "while"
    BLOCK = auto()  # { ... }
    EXPR_STMT = auto()  # Expression statement
    VAR = auto()  # Variable
    NUM = auto()  # Integer


@dataclass
class Node:
    """Represents a node in the abstract syntax tree (AST)."""

    kind: NodeKind  # Node kind
    tok: Token  # Representative token
    dtype: DType | None = None  # Data type

    lhs: Node | None = None  # Left-hand side
    rhs: Node | None = None  # Right-hand side

    # "if" or "for" statement
    cond: Node | None = None
    then: Node | None = None
    els: Node | None = None
    init: Node | None = None
    inc: Node | None = None

    body: list[Node] = field(default_factory=list)  # Block

    var: Obj | None = None  # Used if kind == NodeKind.VAR
    val: int = 0  # Used if kind == NodeKind.NUM


def addType(node: Node | None) -> None:
    """Annotates the AST with type information.

    Args:
        node (Node | None): The AST node to annotate.
    """
    if node is None or node.dtype is not None:
        return

    addType(node.lhs)
    addType(node.rhs)
    addType(node.cond)
    addType(node.then)
    addType(node.els)
    addType(node.init)
    addType(node.inc)

    for stmt in node.body:
        addType(stmt)

    match node.kind:
        case (
            NodeKind.ADD
            | NodeKind.SUB
            | NodeKind.MUL
            | NodeKind.DIV
            | NodeKind.NEG
            | NodeKind.ASSIGN
        ):
            node.dtype = node.lhs.dtype

        case (
            NodeKind.EQ
            | NodeKind.NE
            | NodeKind.LT
            | NodeKind.LE
            | NodeKind.VAR
            | NodeKind.NUM
        ):
            node.dtype = dtypeInt

        case NodeKind.ADDR:
            node.dtype = pointerTo(node.lhs.dtype)

        case NodeKind.DEREF:
            if node.lhs.dtype.kind == DTypeKind.PTR:
                node.dtype = node.lhs.dtype.base
            else:
                node.dtype = dtypeInt

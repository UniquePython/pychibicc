from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from dtypes import Dtype, DtypeKind, dtypeInt, pointerTo
from error_reporter import ErrorReporter
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
    FUNCALL = auto()  # Function call
    EXPR_STMT = auto()  # Expression statement
    VAR = auto()  # Variable
    NUM = auto()  # Integer


@dataclass
class Node:
    """Represents a node in the abstract syntax tree (AST)."""

    kind: NodeKind  # Node kind
    tok: Token  # Representative token
    dtype: Dtype | None = None  # Data type

    lhs: Node | None = None  # Left-hand side
    rhs: Node | None = None  # Right-hand side

    # "if" or "for" statement
    cond: Node | None = None
    then: Node | None = None
    els: Node | None = None
    init: Node | None = None
    inc: Node | None = None

    body: list[Node] = field(default_factory=list)  # Block

    # Function call
    funcName: str = ""
    args: list[Node] = field(default_factory=list)

    var: Obj | None = None  # Used if kind == NodeKind.VAR
    val: int = 0  # Used if kind == NodeKind.NUM


def formatNode(node: Node | None) -> str:
    """Returns a compact C-like representation of an AST node."""

    if node is None:
        return "<none>"

    match node.kind:
        case NodeKind.NUM:
            return str(node.val)

        case NodeKind.VAR:
            return node.var.name

        case NodeKind.NEG:
            return f"-({formatNode(node.lhs)})"

        case NodeKind.ADD:
            return f"({formatNode(node.lhs)} + {formatNode(node.rhs)})"

        case NodeKind.SUB:
            return f"({formatNode(node.lhs)} - {formatNode(node.rhs)})"

        case NodeKind.MUL:
            return f"({formatNode(node.lhs)} * {formatNode(node.rhs)})"

        case NodeKind.DIV:
            return f"({formatNode(node.lhs)} / {formatNode(node.rhs)})"

        case NodeKind.ASSIGN:
            return f"({formatNode(node.lhs)} = {formatNode(node.rhs)})"

        case NodeKind.EQ:
            return f"({formatNode(node.lhs)} == {formatNode(node.rhs)})"

        case NodeKind.NE:
            return f"({formatNode(node.lhs)} != {formatNode(node.rhs)})"

        case NodeKind.LT:
            return f"({formatNode(node.lhs)} < {formatNode(node.rhs)})"

        case NodeKind.LE:
            return f"({formatNode(node.lhs)} <= {formatNode(node.rhs)})"

        case NodeKind.ADDR:
            return f"&{formatNode(node.lhs)}"

        case NodeKind.DEREF:
            return f"*{formatNode(node.lhs)}"

        case NodeKind.FUNCALL:
            args = ", ".join(formatNode(arg) for arg in node.args)
            return f"{node.funcName}({args})"

        case _:
            return f"<{node.kind.name}>"


def addType(node: Node | None, errorReporter: ErrorReporter) -> None:
    """Annotates the AST with type information.

    Args:
        node (Node | None): The AST node to annotate.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
    """
    if node is None or node.dtype is not None:
        return

    addType(node.lhs, errorReporter)
    addType(node.rhs, errorReporter)
    addType(node.cond, errorReporter)
    addType(node.then, errorReporter)
    addType(node.els, errorReporter)
    addType(node.init, errorReporter)
    addType(node.inc, errorReporter)

    for stmt in node.body:
        addType(stmt, errorReporter)

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
            | NodeKind.NUM
            | NodeKind.FUNCALL
        ):
            node.dtype = dtypeInt

        case NodeKind.VAR:
            node.dtype = node.var.dtype

        case NodeKind.ADDR:
            node.dtype = pointerTo(node.lhs.dtype)

        case NodeKind.DEREF:
            if node.lhs.dtype.kind != DtypeKind.PTR:
                errorReporter.errorTok(
                    node.tok, f"{formatNode(node)} is an invalid pointer dereference"
                )

            node.dtype = node.lhs.dtype.base

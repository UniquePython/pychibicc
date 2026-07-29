from __future__ import annotations

import typing
from dataclasses import dataclass, field, fields
from enum import Enum, auto

from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokens import Token
from pychibicc.syntax.dtypes import Dtype, DtypeKind, dtypeInt, pointerTo

if typing.TYPE_CHECKING:
    from pychibicc.syntax.objects import Obj


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
    STMT_EXPR = auto()  # Statement expression
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

    # Block or statement expression
    body: list[Node] = field(default_factory=list)  # Block

    # Function call
    funcName: str = ""
    args: list[Node] = field(default_factory=list)

    var: Obj | None = None  # Used if kind == NodeKind.VAR
    val: CInt = 0  # Used if kind == NodeKind.NUM

    @property
    def children(self):
        """Iterates over this node's child AST nodes.

        Yields:
            Node: Each child node referenced by this node, including nodes stored
                directly in fields and nodes contained in list-valued fields.
        """
        for nodeField in fields(self):
            value = getattr(self, nodeField.name)

            if isinstance(value, Node):
                yield value
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Node):
                        yield item


def addDtype(node: Node | None, errorReporter: ErrorReporter) -> None:
    """Annotates the AST with type information.

    Args:
        node (Node | None): The AST node to annotate.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
    """
    from pychibicc.syntax.formatting import formatNode

    if node is None or node.dtype is not None:
        return

    for child in node.children:
        addDtype(child, errorReporter)

    match node.kind:
        case NodeKind.ADD | NodeKind.SUB | NodeKind.MUL | NodeKind.DIV | NodeKind.NEG:
            node.dtype = node.lhs.dtype

        case NodeKind.ASSIGN:
            if node.lhs.dtype.kind == DtypeKind.ARRAY:
                errorReporter.errorTok(
                    node.lhs.tok, f"{formatNode(node.lhs)} is not an lvalue"
                )

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
            if node.lhs.dtype.kind == DtypeKind.ARRAY:
                node.dtype = pointerTo(node.lhs.dtype.base)
            else:
                node.dtype = pointerTo(node.lhs.dtype)

        case NodeKind.DEREF:
            if node.lhs.dtype.base is None:
                errorReporter.errorTok(
                    node.tok, f"{formatNode(node)} is an invalid pointer dereference"
                )

            node.dtype = node.lhs.dtype.base

        case NodeKind.STMT_EXPR:
            if node.body:
                stmt = node.body[-1]

                if stmt.kind == NodeKind.EXPR_STMT:
                    node.dtype = stmt.lhs.dtype
                    return

            errorReporter.errorTok(
                node.tok, "statement expression returning void is not supported"
            )

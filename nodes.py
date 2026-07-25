from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from objects import Obj


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
    EXPR_STMT = auto()  # Expression statement
    VAR = auto()  # Variable
    NUM = auto()  # Integer


@dataclass
class Node:
    """Represents a node in the abstract syntax tree (AST)."""

    kind: NodeKind  # Node kind
    lhs: Node | None = None  # Left-hand side
    rhs: Node | None = None  # Right-hand side
    val: int = 0  # Used if kind == NodeKind.NUM
    var: Obj = ""  # Used if kind == NodeKind.VAR

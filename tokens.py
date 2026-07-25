from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """Represents the different kinds of lexical tokens.

    Args:
        Enum (Enum): Base enumeration class.
    """

    PUNCT = auto()  # Punctuators
    NUM = auto()  # Numeric literals
    EOF = auto()  # End-of-file markers


@dataclass
class Token:
    """Represents a lexical token produced by the tokenizer."""

    kind: TokenKind  # Token kind
    val: int = 0  # If kind is NUM, its value
    loc: str = ""  # Token location
    pos: int = 0  # Token starting position
    length: int = 0  # Token length


def equal(tok: Token, op: str) -> bool:
    """Returns whether the given token matches the specified operator.

    Args:
        tok (Token): The token to compare.
        op (str): The operator string to compare against.

    Returns:
        bool: True if the token exactly matches the operator, otherwise False.
    """
    return tok.loc == op

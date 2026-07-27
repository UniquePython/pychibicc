from dataclasses import dataclass
from enum import Enum, auto

from pychibicc.ctype.cint import CInt


class TokenKind(Enum):
    """Represents the different kinds of lexical tokens.

    Args:
        Enum (Enum): Base enumeration class.
    """

    IDENT = auto()  # Identifiers
    PUNCT = auto()  # Punctuators
    KEYWORD = auto()  # Keywords
    NUM = auto()  # Numeric literals
    EOF = auto()  # End-of-file markers


@dataclass
class Token:
    """Represents a lexical token produced by the tokenizer."""

    kind: TokenKind  # Token kind
    val: CInt = 0  # If kind is NUM, its value
    loc: str = ""  # Token location
    pos: CInt = 0  # Token starting position
    length: CInt = 0  # Token length

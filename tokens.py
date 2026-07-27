from dataclasses import dataclass
from enum import Enum, auto

from cint import CInt


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


def equal(tok: Token, op: str) -> bool:
    """Returns whether the given token matches the specified operator.

    Args:
        tok (Token): The token to compare.
        op (str): The operator string to compare against.

    Returns:
        bool: True if the token exactly matches the operator, otherwise False.
    """
    return tok.loc == op


def isIdentFirst(c: str) -> bool:
    """Returns whether the character is valid as the first character of an identifier.

    Args:
        c (str): The character to test.

    Returns:
        bool: True if the character is a valid first identifier character,
            otherwise False.
    """
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def isIdentNonFirst(c: str) -> bool:
    """Returns whether the character is valid as a non-first character of an identifier.

    Args:
        c (str): The character to test.

    Returns:
        bool: True if the character is a valid non-first identifier character,
            otherwise False.
    """
    return isIdentFirst(c) or ("0" <= c <= "9")


def readPunct(source: str) -> CInt:
    """Reads a punctuator from the beginning of the string.

    Args:
        source (str): The source string to read from.

    Returns:
        CInt: The length of the punctuator, or 0 if none is found.
    """
    if source.startswith(("==", "!=", "<=", ">=")):
        return 2

    if source and source[0] in "+-*&/()<>!={}[],;":
        return 1

    return 0


KEYWORDS = {"return", "if", "else", "for", "while", "int"}


def isKeyword(tok: Token) -> bool:
    """Returns whether the specified token is a keyword.

    Args:
        tok (Token): The token to check.

    Returns:
        bool: True if the token is a keyword, otherwise False.
    """
    return tok.loc in KEYWORDS


def convertKeywords(tokens: list[Token]) -> None:
    """Converts identifier tokens that are keywords into keyword tokens.

    Args:
        tokens (list[Token]): The token stream.
    """
    for tok in tokens:
        if tok.kind == TokenKind.EOF:
            break

        if isKeyword(tok):
            tok.kind = TokenKind.KEYWORD

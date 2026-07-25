from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    PUNCT = auto()  # Punctuators
    NUM = auto()  # Numeric literals
    EOF = auto()  # End-of-file markers


@dataclass
class Token:
    kind: TokenKind  # Token kind
    nextToken: Token | None = None  # Next token
    val: int = 0  # If kind is NUM, its value
    loc: str = ""  # Token location
    length: int = 0  # Token length


def error(message: str) -> None:
    """Reports an error and exits.

    Args:
        message (str): The error message to be printed
    """
    print(message, file=sys.stderr)
    sys.exit(1)


def equal(tok: Token, op: str) -> bool:
    """Returns whether the given token matches the specified operator.

    Args:
        tok (Token): The token to compare.
        op (str): The operator string to compare against.

    Returns:
        bool: True if the token exactly matches the operator, otherwise False.
    """
    return tok.loc[: tok.length] == op


def skip(tok: Token, s: str) -> Token:
    """Consumes the current token if it matches the expected string.

    Args:
        tok (Token): The current token.
        s (str): The expected token text.

    Returns:
        Token: The next token after the consumed token.

    Raises:
        SystemExit: If the current token does not match the expected string.
    """
    if not equal(tok, s):
        error(f"expected '{s}'")
    return tok.nextToken


def getNumber(tok: Token) -> int:
    """Returns the numeric value of a number token.

    Args:
        tok (Token): The token whose value is to be retrieved.

    Returns:
        int: The integer value stored in the token.

    Raises:
        SystemExit: If the token is not a number token.
    """
    if tok.kind != TokenKind.NUM:
        error("expected a number")
    return tok.val


def tokenize(source: str) -> Token:
    """Tokenizes the input source into a linked list of tokens.

    Args:
        source (str): The source code to tokenize.

    Returns:
        Token: The head of the token list.
    """
    head = Token(TokenKind.EOF)
    cur = head
    idx = 0

    while idx < len(source):
        # Skip whitespace.
        if source[idx].isspace():
            idx += 1
            continue

        # Numeric literal.
        if source[idx].isdigit():
            start = idx

            while idx < len(source) and source[idx].isdigit():
                idx += 1

            tok = Token(
                kind=TokenKind.NUM,
                val=int(source[start:idx]),
                loc=source[start:idx],
                length=idx - start,
            )

            cur.nextToken = tok
            cur = tok
            continue

        # Punctuator.
        if source[idx] in "+-":
            tok = Token(
                kind=TokenKind.PUNCT,
                loc=source[idx],
                length=1,
            )

            cur.nextToken = tok
            cur = tok
            idx += 1
            continue

        error("invalid token")

    cur.nextToken = Token(TokenKind.EOF)
    return head.nextToken


def main() -> None:
    if len(sys.argv) != 2:
        error(f"{sys.argv[0]}: invalid number of arguments")

    tok = tokenize(sys.argv[1])

    print("\t.globl main")
    print("main:")

    # The first token must be a number.
    print(f"\tmov ${getNumber(tok)}, %rax")
    tok = tok.nextToken

    # ... followed by either `+ <number>` or `- <number>`.
    while tok.kind != TokenKind.EOF:
        if equal(tok, "+"):
            print(f"\tadd ${getNumber(tok.nextToken)}, %rax")
            tok = tok.nextToken.nextToken
            continue

        tok = skip(tok, "-")
        print(f"\tsub ${getNumber(tok)}, %rax")
        tok = tok.nextToken

    print("\tret")


if __name__ == "__main__":
    main()

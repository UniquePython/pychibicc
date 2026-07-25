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
    val: int = 0  # If kind is NUM, its value
    loc: str = ""  # Token location
    pos: int = 0  # Token starting position
    length: int = 0  # Token length


def error(message: str) -> None:
    """Reports an error and exits.

    Args:
        message (str): The error message to be printed.
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
    return tok.loc == op


def skip(tokens: list[Token], s: str) -> None:
    """Consumes the current token if it matches the expected string.

    Args:
        tokens (list[Token]): The remaining token stream.
        s (str): The expected token text.

    Raises:
        SystemExit: If the current token does not match the expected string.
    """
    tok = tokens.pop(0)

    if not equal(tok, s):
        error(f"expected '{s}'")


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


def tokenize(source: str) -> list[Token]:
    """Tokenizes the input source into a list of tokens.

    Args:
        source (str): The source code to tokenize.

    Returns:
        list[Token]: The list of generated tokens.
    """
    tokens: list[Token] = []
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

            tokens.append(
                Token(
                    kind=TokenKind.NUM,
                    val=int(source[start:idx]),
                    loc=source[start:idx],
                    pos=start,
                    length=idx - start,
                )
            )
            continue

        # Punctuator.
        if source[idx] in "+-":
            tokens.append(
                Token(
                    kind=TokenKind.PUNCT,
                    loc=source[idx],
                    pos=idx,
                    length=1,
                )
            )

            idx += 1
            continue

        error("invalid token")

    tokens.append(Token(TokenKind.EOF))
    return tokens


def main() -> None:
    if len(sys.argv) != 2:
        error(f"{sys.argv[0]}: invalid number of arguments")

    tokens = tokenize(sys.argv[1])

    print("\t.globl main")
    print("main:")

    # The first token must be a number.
    print(f"\tmov ${getNumber(tokens.pop(0))}, %rax")

    # ... followed by either `+ <number>` or `- <number>`.
    while tokens[0].kind != TokenKind.EOF:
        if equal(tokens[0], "+"):
            tokens.pop(0)
            print(f"\tadd ${getNumber(tokens.pop(0))}, %rax")
            continue

        skip(tokens, "-")
        print(f"\tsub ${getNumber(tokens.pop(0))}, %rax")

    print("\tret")


if __name__ == "__main__":
    main()

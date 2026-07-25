from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum, auto

# ===================================================
# ==================== TOKENIZER ====================
# ===================================================


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


def error(message: str) -> None:
    """Reports an error and exits.

    Args:
        message (str): The error message to be printed.
    """
    print(message, file=sys.stderr)
    sys.exit(1)


def errorAt(pos: int, message: str) -> None:
    """Reports an error at the specified position and exits.

    Args:
        pos (int): The position at which the error occurred.
        message (str): The error message to be printed.
    """
    print(currentInput, file=sys.stderr)
    print(" " * pos + "^ " + message, file=sys.stderr)
    sys.exit(1)


def errorTok(tok: Token, message: str) -> None:
    """Reports an error at the specified token and exits.

    Args:
        tok (Token): The token at which the error occurred.
        message (str): The error message to be printed.
    """
    errorAt(tok.pos, message)


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
        errorTok(tok, f"expected '{s}")


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
        errorTok(tok, "expected a number")

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
        if source[idx] in "+-*/()":
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

        errorAt(idx, "invalid token")

    tokens.append(Token(TokenKind.EOF))
    return tokens


# ================================================
# ==================== PARSER ====================
# ================================================


class NodeKind(Enum):
    """Represents the different kinds of abstract syntax tree (AST) nodes.

    Args:
        Enum (Enum): Base enumeration class.
    """

    ADD = auto()  # +
    SUB = auto()  # -
    MUL = auto()  # *
    DIV = auto()  # /
    NUM = auto()  # Integer


@dataclass
class Node:
    """Represents a node in the abstract syntax tree (AST)."""

    kind: NodeKind  # Node kind
    lhs: Node | None = None  # Left hand side
    rhs: Node | None = None  # Right hand side
    val: int = 0  # Used if kind == NodeKind.NUM


def expr(tokens: list[Token]) -> Node:
    """Parses an expression.

    ## Grammar:
        expr = mul ("+" mul | "-" mul)*

    Args:
        tokens (list[Token]): The remaining token stream.

    Returns:
        Node: The root node of the parsed expression.
    """
    node = mul(tokens)

    while True:
        if equal(tokens[0], "+"):
            tokens.pop(0)
            node = Node(kind=NodeKind.ADD, lhs=node, rhs=mul(tokens))
            continue

        if equal(tokens[0], "-"):
            tokens.pop(0)
            node = Node(kind=NodeKind.SUB, lhs=node, rhs=mul(tokens))
            continue

        return node


def mul(tokens: list[Token]) -> Node:
    """Parses a multiplication or division expression.

    ## Grammar:
        mul = primary ("*" primary | "/" primary)*

    Args:
        tokens (list[Token]): The remaining token stream.

    Returns:
        Node: The root node of the parsed expression.
    """
    node = primary(tokens)

    while True:
        if equal(tokens[0], "*"):
            tokens.pop(0)
            node = Node(kind=NodeKind.MUL, lhs=node, rhs=primary(tokens))
            continue

        if equal(tokens[0], "/"):
            tokens.pop(0)
            node = Node(kind=NodeKind.DIV, lhs=node, rhs=primary(tokens))
            continue

        return node


def primary(tokens: list[Token]) -> Node:
    """Parses a primary expression.

    ## Grammar:
        primary = "(" expr ")" | num

    Args:
        tokens (list[Token]): The remaining token stream.

    Returns:
        Node: The root node of the parsed expression.

    Raises:
        SystemExit: If no valid primary expression is found.
    """
    if equal(tokens[0], "("):
        tokens.pop(0)
        node = expr(tokens)
        skip(tokens, ")")
        return node

    tok = tokens[0]

    if tok.kind == TokenKind.NUM:
        tokens.pop(0)
        return Node(kind=NodeKind.NUM, val=tok.val)

    errorTok(tok, "expected an expression")


# ========================================================
# ==================== CODE GENERATOR ====================
# ========================================================

depth = 0


def push() -> None:
    """Pushes the value in %rax onto the stack."""
    global depth

    print("\tpush %rax")
    depth += 1


def pop(arg: str) -> None:
    """Pops the top value from the stack into the specified register.

    Args:
        arg (str): The destination register.
    """
    global depth

    print(f"\tpop {arg}")
    depth -= 1


def genExpr(node: Node) -> None:
    """Generates assembly code for an expression.

    Args:
        node (Node): The root node of the expression to generate.

    Raises:
        SystemExit: If the expression node kind is invalid.
    """
    if node.kind == NodeKind.NUM:
        print(f"\tmov ${node.val}, %rax")
        return

    genExpr(node.rhs)
    push()
    genExpr(node.lhs)
    pop("%rdi")

    match node.kind:
        case NodeKind.ADD:
            print("\tadd %rdi, %rax")
            return

        case NodeKind.SUB:
            print("\tsub %rdi, %rax")
            return

        case NodeKind.MUL:
            print("\timul %rdi, %rax")
            return

        case NodeKind.DIV:
            print("\tcqo")
            print("\tidiv %rdi")
            return

    error("invalid expression")


def main() -> None:
    global currentInput

    if len(sys.argv) != 2:
        error(f"{sys.argv[0]}: invalid number of arguments")

    # Tokenize and parse.
    currentInput = sys.argv[1]
    tokens = tokenize(currentInput)
    node = expr(tokens)

    if tokens[0].kind != TokenKind.EOF:
        errorTok(tokens[0], "extra token")

    print("\t.globl main")
    print("main:")

    depth = 0

    # Traverse the AST to emit assembly.
    genExpr(node)
    print("\tret")

    assert depth == 0


if __name__ == "__main__":
    main()

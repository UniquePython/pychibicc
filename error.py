import sys

from tokens import Token


def error(message: str) -> None:
    """Reports an error and exits.

    Args:
        message (str): The error message to be printed.
    """
    print(message, file=sys.stderr)
    sys.exit(1)


def errorAt(source: str, pos: int, message: str) -> None:
    """Reports an error at the specified position and exits.

    Args:
        source (str): The source code in which the error was found.
        pos (int): The position at which the error occurred.
        message (str): The error message to be printed.
    """
    print(source, file=sys.stderr)
    print(" " * pos + "^ " + message, file=sys.stderr)
    sys.exit(1)


def errorTok(source: str, tok: Token, message: str) -> None:
    """Reports an error at the specified token and exits.

    Args:
        source (str): The source code in which the error was found.
        tok (Token): The token at which the error occurred.
        message (str): The error message to be printed.
    """
    errorAt(source, tok.pos, message)

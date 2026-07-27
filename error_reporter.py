import sys

from cint import CInt
from tokens import Token


class ErrorReporter:
    def __init__(self, source: str) -> None:
        """Initializes the error reporter

        Args:
            source (str): The source code in which the error was found.
        """
        self.source = source

    @staticmethod
    def error(message: str) -> None:
        """Reports an error and exits.

        Args:
            message (str): The error message to be printed.
        """
        print(message, file=sys.stderr)
        sys.exit(1)

    def errorAt(self, pos: CInt, message: str) -> None:
        """Reports an error at the specified position and exits.

        Args:
            pos (CInt): The position at which the error occurred.
            message (str): The error message to be printed.
        """
        print(self.source, file=sys.stderr)
        print(" " * pos + "^ " + message, file=sys.stderr)
        sys.exit(1)

    def errorTok(self, tok: Token, message: str) -> None:
        """Reports an error at the specified token and exits.

        Args:
            tok (Token): The token at which the error occurred.
            message (str): The error message to be printed.
        """
        self.errorAt(tok.pos, message)

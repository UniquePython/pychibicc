import sys

from pychibicc.ctype.cint import CInt
from pychibicc.frontend.tokens import Token


class ErrorReporter:
    def __init__(self, source: str, filename: str = "<stdin>") -> None:
        """Initializes the error reporter

        Args:
            source (str): The source code in which the error was found.
            filename (str): The name of the file the source came from, used
                to prefix error messages (e.g. "foo.c:10: ..."). Defaults to
                "<stdin>" for source that didn't come from a real file.
        """
        self.source = source
        self.filename = filename

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

        Prints a message in the form:
            ```
            foo.c:10: x = y + 1;
                          ^ <message>
            ```

        Only the offending line is shown, prefixed with the filename and
        1-based line number, with the caret aligned under the error
        position.

        Args:
            pos (CInt): The position at which the error occurred.
            message (str): The error message to be printed.
        """
        pos = int(pos)

        # Find the start of the line containing `pos` by scanning backward
        # to the previous newline (or the start of the source).
        lineStart = pos
        while lineStart > 0 and self.source[lineStart - 1] != "\n":
            lineStart -= 1

        # Find the end of that line by scanning forward to the next newline.
        lineEnd = pos
        while lineEnd < len(self.source) and self.source[lineEnd] != "\n":
            lineEnd += 1

        # Count newlines before the line to get a 1-based line number.
        lineNo = 1 + self.source.count("\n", 0, lineStart)

        prefix = f"{self.filename}:{lineNo}: "
        print(prefix + self.source[lineStart:lineEnd], file=sys.stderr)

        column = pos - lineStart + len(prefix)
        print(" " * column + "^ " + message, file=sys.stderr)
        sys.exit(1)

    def errorTok(self, tok: Token, message: str) -> None:
        """Reports an error at the specified token and exits.

        Args:
            tok (Token): The token at which the error occurred.
            message (str): The error message to be printed.
        """
        self.errorAt(tok.pos, message)

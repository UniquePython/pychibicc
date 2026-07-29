import sys

from dight.ctype.cint import CInt
from dight.frontend.tokens import Token

_WHITE = "\033[97m"
_GREEN = "\033[32m"
_BOLD_RED = "\033[1;31m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


def _colorsEnabled() -> bool:
    """Determines whether ANSI color codes should be emitted.

    Returns:
        bool: True if stderr is a terminal that supports color, otherwise
            False (e.g. when output is piped or redirected).
    """
    return sys.stderr.isatty()


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
        if _colorsEnabled():
            message = f"{_YELLOW}{message}{_RESET}"

        print(message, file=sys.stderr)
        sys.exit(1)

    def errorAt(self, pos: CInt, message: str, length: CInt = 1) -> None:
        """Reports an error at the specified position and exits.

        Prints a message in the form:
            ```
            foo.c:10: x = y + 1;
                          ^ <message>
            ```

        Only the offending line is shown, prefixed with the filename and
        1-based line number, with the caret aligned under the error
        position. When color is enabled, the prefix is dim gray, the
        source line is green (with the offending span in bold red), the
        caret is bold red, and the message is yellow.

        Args:
            pos (CInt): The position at which the error occurred.
            message (str): The error message to be printed.
            length (CInt): The length of the offending span, used to
                highlight it within the source line. Defaults to 1 (a
                single character).
        """
        pos = int(pos)
        length = max(1, int(length))

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
        line = self.source[lineStart:lineEnd]

        # Clamp the offending span to stay within the line's bounds.
        spanStart = pos - lineStart
        spanEnd = min(spanStart + length, len(line))

        if _colorsEnabled():
            coloredPrefix = f"{_WHITE}{prefix}{_RESET}"
            coloredLine = (
                f"{_GREEN}{line[:spanStart]}{_RESET}"
                f"{_BOLD_RED}{line[spanStart:spanEnd]}{_RESET}"
                f"{_GREEN}{line[spanEnd:]}{_RESET}"
            )
            print(coloredPrefix + coloredLine, file=sys.stderr)

            caret = f"{_BOLD_RED}^{_RESET} {_YELLOW}{message}{_RESET}"
        else:
            print(prefix + line, file=sys.stderr)
            caret = "^ " + message

        column = pos - lineStart + len(prefix)
        print(" " * column + caret, file=sys.stderr)
        sys.exit(1)

    def errorTok(self, tok: Token, message: str) -> None:
        """Reports an error at the specified token and exits.

        Args:
            tok (Token): The token at which the error occurred.
            message (str): The error message to be printed.
        """
        self.errorAt(tok.pos, message, tok.length)

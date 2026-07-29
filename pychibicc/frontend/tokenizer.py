from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokens import Token, TokenKind
from pychibicc.syntax.dtypes import arrayOf, dtypeChar


def _isIdentFirst(c: str) -> bool:
    """Returns whether the character is valid as the first character of an identifier.

    Args:
        c (str): The character to test.

    Returns:
        bool: True if the character is a valid first identifier character,
            otherwise False.
    """
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


def _isIdentNonFirst(c: str) -> bool:
    """Returns whether the character is valid as a non-first character of an identifier.

    Args:
        c (str): The character to test.

    Returns:
        bool: True if the character is a valid non-first identifier character,
            otherwise False.
    """
    return _isIdentFirst(c) or ("0" <= c <= "9")


def _fromHex(c: str) -> int:
    """Converts a hexadecimal digit to its integer value.

    Args:
        c (str): A hexadecimal digit.

    Returns:
        int: The digit's value.
    """
    if "0" <= c <= "9":
        return ord(c) - ord("0")

    if "a" <= c <= "f":
        return ord(c) - ord("a") + 10

    return ord(c) - ord("A") + 10


def _isHexDigit(c: str) -> bool:
    return c.lower() in "0123456789abcdef"


_TWO_CHAR_PUNCTS = {
    "==",
    "!=",
    "<=",
    ">=",
}

_SINGLE_CHAR_PUNCTS = {
    "+",
    "-",
    "*",
    "&",
    "/",
    "(",
    ")",
    "<",
    ">",
    "!",
    "=",
    "{",
    "}",
    "[",
    "]",
    ",",
    ";",
}


def _readPunct(source: str) -> CInt:
    """Reads a punctuator from the beginning of the string.

    Args:
        source (str): The source string to read from.

    Returns:
        CInt: The length of the punctuator, or 0 if none is found.
    """
    if source[:2] in _TWO_CHAR_PUNCTS:
        return CInt(2)
    elif source[:1] in _SINGLE_CHAR_PUNCTS:
        return CInt(1)
    else:
        return CInt(0)


_TYPE_NAMES = {
    "int",
    "char",
}


_KEYWORDS = {
    "return",
    "if",
    "else",
    "_Unless",
    "for",
    "while",
    "_Until",
    "_Loop",
    "_Forever",
    "_Infer",
    "sizeof",
    "_Constexpr",
    *_TYPE_NAMES,
}


def isTypename(tok: Token) -> bool:
    """Returns whether the given token is a type name or not.

    Args:
        tok (Token): The token to compare.

    Returns:
        bool: True if the token exactly matches a type name, otherwise False.
    """
    return tok.lexeme in _TYPE_NAMES


_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "t": "\t",
    "n": "\n",
    "v": "\v",
    "f": "\f",
    "r": "\r",
    "e": chr(27),  # GNU extension
}


class Tokenizer:
    """Tokenizes source code into a sequence of lexical tokens."""

    def __init__(self, errorReporter: ErrorReporter):
        """Initializes the tokenizer.

        Args:
            errorReporter (ErrorReporter): The error reporter initialized with the source code to tokenize.
        """
        self._errorReporter = errorReporter
        self._source = self._errorReporter.source

    def _readEscapedChar(self, idx: int) -> tuple[str, int]:
        """Reads an escaped character.

        Args:
            idx (int): Index of the character immediately following the backslash.

        Returns:
            tuple[str, int]: The decoded character and the index of the next unread character.
        """
        # Octal escape sequence.
        if "0" <= self._source[idx] <= "7":
            c = 0

            for _ in range(3):
                if idx >= len(self._source) or not ("0" <= self._source[idx] <= "7"):
                    break

                c = (c << 3) + (ord(self._source[idx]) - ord("0"))
                idx += 1

            return chr(c), idx

        if self._source[idx] == "x":
            # Read a hexadecimal number.
            idx += 1

            if idx >= len(self._source) or not _isHexDigit(self._source[idx]):
                self._errorReporter.errorAt(idx, "invalid hex escape sequence")

            c = 0

            while idx < len(self._source):
                ch = self._source[idx]
                if not _isHexDigit(ch):
                    break

                c = (c << 4) + _fromHex(ch)
                idx += 1

            return chr(c), idx

        return _ESCAPES.get(self._source[idx], self._source[idx]), idx + 1

    def _stringLiteralEnd(self, start: int) -> int:
        """Finds the closing double quote of a string literal.

        Args:
            start (int): Index immediately after the opening quote.

        Returns:
            int: Index of the closing quote.

        Raises:
            SystemExit: If the string literal is unterminated.
        """
        idx = start

        while idx < len(self._source):
            ch = self._source[idx]

            if ch == '"':
                return idx
            if ch == "\n":
                break
            if ch == "\\":
                idx += 1
                if idx >= len(self._source):
                    break
            idx += 1

        self._errorReporter.errorAt(start - 1, "unclosed string literal")

    def _readStringLiteral(self, start: int) -> tuple[Token, int]:
        """Tokenizes a string literal.

        Args:
            start (int): Index of the opening double quote.

        Returns:
            tuple[Token, int]:
                The string literal token and the index immediately after the
                closing quote.
        """
        end = self._stringLiteralEnd(start + 1)

        chars: list[str] = []
        idx = start + 1

        while idx < end:
            if self._source[idx] == "\\":
                ch, idx = self._readEscapedChar(idx + 1)
                chars.append(ch)
            else:
                chars.append(self._source[idx])
                idx += 1

        string = "".join(chars)

        tok = Token(
            kind=TokenKind.STR,
            lexeme=self._source[start : end + 1],
            pos=start,
            length=end - start + 1,
        )

        # +1 for the terminating '\0', just like chibicc.
        tok.dtype = arrayOf(dtypeChar, len(string) + 1)
        tok.string = string + "\0"

        return tok, end + 1

    def tokenize(self) -> list[Token]:
        """Tokenizes the source code into a list of tokens.

        Returns:
            list[Token]: The list of generated tokens.
        """
        tokens: list[Token] = []
        idx = 0

        while idx < len(self._source):
            # Skip line comments.
            if self._source.startswith("//", idx):
                idx += 2

                while idx < len(self._source) and self._source[idx] != "\n":
                    idx += 1

                continue

            # Skip block comments.
            if self._source.startswith("/*", idx):
                end = self._source.find("*/", idx + 2)

                if end == -1:
                    self._errorReporter.errorAt(idx, "unclosed block comment")

                idx = end + 2
                continue

            # Skip whitespace.
            if self._source[idx].isspace():
                idx += 1
                continue

            # Numeric literal.
            if self._source[idx].isdigit():
                start = idx

                while idx < len(self._source) and self._source[idx].isdigit():
                    idx += 1

                tokens.append(
                    Token(
                        kind=TokenKind.NUM,
                        val=CInt(self._source[start:idx]),
                        lexeme=self._source[start:idx],
                        pos=start,
                        length=idx - start,
                    )
                )
                continue

            # String literal.
            if self._source[idx] == '"':
                tok, idx = self._readStringLiteral(idx)
                tokens.append(tok)
                continue

            # Identifier or Keyword
            if _isIdentFirst(self._source[idx]):
                start = idx

                while idx < len(self._source) and _isIdentNonFirst(self._source[idx]):
                    idx += 1

                lexeme = self._source[start:idx]

                tokens.append(
                    Token(
                        kind=TokenKind.KEYWORD
                        if lexeme in _KEYWORDS
                        else TokenKind.IDENT,
                        lexeme=lexeme,
                        pos=start,
                        length=idx - start,
                    )
                )

                continue

            # Punctuators.
            punctLength = _readPunct(self._source[idx:])

            if punctLength:
                tokens.append(
                    Token(
                        kind=TokenKind.PUNCT,
                        lexeme=self._source[idx : idx + punctLength],
                        pos=idx,
                        length=punctLength,
                    )
                )

                idx += punctLength
                continue

            self._errorReporter.errorAt(idx, f"invalid token: '{self._source[idx]}'")

        tokens.append(Token(TokenKind.EOF, pos=len(self._source)))
        return tokens

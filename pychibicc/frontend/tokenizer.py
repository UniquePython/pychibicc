from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokens import Token, TokenKind


def equal(tok: Token, op: str) -> bool:
    """Returns whether the given token matches the specified operator.

    Args:
        tok (Token): The token to compare.
        op (str): The operator string to compare against.

    Returns:
        bool: True if the token exactly matches the operator, otherwise False.
    """
    return tok.loc == op


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


def _readPunct(source: str) -> CInt:
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


_KEYWORDS = {"return", "if", "else", "for", "while", "int"}


def _isKeyword(tok: Token) -> bool:
    """Returns whether the specified token is a keyword.

    Args:
        tok (Token): The token to check.

    Returns:
        bool: True if the token is a keyword, otherwise False.
    """
    return tok.loc in _KEYWORDS


def _convertKeywords(tokens: list[Token]) -> None:
    """Converts identifier tokens that are keywords into keyword tokens.

    Args:
        tokens (list[Token]): The token stream.
    """
    for tok in tokens:
        if tok.kind == TokenKind.EOF:
            break

        if _isKeyword(tok):
            tok.kind = TokenKind.KEYWORD


class Tokenizer:
    """Tokenizes source code into a sequence of lexical tokens."""

    def __init__(self, errorReporter: ErrorReporter):
        """Initializes the tokenizer.

        Args:
            errorReporter (ErrorReporter): The error reporter initialized with the source code to tokenize.
        """
        self._errorReporter = errorReporter
        self._source = self._errorReporter.source

    def tokenize(self) -> list[Token]:
        """Tokenizes the source code into a list of tokens.

        Returns:
            list[Token]: The list of generated tokens.
        """
        tokens: list[Token] = []
        idx = 0

        while idx < len(self._source):
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
                        loc=self._source[start:idx],
                        pos=start,
                        length=idx - start,
                    )
                )
                continue

            # Identifier or Keyword
            if _isIdentFirst(self._source[idx]):
                start = idx

                while idx < len(self._source) and _isIdentNonFirst(self._source[idx]):
                    idx += 1

                tokens.append(
                    Token(
                        kind=TokenKind.IDENT,
                        loc=self._source[start:idx],
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
                        loc=self._source[idx : idx + punctLength],
                        pos=idx,
                        length=punctLength,
                    )
                )

                idx += punctLength
                continue

            self._errorReporter.errorAt(idx, "invalid token")

        tokens.append(Token(TokenKind.EOF, pos=len(self._source)))
        _convertKeywords(tokens)
        return tokens

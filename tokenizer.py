from error_reporter import ErrorReporter
from tokens import (
    Token,
    TokenKind,
    convertKeywords,
    isIdentFirst,
    isIdentNonFirst,
    readPunct,
)


class Tokenizer:
    """Tokenizes source code into a sequence of lexical tokens."""

    def __init__(self, errorReporter: ErrorReporter):
        """Initializes the tokenizer.

        Args:
            errorReporter (ErrorReporter): The error reporter initialized with the source code to tokenize.
        """
        self.errorReporter = errorReporter
        self.source = self.errorReporter.source

    def getNumber(self, tok: Token) -> int:
        """Returns the numeric value of a number token.

        Args:
            tok (Token): The token whose value is to be retrieved.

        Returns:
            int: The integer value stored in the token.

        Raises:
            SystemExit: If the token is not a number token.
        """
        if tok.kind != TokenKind.NUM:
            self.errorReporter.errorTok(tok, "expected a number")

        return tok.val

    def tokenize(self) -> list[Token]:
        """Tokenizes the source code into a list of tokens.

        Returns:
            list[Token]: The list of generated tokens.
        """
        tokens: list[Token] = []
        idx = 0

        while idx < len(self.source):
            # Skip whitespace.
            if self.source[idx].isspace():
                idx += 1
                continue

            # Numeric literal.
            if self.source[idx].isdigit():
                start = idx

                while idx < len(self.source) and self.source[idx].isdigit():
                    idx += 1

                tokens.append(
                    Token(
                        kind=TokenKind.NUM,
                        val=int(self.source[start:idx]),
                        loc=self.source[start:idx],
                        pos=start,
                        length=idx - start,
                    )
                )
                continue

            # Identifier or Keyword
            if isIdentFirst(self.source[idx]):
                start = idx

                while idx < len(self.source) and isIdentNonFirst(self.source[idx]):
                    idx += 1

                tokens.append(
                    Token(
                        kind=TokenKind.IDENT,
                        loc=self.source[start:idx],
                        pos=start,
                        length=idx - start,
                    )
                )

                continue

            # Punctuators.
            punctLength = readPunct(self.source[idx:])

            if punctLength:
                tokens.append(
                    Token(
                        kind=TokenKind.PUNCT,
                        loc=self.source[idx : idx + punctLength],
                        pos=idx,
                        length=punctLength,
                    )
                )

                idx += punctLength
                continue

            self.errorReporter.errorAt(idx, "invalid token")

        tokens.append(Token(TokenKind.EOF, pos=len(self.source)))
        convertKeywords(tokens)
        return tokens

from error import errorAt, errorTok
from tokens import Token, TokenKind


class Tokenizer:
    """Tokenizes source code into a sequence of lexical tokens."""

    def __init__(self, source: str):
        """Initializes the tokenizer.

        Args:
            source (str): The source code to tokenize.
        """
        self.source = source

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
            errorTok(self.source, tok, "expected a number")

        return tok.val

    @staticmethod
    def readPunct(source: str) -> int:
        """Reads a punctuator from the beginning of the string.

        Args:
            source (str): The source string to read from.

        Returns:
            int: The length of the punctuator, or 0 if none is found.
        """
        if source.startswith(("==", "!=", "<=", ">=")):
            return 2

        if source and source[0] in "+-*/()<>!={}[],;":
            return 1

        return 0

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

            # Identifier.
            if "a" <= self.source[idx] <= "z":
                tokens.append(
                    Token(
                        kind=TokenKind.IDENT,
                        loc=self.source[idx],
                        pos=idx,
                        length=1,
                    )
                )

                idx += 1
                continue

            # Punctuators.
            punctLength = self.readPunct(self.source[idx:])

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

            errorAt(self.source, idx, "invalid token")

        tokens.append(Token(TokenKind.EOF, pos=len(self.source)))
        return tokens

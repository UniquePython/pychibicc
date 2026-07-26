from collections import deque

from error_reporter import ErrorReporter
from functions import Function
from nodes import Node, NodeKind
from objects import Obj
from tokens import Token, TokenKind, equal


class Parser:
    """Parses a token stream into an abstract syntax tree (AST)."""

    def __init__(self, errorReporter: ErrorReporter, tokens: list[Token]):
        """Initializes the parser.

        Args:
            errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
            tokens (list[Token]): The token stream to parse.
        """
        self.errorReporter = errorReporter
        self.tokens: deque[Token] = deque(tokens)
        self.locals: list[Obj] = []

    def skip(self, s: str) -> None:
        """Consumes the current token if it matches the expected string.

        Args:
            s (str): The expected token text.

        Raises:
            SystemExit: If the current token does not match the expected string.
        """
        tok = self.tokens.popleft()

        if not equal(tok, s):
            self.errorReporter.errorTok(tok, f"expected '{s}'")

    def findVar(self, tok: Token) -> Obj | None:
        """Finds a local variable by name.

        Args:
            tok (Token): The identifier token to search for.

        Returns:
            Obj | None: The matching local variable, or None if no match is found.
        """
        for var in self.locals:
            if var.name == tok.loc:
                return var

        return None

    def stmt(self) -> Node:
        """Parses a statement.

        ## Grammar:
            ```
            stmt = "return" expr ";"
                | "if" "(" expr ")" stmt ("else" stmt)?
                | "for" "(" expr-stmt expr? ";" expr? ")" stmt
                | "while" "(" expr ")" stmt
                | "{" compound-stmt
                | expr-stmt
            ```

        Returns:
            Node: The root node of the parsed statement.
        """
        if equal(self.tokens[0], "return"):
            tok = self.tokens.popleft()

            node = Node(
                kind=NodeKind.RETURN,
                tok=tok,
                lhs=self.expr(),
            )

            self.skip(";")
            return node

        if equal(self.tokens[0], "if"):
            tok = self.tokens.popleft()

            node = Node(kind=NodeKind.IF, tok=tok)

            self.skip("(")
            node.cond = self.expr()
            self.skip(")")

            node.then = self.stmt()

            if equal(self.tokens[0], "else"):
                self.tokens.popleft()
                node.els = self.stmt()

            return node

        if equal(self.tokens[0], "for"):
            tok = self.tokens.popleft()

            node = Node(kind=NodeKind.FOR, tok=tok)

            self.skip("(")

            node.init = self.exprStmt()

            if not equal(self.tokens[0], ";"):
                node.cond = self.expr()
            self.skip(";")

            if not equal(self.tokens[0], ")"):
                node.inc = self.expr()
            self.skip(")")

            node.then = self.stmt()
            return node

        if equal(self.tokens[0], "while"):
            tok = self.tokens.popleft()

            node = Node(kind=NodeKind.FOR, tok=tok)

            self.skip("(")
            node.cond = self.expr()
            self.skip(")")

            node.then = self.stmt()
            return node

        if equal(self.tokens[0], "{"):
            tok = self.tokens.popleft()
            return self.compoundStmt(tok)

        return self.exprStmt()

    def compoundStmt(self, tok: Token) -> Node:
        """Parses a compound statement.

        ## Grammar:
            ```
            compound-stmt = stmt* "}"
            ```

        Args:
            tok (Token): The "{" token that opened this block.

        Returns:
            Node: The root node of the parsed compound statement.
        """
        body: list[Node] = []

        while not equal(self.tokens[0], "}"):
            body.append(self.stmt())

        self.skip("}")

        return Node(
            kind=NodeKind.BLOCK,
            tok=tok,
            body=body,
        )

    def exprStmt(self) -> Node:
        """Parses an expression statement.

        ## Grammar:
            ```
            expr-stmt = expr? ";"
            ```

        Returns:
            Node: The root node of the parsed expression statement.
        """
        if equal(self.tokens[0], ";"):
            tok = self.tokens.popleft()
            return Node(kind=NodeKind.BLOCK, tok=tok)

        tok = self.tokens[0]

        node = Node(
            kind=NodeKind.EXPR_STMT,
            tok=tok,
            lhs=self.expr(),
        )

        self.skip(";")
        return node

    def expr(self) -> Node:
        """Parses an expression.

        ## Grammar:
            ```
            expr = assign
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        return self.assign()

    def assign(self) -> Node:
        """Parses an assignment expression.

        ## Grammar:
            ```
            assign = equality ("=" assign)?
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self.equality()

        if equal(self.tokens[0], "="):
            tok = self.tokens.popleft()
            node = Node(
                kind=NodeKind.ASSIGN,
                tok=tok,
                lhs=node,
                rhs=self.assign(),
            )

        return node

    def equality(self) -> Node:
        """Parses an equality expression.

        ## Grammar:
            ```
            equality = relational ("==" relational | "!=" relational)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self.relational()

        while True:
            start = self.tokens[0]

            if equal(self.tokens[0], "=="):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.EQ,
                    tok=start,
                    lhs=node,
                    rhs=self.relational(),
                )
                continue

            if equal(self.tokens[0], "!="):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.NE,
                    tok=start,
                    lhs=node,
                    rhs=self.relational(),
                )
                continue

            return node

    def relational(self) -> Node:
        """Parses a relational expression.

        ## Grammar:
            ```
            relational = add ("<" add | "<=" add | ">" add | ">=" add)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self.add()

        while True:
            start = self.tokens[0]

            if equal(self.tokens[0], "<"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.LT,
                    tok=start,
                    lhs=node,
                    rhs=self.add(),
                )
                continue

            if equal(self.tokens[0], "<="):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.LE,
                    tok=start,
                    lhs=node,
                    rhs=self.add(),
                )
                continue

            if equal(self.tokens[0], ">"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.LT,
                    tok=start,
                    lhs=self.add(),
                    rhs=node,
                )
                continue

            if equal(self.tokens[0], ">="):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.LE,
                    tok=start,
                    lhs=self.add(),
                    rhs=node,
                )
                continue

            return node

    def add(self) -> Node:
        """Parses an addition or subtraction expression.

        ## Grammar:
            ```
            add = mul ("+" mul | "-" mul)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self.mul()

        while True:
            start = self.tokens[0]

            if equal(self.tokens[0], "+"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.ADD,
                    tok=start,
                    lhs=node,
                    rhs=self.mul(),
                )
                continue

            if equal(self.tokens[0], "-"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.SUB,
                    tok=start,
                    lhs=node,
                    rhs=self.mul(),
                )
                continue

            return node

    def mul(self) -> Node:
        """Parses a multiplication or division expression.

        ## Grammar:
            ```
            mul = unary ("*" unary | "/" unary)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self.unary()

        while True:
            start = self.tokens[0]

            if equal(self.tokens[0], "*"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.MUL,
                    tok=start,
                    lhs=node,
                    rhs=self.unary(),
                )
                continue

            if equal(self.tokens[0], "/"):
                self.tokens.popleft()
                node = Node(
                    kind=NodeKind.DIV,
                    tok=start,
                    lhs=node,
                    rhs=self.unary(),
                )
                continue

            return node

    def unary(self) -> Node:
        """Parses a unary expression.

        ## Grammar:
            ```
            unary = ("+" | "-" | "*" | "&") unary
                    | primary
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        if equal(self.tokens[0], "+"):
            self.tokens.popleft()
            return self.unary()

        if equal(self.tokens[0], "-"):
            tok = self.tokens.popleft()
            return Node(
                kind=NodeKind.NEG,
                tok=tok,
                lhs=self.unary(),
            )

        if equal(self.tokens[0], "&"):
            tok = self.tokens.popleft()
            return Node(
                kind=NodeKind.ADDR,
                tok=tok,
                lhs=self.unary(),
            )

        if equal(self.tokens[0], "*"):
            tok = self.tokens.popleft()
            return Node(
                kind=NodeKind.DEREF,
                tok=tok,
                lhs=self.unary(),
            )

        return self.primary()

    def primary(self) -> Node:
        """Parses a primary expression.

        ## Grammar:
            ```
            primary = "(" expr ")" | ident | num
            ```

        Returns:
            Node: The root node of the parsed expression.

        Raises:
            SystemExit: If no valid primary expression is found.
        """
        if equal(self.tokens[0], "("):
            self.tokens.popleft()
            node = self.expr()
            self.skip(")")
            return node

        tok = self.tokens[0]

        if tok.kind == TokenKind.IDENT:
            var = self.findVar(tok)

            if var is None:
                var = Obj(name=tok.loc)
                self.locals.append(var)

            self.tokens.popleft()
            return Node(
                kind=NodeKind.VAR,
                tok=tok,
                var=var,
            )

        if tok.kind == TokenKind.NUM:
            self.tokens.popleft()
            return Node(
                kind=NodeKind.NUM,
                tok=tok,
                val=tok.val,
            )

        self.errorReporter.errorTok(tok, "expected an expression")

    def parse(self) -> Function:
        """Parses the token stream.

        ## Grammar:
            ```
            program = "{" stmt* "}"
            ```

        Returns:
            Function: The parsed function.
        """
        tok = self.tokens[0]
        self.skip("{")

        return Function(
            body=self.compoundStmt(tok),
            locals=self.locals,
        )

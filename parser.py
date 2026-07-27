from collections import deque

from dtypes import Dtype, arrayOf, copyType, dtypeInt, funcType, pointerTo
from error_reporter import ErrorReporter
from functions import Function
from node_constructors import (
    newAdd,
    newBinary,
    newBlock,
    newFuncall,
    newNode,
    newNum,
    newSub,
    newUnary,
    newVarNode,
)
from nodes import Node, NodeKind, addType
from objects import Obj
from tokens import Token, TokenKind, equal


def getIdent(tok: Token, errorReporter: ErrorReporter) -> str:
    """Extracts the identifier name from a token, erroring if it isn't one.

    Args:
        tok (Token): The token to extract from.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.

    Returns:
        str: The identifier's name.

    Raises:
        SystemExit: If the token is not an identifier.
    """
    if tok.kind != TokenKind.IDENT:
        errorReporter.errorTok(tok, "expected an identifier")

    return tok.loc


def getNumber(tok: Token, errorReporter: ErrorReporter) -> int:
    """Extracts a number from a token, erroring if it isn't one.

    Args:
        tok (Token): The token to extract from.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.

    Returns:
        int: The number.

    Raises:
        SystemExit: If the token is not an identifier.
    """
    if tok.kind != TokenKind.NUM:
        errorReporter.errorTok(tok, "expected a number")

    return tok.loc


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

    def expect(self, s: str) -> None:
        """Consumes the current token if it matches the expected string.

        Args:
            s (str): The expected token text.

        Raises:
            SystemExit: If the current token does not match the expected string.
        """
        tok = self.tokens.popleft()

        if not equal(tok, s):
            self.errorReporter.errorTok(tok, f"expected '{s}'")

    def consume(self, s: str) -> bool:
        """Consumes the current token if it matches the expected string.

        Args:
            s (str): The expected token text.

        Returns:
            bool: True if the token was consumed, otherwise False.
        """
        if equal(self.tokens[0], s):
            self.tokens.popleft()
            return True

        return False

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

    def declspec(self) -> Dtype:
        """Parses declaration specifiers.

        ## Grammar:
            ```
            declspec = "int"
            ```

        Returns:
            Type: The parsed type.
        """
        self.expect("int")
        return dtypeInt

    def funcParams(self, dtype: Dtype) -> Dtype:
        """Parses function parameters.

        ## Grammar:
            ```
            func-params = (param ("," param)*)? ")"
            param       = declspec declarator
            ```

        Args:
            dtype (Dtype): The function return type.

        Returns:
            Dtype: The resulting function type.
        """
        params: list[Dtype] = []

        while not equal(self.tokens[0], ")"):
            if params:
                self.expect(",")

            baseType = self.declspec()
            paramType = self.declarator(baseType)
            params.append(copyType(paramType))

        self.expect(")")

        func = funcType(dtype)
        func.params = params
        return func

    def typeSuffix(self, dtype: Dtype) -> Dtype:
        """Parses a type suffix.

        ## Grammar:
            ```
            type-suffix = "(" func-params
                        | "[" num "]"
                        | ε
            ```

        Args:
            dtype (Dtype): The type constructed so far.

        Returns:
            Dtype: The resulting type.
        """
        if equal(self.tokens[0], "("):
            self.expect("(")
            return self.funcParams(dtype)

        if equal(self.tokens[0], "["):
            self.expect("[")

            tok = self.tokens.popleft()

            if tok.kind != TokenKind.NUM:
                self.errorReporter.errorTok(tok, "expected an array size")

            self.expect("]")

            return arrayOf(dtype, tok.val)

        return dtype

    def declarator(self, dtype: Dtype) -> Dtype:
        """Parses a declarator.

        ## Grammar:
            ```
            declarator = "*"* ident type-suffix
            ```

        Args:
            dtype (Dtype): The base type.

        Returns:
            Dtype: The parsed type.
        """
        while self.consume("*"):
            dtype = pointerTo(dtype)

        tok = self.tokens[0]

        if tok.kind != TokenKind.IDENT:
            self.errorReporter.errorTok(tok, "expected a variable name")

        self.tokens.popleft()

        dtype = self.typeSuffix(dtype)
        dtype.name = tok

        return dtype

    def declaration(self) -> Node:
        """Parses a declaration.

        ## Grammar:
            ```
            declaration = declspec (declarator ("=" expr)? ("," declarator ("=" expr)?)*)? ";"
            ```

        Returns:
            Node: The parsed declaration statement.
        """
        baseDtype = self.declspec()

        body: list[Node] = []
        i = 0

        while not equal(self.tokens[0], ";"):
            if i > 0:
                self.expect(",")
            i += 1

            dtype = self.declarator(baseDtype)
            var = self.newLVar(getIdent(dtype.name, self.errorReporter), dtype)

            if not equal(self.tokens[0], "="):
                continue

            tok = self.tokens.popleft()

            lhs = newVarNode(var, dtype.name)
            rhs = self.assign()

            node = newBinary(NodeKind.ASSIGN, lhs, rhs, tok)
            body.append(newUnary(NodeKind.EXPR_STMT, node, tok))

        tok = self.tokens[0]
        self.expect(";")

        return newBlock(body, tok)

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

            node = newUnary(NodeKind.RETURN, self.expr(), tok)

            self.expect(";")
            return node

        if equal(self.tokens[0], "if"):
            tok = self.tokens.popleft()

            node = newNode(NodeKind.IF, tok)

            self.expect("(")
            node.cond = self.expr()
            self.expect(")")

            node.then = self.stmt()

            if equal(self.tokens[0], "else"):
                self.tokens.popleft()
                node.els = self.stmt()

            return node

        if equal(self.tokens[0], "for"):
            tok = self.tokens.popleft()

            node = newNode(NodeKind.FOR, tok)

            self.expect("(")

            node.init = self.exprStmt()

            if not equal(self.tokens[0], ";"):
                node.cond = self.expr()
            self.expect(";")

            if not equal(self.tokens[0], ")"):
                node.inc = self.expr()
            self.expect(")")

            node.then = self.stmt()
            return node

        if equal(self.tokens[0], "while"):
            tok = self.tokens.popleft()

            node = newNode(NodeKind.FOR, tok)

            self.expect("(")
            node.cond = self.expr()
            self.expect(")")

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
            compound-stmt = (declaration | stmt)* "}"
            ```

        Args:
            tok (Token): The "{" token that opened this block.

        Returns:
            Node: The root node of the parsed compound statement.
        """
        body: list[Node] = []

        while not equal(self.tokens[0], "}"):
            if equal(self.tokens[0], "int"):
                node = self.declaration()
            else:
                node = self.stmt()

            addType(node, self.errorReporter)
            body.append(node)

        self.expect("}")

        return newBlock(body, tok)

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
            return newNode(NodeKind.BLOCK, tok)

        tok = self.tokens[0]

        node = newUnary(NodeKind.EXPR_STMT, self.expr(), tok)

        self.expect(";")
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
            node = newBinary(NodeKind.ASSIGN, node, self.assign(), tok)

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
                node = newBinary(NodeKind.EQ, node, self.relational(), start)
                continue

            if equal(self.tokens[0], "!="):
                self.tokens.popleft()
                node = newBinary(NodeKind.NE, node, self.relational(), start)
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
                node = newBinary(NodeKind.LT, node, self.add(), start)
                continue

            if equal(self.tokens[0], "<="):
                self.tokens.popleft()
                node = newBinary(NodeKind.LE, node, self.add(), start)
                continue

            if equal(self.tokens[0], ">"):
                self.tokens.popleft()
                node = newBinary(NodeKind.LT, self.add(), node, start)
                continue

            if equal(self.tokens[0], ">="):
                self.tokens.popleft()
                node = newBinary(NodeKind.LE, self.add(), node, start)
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
                node = newAdd(node, self.mul(), start, self.errorReporter)
                continue

            if equal(self.tokens[0], "-"):
                self.tokens.popleft()
                node = newSub(node, self.mul(), start, self.errorReporter)
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
                node = newBinary(NodeKind.MUL, node, self.unary(), start)
                continue

            if equal(self.tokens[0], "/"):
                self.tokens.popleft()
                node = newBinary(NodeKind.DIV, node, self.unary(), start)
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
            return newUnary(NodeKind.NEG, self.unary(), tok)

        if equal(self.tokens[0], "&"):
            tok = self.tokens.popleft()
            return newUnary(NodeKind.ADDR, self.unary(), tok)

        if equal(self.tokens[0], "*"):
            tok = self.tokens.popleft()
            return newUnary(NodeKind.DEREF, self.unary(), tok)

        return self.primary()

    def newLVar(self, name: str, dtype: Dtype) -> Obj:
        """Creates a new local variable and registers it in scope.

        Args:
            name (str): The variable's name.
            dtype (Dtype): The variable's datatype.

        Returns:
            Obj: The newly created variable.
        """
        var = Obj(name=name, dtype=dtype)
        self.locals.append(var)
        return var

    def funcall(self) -> Node:
        """Parses a function call.

        ## Grammar:
            ```
            funcall = ident "(" (assign ("," assign)*)? ")"
            ```

        Returns:
            Node: The parsed function call.
        """
        start = self.tokens.popleft()  # identifier
        self.expect("(")

        args: list[Node] = []

        while not equal(self.tokens[0], ")"):
            if args:
                self.expect(",")

            args.append(self.assign())

        self.expect(")")

        return newFuncall(start.loc, args, start)

    def primary(self) -> Node:
        """Parses a primary expression.

        ## Grammar:
            ```
            primary = "(" expr ")" | ident args? | num
            args = "(" ")"
            ```

        Returns:
            Node: The root node of the parsed expression.

        Raises:
            SystemExit: If no valid primary expression is found.
        """
        if equal(self.tokens[0], "("):
            self.tokens.popleft()
            node = self.expr()
            self.expect(")")
            return node

        tok = self.tokens[0]

        if tok.kind == TokenKind.IDENT:
            # Function call
            if len(self.tokens) > 1 and equal(self.tokens[1], "("):
                return self.funcall()

            # Variable
            var = self.findVar(tok)

            if var is None:
                self.errorReporter.errorTok(tok, "undefined variable")

            self.tokens.popleft()
            return newVarNode(var, tok)

        if tok.kind == TokenKind.NUM:
            self.tokens.popleft()
            return newNum(tok.val, tok)

        self.errorReporter.errorTok(tok, "expected an expression")

    def createParamLVars(self, params: list[Dtype]) -> None:
        """Creates local variables for function parameters.

        Args:
            params (list[Dtype]): The function parameter types.
        """
        for param in params:
            self.newLVar(getIdent(param.name, self.errorReporter), param)

    def function(self) -> Function:
        """Parses a function definition.

        ## Grammar:
            ```
            function-definition = declspec declarator compound-stmt
            ```

        Returns:
            Function: The parsed function.
        """
        dtype = self.declspec()
        dtype = self.declarator(dtype)

        # Each function has its own local symbol table.
        self.locals.clear()

        fn = Function(name=getIdent(dtype.name, self.errorReporter))
        self.createParamLVars(dtype.params)
        fn.params = self.locals.copy()

        tok = self.tokens[0]
        self.expect("{")
        fn.body = self.compoundStmt(tok)
        fn.locals = self.locals.copy()

        return fn

    def parse(self) -> list[Function]:
        """Parses the token stream.

        ## Grammar:
            ```
            program = function-definition*
            ```

        Returns:
            list[Function]: The parsed functions.
        """
        functions: list[Function] = []

        while self.tokens[0].kind != TokenKind.EOF:
            functions.append(self.function())

        return functions

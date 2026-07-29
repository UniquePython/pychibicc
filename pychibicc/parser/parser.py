from collections import deque

from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokenizer import equal, isTypename
from pychibicc.frontend.tokens import Token, TokenKind
from pychibicc.syntax.dtypes import (
    Dtype,
    DtypeKind,
    arrayOf,
    copyType,
    dtypeChar,
    dtypeInt,
    funcType,
    pointerTo,
)
from pychibicc.syntax.formatting import formatNode, formatToken
from pychibicc.syntax.node_constructors import (
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
from pychibicc.syntax.nodes import Node, NodeKind, addDtype
from pychibicc.syntax.objects import Obj


def _getIdent(tok: Token, errorReporter: ErrorReporter) -> str:
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
        errorReporter.errorTok(
            tok, f"expected an identifier, but got {formatToken(tok)} instead"
        )

    return tok.lexeme


def _getNumber(tok: Token, errorReporter: ErrorReporter) -> CInt:
    """Extracts a number from a token, erroring if it isn't one.

    Args:
        tok (Token): The token to extract from.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.

    Returns:
        CInt: The number.

    Raises:
        SystemExit: If the token is not an identifier.
    """
    if tok.kind != TokenKind.NUM:
        errorReporter.errorTok(
            tok, f"expected a number, but got {formatToken(tok)} instead"
        )

    return tok.val


def _evalConst(node: Node, errorReporter: ErrorReporter) -> CInt:
    """Evaluates a constant expression at compile time.

    Only expressions built entirely out of integer literals and the basic
    arithmetic operators (+, -, *, /, unary -) can be folded this way;
    anything else (variables, function calls, pointer operations, ...)
    is rejected with an error pointing at the offending subexpression.

    Args:
        node (Node): The expression to evaluate.
        errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.

    Returns:
        CInt: The expression's compile-time value.

    Raises:
        SystemExit: If the expression is not a constant expression, or if
            it involves division or modulo by zero.
    """
    match node.kind:
        case NodeKind.NUM:
            return node.val

        case NodeKind.NEG:
            return -_evalConst(node.lhs, errorReporter)

        case NodeKind.ADD:
            return _evalConst(node.lhs, errorReporter) + _evalConst(
                node.rhs, errorReporter
            )

        case NodeKind.SUB:
            return _evalConst(node.lhs, errorReporter) - _evalConst(
                node.rhs, errorReporter
            )

        case NodeKind.MUL:
            return _evalConst(node.lhs, errorReporter) * _evalConst(
                node.rhs, errorReporter
            )

        case NodeKind.DIV:
            lhs = _evalConst(node.lhs, errorReporter)
            rhs = _evalConst(node.rhs, errorReporter)

            if rhs == 0:
                errorReporter.errorTok(node.rhs.tok, "division by zero")

            return lhs // rhs

        case NodeKind.EQ:
            lhs = _evalConst(node.lhs, errorReporter)
            rhs = _evalConst(node.rhs, errorReporter)
            return CInt(1) if lhs == rhs else CInt(0)

        case NodeKind.NE:
            lhs = _evalConst(node.lhs, errorReporter)
            rhs = _evalConst(node.rhs, errorReporter)
            return CInt(1) if lhs != rhs else CInt(0)

        case NodeKind.LT:
            lhs = _evalConst(node.lhs, errorReporter)
            rhs = _evalConst(node.rhs, errorReporter)
            return CInt(1) if lhs < rhs else CInt(0)

        case NodeKind.LE:
            lhs = _evalConst(node.lhs, errorReporter)
            rhs = _evalConst(node.rhs, errorReporter)
            return CInt(1) if lhs <= rhs else CInt(0)

        case _:
            errorReporter.errorTok(
                node.tok,
                f"{formatNode(node)} is not a compile-time constant expression",
            )


class Parser:
    """Parses a token stream into an abstract syntax tree (AST)."""

    def __init__(self, errorReporter: ErrorReporter, tokens: list[Token]):
        """Initializes the parser.

        Args:
            errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
            tokens (list[Token]): The token stream to parse.
        """
        self._errorReporter = errorReporter
        self._tokens: deque[Token] = deque(tokens)
        self._locals: list[Obj] = []
        self._globals: list[Obj] = []

        self._nextUniqueId: CInt = 0

    def _expect(self, s: str) -> None:
        """Consumes the current token if it matches the expected string.

        Args:
            s (str): The expected token text.

        Raises:
            SystemExit: If the current token does not match the expected string.
        """
        tok = self._tokens.popleft()

        if not equal(tok, s):
            self._errorReporter.errorTok(
                tok, f"expected '{s}', but got {formatToken(tok)} instead"
            )

    def _consume(self, s: str) -> bool:
        """Consumes the current token if it matches the expected string.

        Args:
            s (str): The expected token text.

        Returns:
            bool: True if the token was consumed, otherwise False.
        """
        if equal(self._tokens[0], s):
            self._tokens.popleft()
            return True

        return False

    def _findVar(self, tok: Token) -> Obj | None:
        """Finds a local or global variable by name.

        Args:
            tok (Token): The identifier token to search for.

        Returns:
            Obj | None: The matching local or global variable, or None if no match is found.
        """
        for lvar in self._locals:
            if lvar.name == tok.lexeme:
                return lvar

        for gvar in self._globals:
            if gvar.name == tok.lexeme:
                return gvar

        return None

    def _declspec(self) -> Dtype:
        """Parses declaration specifiers.

        ## Grammar:
            ```
            declspec = "char" | "int"
            ```

        Returns:
            Dtype: The parsed type.
        """
        if self._consume("char"):
            return dtypeChar

        self._expect("int")
        return dtypeInt

    def _funcParams(self, dtype: Dtype) -> Dtype:
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

        while not equal(self._tokens[0], ")"):
            if params:
                self._expect(",")

            baseType = self._declspec()
            paramType = self._declarator(baseType)
            params.append(copyType(paramType))

        self._expect(")")

        func = funcType(dtype)
        func.params = params
        return func

    def _typeSuffix(self, dtype: Dtype) -> Dtype:
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
        if equal(self._tokens[0], "("):
            self._expect("(")
            return self._funcParams(dtype)

        if equal(self._tokens[0], "["):
            self._expect("[")

            tok = self._tokens.popleft()
            sz = _getNumber(tok, self._errorReporter)
            self._expect("]")

            dtype = self._typeSuffix(dtype)
            return arrayOf(dtype, sz)

        return dtype

    def _declarator(self, dtype: Dtype) -> Dtype:
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
        while self._consume("*"):
            dtype = pointerTo(dtype)

        tok = self._tokens[0]

        if tok.kind != TokenKind.IDENT:
            self._errorReporter.errorTok(
                tok, f"expected a variable name, but got {formatToken(tok)} instead"
            )

        self._tokens.popleft()

        dtype = self._typeSuffix(dtype)
        dtype.name = tok

        return dtype

    def _declaration(self) -> Node:
        """Parses a declaration.

        ## Grammar:
            ```
            declaration = declspec (declarator ("=" expr)? ("," declarator ("=" expr)?)*)? ";"
            ```

        Returns:
            Node: The parsed declaration statement.
        """
        baseDtype = self._declspec()

        body: list[Node] = []
        i = 0

        while not equal(self._tokens[0], ";"):
            if i > 0:
                self._expect(",")
            i += 1

            dtype = self._declarator(baseDtype)
            var = self._newLVar(_getIdent(dtype.name, self._errorReporter), dtype)

            if not equal(self._tokens[0], "="):
                continue

            tok = self._tokens.popleft()

            lhs = newVarNode(var, dtype.name)
            rhs = self._assign()

            node = newBinary(NodeKind.ASSIGN, lhs, rhs, tok)
            body.append(newUnary(NodeKind.EXPR_STMT, node, tok))

        tok = self._tokens[0]
        self._expect(";")

        return newBlock(body, tok)

    def _stmt(self) -> Node:
        """Parses a statement.

        ## Grammar:
            ```
            stmt = "return" expr ";"
                | "if" "(" expr ")" stmt ("else" stmt)?
                | "_Unless" "(" expr ")" stmt ("else" stmt)?
                | "for" "(" expr-stmt expr? ";" expr? ")" stmt
                | "while" "(" expr ")" stmt
                | "_Until" "(" expr ")" stmt
                | "_Loop" "(" expr ")" stmt
                | "_Forever" stmt
                | "_Infer" ident "=" expr ";"
                | "{" compound-stmt
                | expr-stmt
            ```

        Returns:
            Node: The root node of the parsed statement.
        """
        if equal(self._tokens[0], "return"):
            tok = self._tokens.popleft()

            node = newUnary(NodeKind.RETURN, self._expr(), tok)

            self._expect(";")
            return node

        if equal(self._tokens[0], "if"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.IF, tok)

            self._expect("(")
            node.cond = self._expr()
            self._expect(")")

            node.then = self._stmt()

            if equal(self._tokens[0], "else"):
                self._tokens.popleft()
                node.els = self._stmt()

            return node

        if equal(self._tokens[0], "_Unless"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.IF, tok)

            self._expect("(")
            node.cond = newBinary(NodeKind.EQ, self._expr(), newNum(0, tok), tok)
            self._expect(")")

            node.then = self._stmt()

            if equal(self._tokens[0], "else"):
                self._tokens.popleft()
                node.els = self._stmt()

            return node

        if equal(self._tokens[0], "for"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.FOR, tok)

            self._expect("(")

            node.init = self._exprStmt()

            if not equal(self._tokens[0], ";"):
                node.cond = self._expr()
            self._expect(";")

            if not equal(self._tokens[0], ")"):
                node.inc = self._expr()
            self._expect(")")

            node.then = self._stmt()
            return node

        if equal(self._tokens[0], "while"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.FOR, tok)

            self._expect("(")
            node.cond = self._expr()
            self._expect(")")

            node.then = self._stmt()
            return node

        if equal(self._tokens[0], "_Until"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.FOR, tok)

            self._expect("(")
            node.cond = newBinary(NodeKind.EQ, self._expr(), newNum(0, tok), tok)
            self._expect(")")

            node.then = self._stmt()
            return node

        if equal(self._tokens[0], "_Loop"):
            tok = self._tokens.popleft()

            self._expect("(")
            count = self._expr()
            self._expect(")")

            node = newNode(NodeKind.FOR, tok)

            bound = self._newLVar(self._newUniqueName(), dtypeInt)
            counter = self._newLVar(self._newUniqueName(), dtypeInt)

            boundNode = newVarNode(bound, tok)
            counterNode = newVarNode(counter, tok)

            # init: <bound> = count; <counter> = 0;
            # (count is evaluated exactly once, up front, not on every iteration)
            node.init = newBlock(
                [
                    newUnary(
                        NodeKind.EXPR_STMT,
                        newBinary(NodeKind.ASSIGN, boundNode, count, tok),
                        tok,
                    ),
                    newUnary(
                        NodeKind.EXPR_STMT,
                        newBinary(NodeKind.ASSIGN, counterNode, newNum(0, tok), tok),
                        tok,
                    ),
                ],
                tok,
            )

            # cond: <counter> < <bound>
            node.cond = newBinary(NodeKind.LT, counterNode, boundNode, tok)

            # inc: <counter> = <counter> + 1
            node.inc = newBinary(
                NodeKind.ASSIGN,
                counterNode,
                newAdd(counterNode, newNum(1, tok), tok, self._errorReporter),
                tok,
            )

            node.then = self._stmt()
            return node

        if equal(self._tokens[0], "_Forever"):
            tok = self._tokens.popleft()

            node = newNode(NodeKind.FOR, tok)
            node.then = self._stmt()

            return node

        if equal(self._tokens[0], "_Infer"):
            tok = self._tokens.popleft()

            nameTok = self._tokens.popleft()
            name = _getIdent(nameTok, self._errorReporter)

            self._expect("=")

            rhs = self._assign()
            addDtype(rhs, self._errorReporter)

            var = self._newLVar(name, rhs.dtype)
            lhs = newVarNode(var, nameTok)

            node = newBinary(NodeKind.ASSIGN, lhs, rhs, tok)
            self._expect(";")

            return newUnary(NodeKind.EXPR_STMT, node, tok)

        if equal(self._tokens[0], "{"):
            tok = self._tokens.popleft()
            return self._compoundStmt(tok)

        return self._exprStmt()

    def _compoundStmt(self, tok: Token) -> Node:
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

        while not equal(self._tokens[0], "}"):
            if isTypename(self._tokens[0]):
                node = self._declaration()
            else:
                node = self._stmt()

            addDtype(node, self._errorReporter)
            body.append(node)

        self._expect("}")

        return newBlock(body, tok)

    def _exprStmt(self) -> Node:
        """Parses an expression statement.

        ## Grammar:
            ```
            expr-stmt = expr? ";"
            ```

        Returns:
            Node: The root node of the parsed expression statement.
        """
        if equal(self._tokens[0], ";"):
            tok = self._tokens.popleft()
            return newNode(NodeKind.BLOCK, tok)

        tok = self._tokens[0]

        node = newUnary(NodeKind.EXPR_STMT, self._expr(), tok)

        self._expect(";")
        return node

    def _expr(self) -> Node:
        """Parses an expression.

        ## Grammar:
            ```
            expr = assign
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        return self._assign()

    def _assign(self) -> Node:
        """Parses an assignment expression.

        ## Grammar:
            ```
            assign = equality ("=" assign)?
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._equality()

        if equal(self._tokens[0], "="):
            tok = self._tokens.popleft()
            node = newBinary(NodeKind.ASSIGN, node, self._assign(), tok)

        return node

    def _equality(self) -> Node:
        """Parses an equality expression.

        ## Grammar:
            ```
            equality = relational ("==" relational | "!=" relational)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._relational()

        while True:
            start = self._tokens[0]

            if equal(self._tokens[0], "=="):
                self._tokens.popleft()
                node = newBinary(NodeKind.EQ, node, self._relational(), start)
                continue

            if equal(self._tokens[0], "!="):
                self._tokens.popleft()
                node = newBinary(NodeKind.NE, node, self._relational(), start)
                continue

            return node

    def _relational(self) -> Node:
        """Parses a relational expression.

        ## Grammar:
            ```
            relational = add ("<" add | "<=" add | ">" add | ">=" add)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._add()

        while True:
            start = self._tokens[0]

            if equal(self._tokens[0], "<"):
                self._tokens.popleft()
                node = newBinary(NodeKind.LT, node, self._add(), start)
                continue

            if equal(self._tokens[0], "<="):
                self._tokens.popleft()
                node = newBinary(NodeKind.LE, node, self._add(), start)
                continue

            if equal(self._tokens[0], ">"):
                self._tokens.popleft()
                node = newBinary(NodeKind.LT, self._add(), node, start)
                continue

            if equal(self._tokens[0], ">="):
                self._tokens.popleft()
                node = newBinary(NodeKind.LE, self._add(), node, start)
                continue

            return node

    def _add(self) -> Node:
        """Parses an addition or subtraction expression.

        ## Grammar:
            ```
            add = mul ("+" mul | "-" mul)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._mul()

        while True:
            start = self._tokens[0]

            if equal(self._tokens[0], "+"):
                self._tokens.popleft()
                node = newAdd(node, self._mul(), start, self._errorReporter)
                continue

            if equal(self._tokens[0], "-"):
                self._tokens.popleft()
                node = newSub(node, self._mul(), start, self._errorReporter)
                continue

            return node

    def _mul(self) -> Node:
        """Parses a multiplication or division expression.

        ## Grammar:
            ```
            mul = unary ("*" unary | "/" unary)*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._unary()

        while True:
            start = self._tokens[0]

            if equal(self._tokens[0], "*"):
                self._tokens.popleft()
                node = newBinary(NodeKind.MUL, node, self._unary(), start)
                continue

            if equal(self._tokens[0], "/"):
                self._tokens.popleft()
                node = newBinary(NodeKind.DIV, node, self._unary(), start)
                continue

            return node

    def _unary(self) -> Node:
        """Parses a unary expression.

        ## Grammar:
            ```
            unary = ("+" | "-" | "*" | "&") unary
                    | postfix
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        if equal(self._tokens[0], "+"):
            self._tokens.popleft()
            return self._unary()

        if equal(self._tokens[0], "-"):
            tok = self._tokens.popleft()
            return newUnary(NodeKind.NEG, self._unary(), tok)

        if equal(self._tokens[0], "&"):
            tok = self._tokens.popleft()
            return newUnary(NodeKind.ADDR, self._unary(), tok)

        if equal(self._tokens[0], "*"):
            tok = self._tokens.popleft()
            return newUnary(NodeKind.DEREF, self._unary(), tok)

        return self._postfix()

    def _postfix(self) -> Node:
        """Parses a postfix expression.

        ## Grammar:
            ```
            postfix = primary ("[" expr "]")*
            ```

        Returns:
            Node: The root node of the parsed expression.
        """
        node = self._primary()

        while equal(self._tokens[0], "["):
            start = self._tokens.popleft()

            idx = self._expr()
            self._expect("]")

            # x[y] is equivalent to *(x + y)
            node = newUnary(
                NodeKind.DEREF,
                newAdd(node, idx, start, self._errorReporter),
                start,
            )

        return node

    def _newVar(self, name: str, dtype: Dtype) -> Obj:
        """Creates a new variable.

        Args:
            name (str): The variable's name.
            dtype (Dtype): The variable's datatype.

        Returns:
            Obj: The newly created variable.
        """
        return Obj(name=name, dtype=dtype)

    def _newLVar(self, name: str, dtype: Dtype) -> Obj:
        """Creates a new local variable and registers it in scope.

        Args:
            name (str): The variable's name.
            dtype (Dtype): The variable's datatype.

        Returns:
            Obj: The newly created local variable.
        """
        var = self._newVar(name, dtype)
        var.isLocal = True
        self._locals.append(var)
        return var

    def _newGVar(self, name: str, dtype: Dtype) -> Obj:
        """Creates a new global variable.

        Args:
            name (str): The variable's name.
            dtype (Dtype): The variable's datatype.

        Returns:
            Obj: The newly created global variable.
        """
        var = self._newVar(name, dtype)
        self._globals.append(var)
        return var

    def _newUniqueName(self) -> str:
        """Generates a unique internal symbol name.

        Returns:
            str: A unique symbol name.
        """
        name = f".pychibicc.symbol.{self._nextUniqueId}"
        self._nextUniqueId += 1
        return name

    def _newAnonGVar(self, dtype: Dtype) -> Obj:
        """Creates a new anonymous global variable.

        Args:
            dtype (Dtype): The variable's datatype.

        Returns:
            Obj: The newly created global variable.
        """
        return self._newGVar(self._newUniqueName(), dtype)

    def _newStringLiteral(self, string: str, dtype: Dtype) -> Obj:
        """Creates an anonymous global variable for a string literal.

        Args:
            string (str): The string literal contents.
            dtype (Dtype): The array type of the string.

        Returns:
            Obj: The global variable holding the string.
        """
        var = self._newAnonGVar(dtype)
        var.initData = string
        return var

    def _funcall(self) -> Node:
        """Parses a function call.

        ## Grammar:
            ```
            funcall = ident "(" (assign ("," assign)*)? ")"
            ```

        Returns:
            Node: The parsed function call.
        """
        start = self._tokens.popleft()  # identifier
        self._expect("(")

        args: list[Node] = []

        while not equal(self._tokens[0], ")"):
            if args:
                self._expect(",")

            args.append(self._assign())

        self._expect(")")

        return newFuncall(start.lexeme, args, start)

    def _primary(self) -> Node:
        """Parses a primary expression.

        ## Grammar:
            ```
            primary = "(" "{" stmt+ "}" ")"
                      | "(" expr ")"
                      | "sizeof" unary
                      | "_Comptime" "(" expr ")"
                      | ident func-args?
                      | str
                      | num
            ```

        Returns:
            Node: The root node of the parsed expression.

        Raises:
            SystemExit: If no valid primary expression is found.
        """
        if equal(self._tokens[0], "(") and equal(self._tokens[1], "{"):
            # This is a GNU statement expression.
            tok = self._tokens[0]

            self._expect("(")
            brace_tok = self._tokens.popleft()
            stmt = self._compoundStmt(brace_tok)
            self._expect(")")

            return Node(kind=NodeKind.STMT_EXPR, tok=tok, body=stmt.body)

        if equal(self._tokens[0], "("):
            self._tokens.popleft()
            node = self._expr()
            self._expect(")")
            return node

        if equal(self._tokens[0], "sizeof"):
            tok = self._tokens.popleft()

            node = self._unary()
            addDtype(node, self._errorReporter)

            return newNum(node.dtype.size, tok)

        if equal(self._tokens[0], "_Comptime"):
            tok = self._tokens.popleft()

            self._expect("(")
            node = self._expr()
            self._expect(")")

            return newNum(_evalConst(node, self._errorReporter), tok)

        tok = self._tokens[0]

        if tok.kind == TokenKind.IDENT:
            # Function call
            if len(self._tokens) > 1 and equal(self._tokens[1], "("):
                return self._funcall()

            # Variable
            var = self._findVar(tok)

            if var is None:
                self._errorReporter.errorTok(tok, f"undefined variable {tok.lexeme}")

            self._tokens.popleft()
            return newVarNode(var, tok)

        if tok.kind == TokenKind.STR:
            self._tokens.popleft()
            return newVarNode(self._newStringLiteral(tok.string, tok.dtype), tok)

        if tok.kind == TokenKind.NUM:
            self._tokens.popleft()
            return newNum(tok.val, tok)

        self._errorReporter.errorTok(
            tok, f"expected an expression, but got {formatToken(tok)} instead"
        )

    def _createParamLVars(self, params: list[Dtype]) -> None:
        """Creates local variables for function parameters.

        Args:
            params (list[Dtype]): The function parameter types.
        """
        for param in params:
            self._newLVar(_getIdent(param.name, self._errorReporter), param)

    def _function(self, baseDtype: Dtype) -> Obj:
        """Parses a function definition.

        ## Grammar:
            ```
            function-definition = declarator compound-stmt
            ```

        Args:
            baseDtype (Dtype): The function's base type.

        Returns:
            Obj: The parsed function.
        """
        dtype = self._declarator(baseDtype)

        fn = self._newGVar(_getIdent(dtype.name, self._errorReporter), dtype)
        fn.isFunction = True

        # Each function has its own local symbol table.
        self._locals.clear()

        self._createParamLVars(dtype.params)
        fn.params = self._locals.copy()

        tok = self._tokens[0]
        self._expect("{")
        fn.body = self._compoundStmt(tok)
        fn.locals = self._locals.copy()

        return fn

    def _globalVariable(self, baseDtype: Dtype) -> None:
        """Parses one or more global variable declarations.

        ## Grammar:
            ```
            global-variable = declarator ("," declarator)* ";"
            ```

        Args:
            baseDtype (Dtype): The base type of the declaration.
        """
        first = True

        while not self._consume(";"):
            if not first:
                self._expect(",")

            first = False

            dtype = self._declarator(baseDtype)
            self._newGVar(_getIdent(dtype.name, self._errorReporter), dtype)

    def _isFunction(self) -> bool:
        """Returns whether the upcoming declaration is a function.

        Returns:
            bool: True if the declaration is a function, False otherwise.
        """
        if equal(self._tokens[0], ";"):
            return False

        tokens = self._tokens.copy()

        dummy = Dtype(kind=DtypeKind.INT)
        dtype = self._declarator(dummy)

        self._tokens = tokens
        return dtype.kind == DtypeKind.FUNC

    def parse(self) -> list[Obj]:
        """Parses the token stream.

        ## Grammar:
            ```
            program = (function-definition | global-variable)*
            ```

        Returns:
            list[Obj]: The parsed global objects.
        """
        self._globals.clear()

        while self._tokens[0].kind != TokenKind.EOF:
            baseType = self._declspec()

            # Function
            if self._isFunction():
                self._function(baseType)
                continue

            # Global variable
            self._globalVariable(baseType)

        return self._globals

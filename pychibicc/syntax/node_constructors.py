from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokens import Token
from pychibicc.syntax.dtypes import dtypeInt, isInteger
from pychibicc.syntax.nodes import Node, NodeKind, addDtype
from pychibicc.syntax.objects import Obj


def newNode(kind: NodeKind, tok: Token) -> Node:
    """Creates a bare node with no operands.

    Args:
        kind (NodeKind): The kind of node to create.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=kind, tok=tok)


def newUnary(kind: NodeKind, lhs: Node, tok: Token) -> Node:
    """Creates a unary node.

    Args:
        kind (NodeKind): The kind of node to create.
        lhs (Node): The operand.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=kind, tok=tok, lhs=lhs)


def newBinary(kind: NodeKind, lhs: Node, rhs: Node, tok: Token) -> Node:
    """Creates a binary node.

    Args:
        kind (NodeKind): The kind of node to create.
        lhs (Node): The left-hand operand.
        rhs (Node): The right-hand operand.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=kind, tok=tok, lhs=lhs, rhs=rhs)


def newNum(val: CInt, tok: Token) -> Node:
    """Creates a number node.

    Args:
        val (CInt): The integer value.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=NodeKind.NUM, tok=tok, dtype=dtypeInt, val=val)


def newBlock(body: list[Node], tok: Token) -> Node:
    """Creates a block node.

    Args:
        body (list[Node]): The statements contained in the block.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=NodeKind.BLOCK, tok=tok, body=body)


def newVarNode(var: Obj, tok: Token) -> Node:
    """Creates a variable reference node.

    Args:
        var (Obj): The variable being referenced.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=NodeKind.VAR, tok=tok, var=var)


def newFuncall(funcName: str, args: list[Node], tok: Token) -> Node:
    """Creates a function call node.

    Args:
        funcName (str): The name of the function.
        args (list[Node]): The arguments to the function.
        tok (Token): The representative token.

    Returns:
        Node: The newly created node.
    """
    return Node(kind=NodeKind.FUNCALL, tok=tok, funcName=funcName, args=args)


def newAdd(lhs: Node, rhs: Node, tok: Token, errorReporter: ErrorReporter) -> Node:
    """Creates an addition node, handling pointer arithmetic.

    Args:
        lhs (Node): The left-hand operand.
        rhs (Node): The right-hand operand.
        tok (Token): The representative token.
        errorReporter (ErrorReporter): The error reporter to use on invalid operands.

    Returns:
        Node: The newly created node.
    """
    addDtype(lhs, errorReporter)
    addDtype(rhs, errorReporter)

    # num + num
    if isInteger(lhs.dtype) and isInteger(rhs.dtype):
        return newBinary(NodeKind.ADD, lhs, rhs, tok)

    if lhs.dtype.base is not None and rhs.dtype.base is not None:
        errorReporter.errorTok(tok, "invalid operands")

    # Canonicalize num + ptr to ptr + num.
    if lhs.dtype.base is None and rhs.dtype.base is not None:
        lhs, rhs = rhs, lhs

    # ptr + num
    rhs = newBinary(NodeKind.MUL, rhs, newNum(lhs.dtype.base.size, tok), tok)
    addDtype(rhs, errorReporter)

    return newBinary(NodeKind.ADD, lhs, rhs, tok)


def newSub(lhs: Node, rhs: Node, tok: Token, errorReporter: ErrorReporter) -> Node:
    """Creates a subtraction node, handling pointer arithmetic.

    Args:
        lhs (Node): The left-hand operand.
        rhs (Node): The right-hand operand.
        tok (Token): The representative token.
        errorReporter (ErrorReporter): The error reporter to use on invalid operands.

    Returns:
        Node: The newly created node.
    """
    addDtype(lhs, errorReporter)
    addDtype(rhs, errorReporter)

    # num - num
    if isInteger(lhs.dtype) and isInteger(rhs.dtype):
        return newBinary(NodeKind.SUB, lhs, rhs, tok)

    # ptr - num
    if lhs.dtype.base is not None and isInteger(rhs.dtype):
        rhs = newBinary(NodeKind.MUL, rhs, newNum(lhs.dtype.base.size, tok), tok)
        addDtype(rhs, errorReporter)

        node = newBinary(NodeKind.SUB, lhs, rhs, tok)
        node.dtype = lhs.dtype
        return node

    # ptr - ptr
    if lhs.dtype.base is not None and rhs.dtype.base is not None:
        node = newBinary(NodeKind.SUB, lhs, rhs, tok)
        node.dtype = dtypeInt

        return newBinary(NodeKind.DIV, node, newNum(lhs.dtype.base.size, tok), tok)

    errorReporter.errorTok(tok, "invalid operands")

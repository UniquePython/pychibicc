from dtypes import dtypeInt, isInteger
from error_reporter import ErrorReporter
from nodes import Node, NodeKind, addType
from objects import Obj
from tokens import Token


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


def newNum(val: int, tok: Token) -> Node:
    """Creates a number node.

    Args:
        val (int): The integer value.
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
    addType(lhs, errorReporter)
    addType(rhs, errorReporter)

    # num + num
    if isInteger(lhs.dtype) and isInteger(rhs.dtype):
        return newBinary(NodeKind.ADD, lhs, rhs, tok)

    if lhs.dtype.base is not None and rhs.dtype.base is not None:
        errorReporter.errorTok(tok, "invalid operands")

    # Canonicalize num + ptr to ptr + num.
    if lhs.dtype.base is None and rhs.dtype.base is not None:
        lhs, rhs = rhs, lhs

    # ptr + num
    rhs = newBinary(NodeKind.MUL, rhs, newNum(8, tok), tok)
    addType(rhs, errorReporter)

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
    addType(lhs, errorReporter)
    addType(rhs, errorReporter)

    # num - num
    if isInteger(lhs.dtype) and isInteger(rhs.dtype):
        return newBinary(NodeKind.SUB, lhs, rhs, tok)

    # ptr - num
    if lhs.dtype.base is not None and isInteger(rhs.dtype):
        rhs = newBinary(NodeKind.MUL, rhs, newNum(8, tok), tok)
        addType(rhs, errorReporter)

        node = newBinary(NodeKind.SUB, lhs, rhs, tok)
        node.dtype = lhs.dtype
        return node

    # ptr - ptr
    if lhs.dtype.base is not None and rhs.dtype.base is not None:
        node = newBinary(NodeKind.SUB, lhs, rhs, tok)
        node.dtype = dtypeInt

        return newBinary(NodeKind.DIV, node, newNum(8, tok), tok)

    errorReporter.errorTok(tok, "invalid operands")

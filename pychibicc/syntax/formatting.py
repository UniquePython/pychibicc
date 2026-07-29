from __future__ import annotations

from pychibicc.frontend.tokens import Token, TokenKind
from pychibicc.syntax.dtypes import Dtype, DtypeKind
from pychibicc.syntax.nodes import Node, NodeKind


def _formatStringLiteral(data: str) -> str:
    """Formats string-literal storage as a C string literal for display.

    Args:
        data (str): The raw byte content, including the trailing NUL added
            when the literal was tokenized.

    Returns:
        str: A double-quoted, escaped representation of the string, e.g.
            '"ab\\n"'.
    """
    content = data.removesuffix("\0")

    escapes = {
        "\\": "\\\\",
        '"': '\\"',
        "\a": "\\a",
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\v": "\\v",
        "\f": "\\f",
        "\r": "\\r",
        "\x1b": "\\e",
        "\0": "\\0",
    }

    escaped = "".join(
        escapes.get(ch, ch if ch.isprintable() else f"\\x{ord(ch):02x}")
        for ch in content
    )

    return f'"{escaped}"'


def formatToken(tok: Token | None) -> str:
    """Formats a token for display in error messages.

    Args:
        tok (Token | None): The token to format.

    Returns:
        str: A textual representation of the token, e.g.
            'identifier "foo"', 'the string literal "abc"', or
            'end of file'.
    """
    if tok is None:
        return "<none>"

    match tok.kind:
        case TokenKind.IDENT:
            return f'identifier "{tok.lexeme}"'

        case TokenKind.KEYWORD:
            return f'keyword "{tok.lexeme}"'

        case TokenKind.PUNCT:
            return f'"{tok.lexeme}"'

        case TokenKind.NUM:
            return f"number {tok.val}"

        case TokenKind.STR:
            return f"string literal {_formatStringLiteral(tok.string)}"

        case TokenKind.EOF:
            return "end of file"

        case _:
            return f"<{tok.kind.name}>"


def formatNode(node: Node | None) -> str:
    """Formats an AST node as a compact C-like expression.

    Args:
        node (Node | None): The node to format.

    Returns:
        str: A compact C-like representation of the node.
    """

    if node is None:
        return "<none>"

    BINARY_OPS = {
        NodeKind.ADD: "+",
        NodeKind.SUB: "-",
        NodeKind.MUL: "*",
        NodeKind.DIV: "/",
        NodeKind.ASSIGN: "=",
        NodeKind.EQ: "==",
        NodeKind.NE: "!=",
        NodeKind.LT: "<",
        NodeKind.LE: "<=",
    }

    if node.kind in BINARY_OPS:
        op = BINARY_OPS[node.kind]
        return f"({formatNode(node.lhs)} {op} {formatNode(node.rhs)})"

    match node.kind:
        case NodeKind.NUM:
            return str(node.val)

        case NodeKind.VAR:
            if node.var.initData is not None:
                return _formatStringLiteral(node.var.initData)
            return node.var.name

        case NodeKind.NEG:
            return f"-({formatNode(node.lhs)})"

        case NodeKind.ADDR:
            return f"&{formatNode(node.lhs)}"

        case NodeKind.DEREF:
            return f"*{formatNode(node.lhs)}"

        case NodeKind.FUNCALL:
            args = ", ".join(formatNode(arg) for arg in node.args)
            return f"{node.funcName}({args})"

        case NodeKind.EXPR_STMT:
            return formatNode(node.lhs)

        case NodeKind.RETURN:
            return f"return {formatNode(node.lhs)}"

        case NodeKind.IF:
            s = f"if ({formatNode(node.cond)}) {formatNode(node.then)}"
            if node.els is not None:
                s += f" else {formatNode(node.els)}"
            return s

        case NodeKind.FOR:
            if node.init is None and node.inc is None:
                return f"while ({formatNode(node.cond)}) {formatNode(node.then)}"
            return (
                f"for ({formatNode(node.init)}; {formatNode(node.cond)}; "
                f"{formatNode(node.inc)}) {formatNode(node.then)}"
            )

        case NodeKind.BLOCK:
            stmts = " ".join(formatNode(stmt) for stmt in node.body)
            return f"{{ {stmts} }}"

        case NodeKind.STMT_EXPR:
            stmts = " ".join(formatNode(stmt) for stmt in node.body)
            return f"({{ {stmts} }})"

        case _:
            return f"<{node.kind.name}>"


_PLACEHOLDER = "__T__"


def formatDtype(dtype: Dtype | None = None) -> str:
    """Formats a type as a valid C declaration.

    Args:
        dtype (Dtype | None): The type to format.

    Returns:
        str: A C declaration representing the type.
    """

    if dtype is None:
        return "<none>"

    def declarator(dtype: Dtype) -> str:
        match dtype.kind:
            case DtypeKind.CHAR | DtypeKind.INT:
                return _PLACEHOLDER

            case DtypeKind.PTR:
                decl = declarator(dtype.base)

                # If the placeholder is immediately followed by a postfix
                # operator, parenthesize before prepending '*'.
                idx = decl.find(_PLACEHOLDER)
                after = decl[idx + len(_PLACEHOLDER) :] if idx != -1 else ""

                if after.startswith(("[", "(")):
                    return decl.replace(_PLACEHOLDER, f"(*{_PLACEHOLDER})", 1)

                return decl.replace(_PLACEHOLDER, f"*{_PLACEHOLDER}", 1)

            case DtypeKind.ARRAY:
                decl = declarator(dtype.base)
                return decl.replace(
                    _PLACEHOLDER, f"{_PLACEHOLDER}[{dtype.arrayLen}]", 1
                )

            case DtypeKind.FUNC:
                decl = declarator(dtype.returnDtype)
                params = ", ".join(formatDtype(param) for param in dtype.params)
                return decl.replace(_PLACEHOLDER, f"{_PLACEHOLDER}({params})", 1)

            case _:
                return f"<{dtype.kind.name}>"

    def baseTypeName(dtype: Dtype) -> str:
        match dtype.kind:
            case DtypeKind.CHAR:
                return "char"

            case DtypeKind.INT:
                return "int"

            case DtypeKind.PTR | DtypeKind.ARRAY:
                return baseTypeName(dtype.base)

            case DtypeKind.FUNC:
                return baseTypeName(dtype.returnDtype)

            case _:
                return "<unknown>"

    decl = declarator(dtype)
    return f"{baseTypeName(dtype)} {decl.replace(_PLACEHOLDER, '')}".rstrip()

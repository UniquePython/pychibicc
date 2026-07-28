from __future__ import annotations

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


def formatNode(node: Node | None) -> str:
    """Formats an AST node as a compact C-like expression.

    Args:
        node (Node | None): The node to format.

    Returns:
        str: A compact C-like representation of the node.
    """

    if node is None:
        return "<none>"

    match node.kind:
        case NodeKind.NUM:
            return str(node.val)

        case NodeKind.VAR:
            if node.var.initData is not None:
                return _formatStringLiteral(node.var.initData)
            return node.var.name

        case NodeKind.NEG:
            return f"-({formatNode(node.lhs)})"

        case NodeKind.ADD:
            return f"({formatNode(node.lhs)} + {formatNode(node.rhs)})"

        case NodeKind.SUB:
            return f"({formatNode(node.lhs)} - {formatNode(node.rhs)})"

        case NodeKind.MUL:
            return f"({formatNode(node.lhs)} * {formatNode(node.rhs)})"

        case NodeKind.DIV:
            return f"({formatNode(node.lhs)} / {formatNode(node.rhs)})"

        case NodeKind.ASSIGN:
            return f"({formatNode(node.lhs)} = {formatNode(node.rhs)})"

        case NodeKind.EQ:
            return f"({formatNode(node.lhs)} == {formatNode(node.rhs)})"

        case NodeKind.NE:
            return f"({formatNode(node.lhs)} != {formatNode(node.rhs)})"

        case NodeKind.LT:
            return f"({formatNode(node.lhs)} < {formatNode(node.rhs)})"

        case NodeKind.LE:
            return f"({formatNode(node.lhs)} <= {formatNode(node.rhs)})"

        case NodeKind.ADDR:
            return f"&{formatNode(node.lhs)}"

        case NodeKind.DEREF:
            return f"*{formatNode(node.lhs)}"

        case NodeKind.FUNCALL:
            args = ", ".join(formatNode(arg) for arg in node.args)
            return f"{node.funcName}({args})"

        case NodeKind.EXPR_STMT:
            return formatNode(node.lhs)

        case _:
            return f"<{node.kind.name}>"


_PLACEHOLDER = "__T__"


def formatDtype(dtype: Dtype) -> str:
    """Formats a type as a valid C declaration.

    Args:
        dtype (Dtype): The type to format.

    Returns:
        str: A C declaration representing the type.
    """

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

import argparse
import sys

from pychibicc.backend.asm_writer import AsmWriter, Syntax
from pychibicc.backend.codegen import CodeGenerator
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokenizer import Tokenizer
from pychibicc.parser.parser import Parser


def readFile(path: str) -> str:
    """Reads the contents of a source file, or stdin if `path` is "-".

    By convention, a path of "-" means"read from stdin" instead of
    opening a real file. The returned text is guaranteed to end with a
    newline, since the rest of the pipeline (in particular error reporting,
    which scans forward from a positionto the next newline) assumes every
    line is newline-terminated.

    Args:
        path (str): Path to the source file to read, or "-" for stdin.

    Returns:
        str: The file's contents, guaranteed to end with "\\n".
    """
    if path == "-":
        content = sys.stdin.read()
    else:
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            ErrorReporter.error(f"cannot open {path}: {e.strerror}")

    if not content.endswith("\n"):
        content += "\n"

    return content


def main() -> None:
    cli = argparse.ArgumentParser(prog="pychibicc")

    cli.add_argument(
        "source",
        help='Path to the C source file to compile, or "-" to read from stdin.',
    )

    cli.add_argument(
        "-masm",
        dest="syntax",
        type=Syntax,
        choices=list(Syntax),
        default=Syntax.ATT,
        help="Assembly syntax to emit (default: att).",
    )

    args = cli.parse_args()

    path = args.source
    syntax = args.syntax

    source = readFile(path)
    filename = "<stdin>" if path == "-" else path

    errorReporter = ErrorReporter(source, filename)

    tokenizer = Tokenizer(errorReporter)
    tokens = tokenizer.tokenize()

    parser = Parser(errorReporter, tokens)
    program = parser.parse()

    asmWriter = AsmWriter(syntax)

    codeGenerator = CodeGenerator(asmWriter, errorReporter)
    code = codeGenerator.codegen(program)

    print(code)


if __name__ == "__main__":
    main()

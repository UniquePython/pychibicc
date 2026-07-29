from __future__ import annotations

import argparse
import sys
from typing import TextIO

from dight.backend.asm_writer import AsmWriter, Syntax
from dight.backend.codegen import CodeGenerator
from dight.diagnostics.error_reporter import ErrorReporter
from dight.frontend.tokenizer import Tokenizer
from dight.parser.parser import Parser


def readFile(path: str) -> str:
    """Read the contents of a source file.

    A path of "-" is treated specially and causes input to be read
    from stdin. The returned source is guaranteed to end with a newline,
    as later compiler stages assume every line is newline-terminated.

    Args:
        path: Path to the source file, or "-" to read from stdin.

    Returns:
        The contents of the source file with a trailing newline.

    Raises:
        SystemExit: If the file cannot be opened.
    """
    if path == "-":
        content = sys.stdin.read()
    else:
        try:
            with open(path, encoding="utf-8") as file:
                content = file.read()
        except OSError as error:
            ErrorReporter.error(f"cannot open input file: {path}: {error.strerror}")

    if not content.endswith("\n"):
        content += "\n"

    return content


def openFile(path: str | None) -> TextIO:
    """Open an output file.

    A path of None or "-" writes output to stdout.

    Args:
        path: Output path, or None / "-" for stdout.

    Returns:
        A writable text stream.

    Raises:
        SystemExit: If the output file cannot be opened.
    """
    if path is None or path == "-":
        return sys.stdout

    try:
        return open(path, "w", encoding="utf-8")
    except OSError as error:
        ErrorReporter.error(f"cannot open output file: {path}: {error.strerror}")


def main() -> None:
    """Compile a C source file into assembly.

    The compilation pipeline follows the following stages:

    1. Read source file.
    2. Tokenize source.
    3. Parse tokens into an AST.
    4. Traverse AST and emit assembly.
    """
    cli = argparse.ArgumentParser(prog="dight")

    cli.add_argument(
        "source",
        help="C source file to compile, or '-' to read from stdin.",
    )

    cli.add_argument(
        "-o",
        metavar="path",
        help="Write output to <path>.",
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

    sourcePath: str = args.source
    outputPath: str | None = args.o
    syntax: Syntax = args.syntax

    source: str = readFile(sourcePath)

    filename: str = "<stdin>" if sourcePath == "-" else sourcePath

    errorReporter = ErrorReporter(source, filename)

    # Tokenize and parse.
    tokenizer = Tokenizer(errorReporter)
    tokens = tokenizer.tokenize()

    parser = Parser(errorReporter, tokens)
    program = parser.parse()

    # Traverse the AST to emit assembly.
    output = openFile(outputPath)

    try:
        asmWriter = AsmWriter(syntax)

        codeGenerator = CodeGenerator(
            asmWriter,
            errorReporter,
        )

        assembly: str = codeGenerator.codegen(program)
        output.write(assembly)

    finally:
        if output is not sys.stdout:
            output.close()


if __name__ == "__main__":
    main()

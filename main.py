import argparse

from pychibicc.backend.asm_writer import AsmWriter, Syntax
from pychibicc.backend.codegen import CodeGenerator
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokenizer import Tokenizer
from pychibicc.parser.parser import Parser


def main() -> None:
    cli = argparse.ArgumentParser(prog="pychibicc")

    cli.add_argument(
        "source",
        help="The C source code to compile.",
    )

    cli.add_argument(
        "-masm",
        dest="syntax",
        type=Syntax,
        choices=list(Syntax),
        default=Syntax.ATT,
        metavar="{att,intel}",
        help="Assembly syntax to emit (default: att).",
    )

    args = cli.parse_args()

    source = args.source
    syntax = args.syntax

    errorReporter = ErrorReporter(source)

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

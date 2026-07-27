import sys

from pychibicc.backend.asm_writer import AsmWriter, Syntax
from pychibicc.backend.codegen import CodeGenerator
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokenizer import Tokenizer
from pychibicc.parser.parser import Parser


def main() -> None:
    if not (2 <= len(sys.argv) <= 3):
        ErrorReporter.error(
            f"{sys.argv[0]}: invalid number of arguments\n"
            "Usage: main.py <source> [att|intel]"
        )

    source = sys.argv[1]

    if len(sys.argv) == 3:
        syntaxStr = sys.argv[2]

        try:
            syntax = Syntax(syntaxStr)
        except ValueError:
            ErrorReporter.error(
                f"unknown assembly syntax: {syntaxStr}\n"
                f"Valid syntaxes are: {', '.join(Syntax)}"
            )
    else:
        syntax = Syntax.ATT

    errorReporter = ErrorReporter(source)

    tokenizer = Tokenizer(errorReporter)
    tokens = tokenizer.tokenize()

    parser = Parser(errorReporter, tokens)
    node = parser.parse()

    asmWriter = AsmWriter(syntax)

    codeGenerator = CodeGenerator(asmWriter, errorReporter)
    code = codeGenerator.codegen(node)

    print(code)


if __name__ == "__main__":
    main()

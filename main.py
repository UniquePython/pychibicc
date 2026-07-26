import sys

from codegen import CodeGenerator
from error_reporter import ErrorReporter
from parser import Parser
from tokenizer import Tokenizer


def main() -> None:
    if len(sys.argv) != 3:
        ErrorReporter.error(
            f"{sys.argv[0]}: invalid number of arguments\n"
            "Usage: main.py <source> <att|intel>"
        )

    source = sys.argv[1]
    syntax = sys.argv[2]

    errorReporter = ErrorReporter(source)

    tokenizer = Tokenizer(errorReporter)
    tokens = tokenizer.tokenize()

    parser = Parser(errorReporter, tokens)
    node = parser.parse()

    codeGenerator = CodeGenerator(errorReporter, syntax)
    code = codeGenerator.codegen(node)

    print(code)


if __name__ == "__main__":
    main()

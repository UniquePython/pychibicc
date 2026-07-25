import sys

from codegen import CodeGenerator
from error import error
from parser import Parser
from tokenizer import Tokenizer


def main() -> None:
    if len(sys.argv) != 3:
        error(
            f"{sys.argv[0]}: invalid number of arguments\n"
            "Usage: main.py <source> <att|intel>"
        )

    source = sys.argv[1]
    syntax = sys.argv[2]

    tokenizer = Tokenizer(source)
    tokens = tokenizer.tokenize()

    parser = Parser(source, tokens)
    node = parser.parse()

    codeGenerator = CodeGenerator(syntax)
    code = codeGenerator.codegen(node)

    print(code)


if __name__ == "__main__":
    main()

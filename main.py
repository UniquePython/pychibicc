import sys


def parseNumber(expr: str, idx: int) -> tuple[int, int]:
    start = idx

    while idx < len(expr) and expr[idx].isdigit():
        idx += 1

    if start == idx:
        return 0, idx

    return int(expr[start:idx]), idx


def main() -> None:
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        sys.exit(1)

    expr = sys.argv[1]
    idx = 0

    value, idx = parseNumber(expr, idx)

    print("\t.globl main")
    print("main:")
    print(f"\tmov ${value}, %rax")

    while idx < len(expr):
        if expr[idx] == "+":
            idx += 1
            value, idx = parseNumber(expr, idx)
            print(f"\tadd ${value}, %rax")
            continue

        if expr[idx] == "-":
            idx += 1
            value, idx = parseNumber(expr, idx)
            print(f"\tsub ${value}, %rax")
            continue

        print(f"unexpected character: '{expr[idx]}'", file=sys.stderr)
        sys.exit(1)

    print("\tret")

    sys.exit(0)


if __name__ == "__main__":
    main()

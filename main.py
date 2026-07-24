import sys


def main() -> None:
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        sys.exit(1)

    try:
        value = int(sys.argv[1])
    except ValueError:
        value = 0

    print("\t.globl main")
    print("main:")
    print(f"\tmov ${value}, %rax")
    print("\tret")

    sys.exit(0)


if __name__ == "__main__":
    main()

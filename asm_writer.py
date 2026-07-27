from enum import StrEnum

from cint import CInt


class Syntax(StrEnum):
    """Assembly syntax flavors the writer can emit."""

    ATT = "att"
    INTEL = "intel"


class AsmWriter:
    """Formats and emits x86-64 assembly text in a chosen syntax flavor."""

    def __init__(self, syntax: Syntax = Syntax.ATT):
        """Initializes the assembly writer.

        Args:
            syntax (Syntax): Assembly syntax to emit, either `Syntax.ATT` (default) or `Syntax.INTEL`.
        """
        self.syntax = syntax
        self.code: list[str] = []

    def mem(self, base: str, disp: CInt = 0) -> str:
        """Formats a memory operand: dereference `base`, optionally offset by `disp` bytes.

        Args:
            base (str): The bare base register name (e.g. "rbp").
            disp (CInt): Byte displacement, may be negative.

        Returns:
            str: The formatted memory operand for the current syntax.
        """
        if self.syntax == Syntax.ATT:
            reg = self.reg(base)
            return f"{disp}({reg})" if disp else f"({reg})"
        else:
            if disp > 0:
                return f"[{base}+{disp}]"
            elif disp < 0:
                return f"[{base}{disp}]"
            else:
                return f"[{base}]"

    def reg(self, name: str) -> str:
        """Formats a register operand for the current syntax.

        Args:
            name (str): The bare register name (e.g. "rax").

        Returns:
            str: The formatted register operand.
        """
        return f"%{name}" if self.syntax == Syntax.ATT else name

    def imm(self, value: CInt) -> str:
        """Formats an immediate operand for the current syntax.

        Args:
            value (CInt): The immediate value.

        Returns:
            str: The formatted immediate operand.
        """
        return f"${value}" if self.syntax == Syntax.ATT else str(value)

    def emit1(self, mnemonic: str, operand: str) -> None:
        """Emits a one-operand instruction.

        Args:
            mnemonic (str): The instruction mnemonic.
            operand (str): The already-formatted operand.
        """
        self.code.append(f"\t{mnemonic} {operand}")

    def emit2(self, mnemonic: str, src: str, dst: str) -> None:
        """Emits a two-operand instruction, accounting for syntax operand order.

        Args:
            mnemonic (str): The instruction mnemonic.
            src (str): The already-formatted source operand (AT&T order).
            dst (str): The already-formatted destination operand (AT&T order).
        """
        if self.syntax == Syntax.ATT:
            self.code.append(f"\t{mnemonic} {src}, {dst}")
        else:
            self.code.append(f"\t{mnemonic} {dst}, {src}")

    def emit0(self, mnemonic: str) -> None:
        """Emits a zero-operand instruction.

        Args:
            mnemonic (str): The instruction mnemonic.
        """
        self.code.append(f"\t{mnemonic}")

    def label(self, name: str) -> str:
        """Formats a compiler-generated label.

        Args:
            name (str): The label name without a leading `.`

        Returns:
            str: The formatted label.
        """
        return f".pychibicc.{name}"

    def emitLabel(self, name: str) -> None:
        """Emits a label.

        Args:
            name (str): The label name without a leading `.`.
        """
        self.empty()
        self.code.append(f"{self.label(name)}:")

    def commentLast(self, text: str) -> None:
        """Appends a trailing comment to the most recently emitted line.

        Args:
            text (str): The comment text (no leading '#').
        """
        self.code[-1] += f"\t# {text}"

    def comment(self, text: str) -> None:
        """Appends a standalone comment line.

        Args:
            text (str): The comment text (no leading '#').
        """
        self.code.append(f"\t# {text}")

    def empty(self) -> None:
        """Appends an empty line."""
        self.code.append("")

    def directive(self, text: str) -> None:
        """Appends a raw, tab-indented assembler directive line.

        Args:
            text (str): The directive text, e.g. ".globl main".
        """
        self.code.append(f"\t{text}")

    def raw(self, text: str) -> None:
        """Appends a raw, unindented line, e.g. a bare label like "main:".

        Args:
            text (str): The raw line text.
        """
        self.code.append(text)

    def getValue(self) -> str:
        """Returns the accumulated assembly text.

        Returns:
            str: The full assembly source generated so far, newline-joined.
        """
        return "\n".join(self.code)

from error import error
from functions import Function
from nodes import Node, NodeKind


def alignTo(n: int, align: int) -> int:
    """Rounds up a value to the nearest multiple of the specified alignment.

    Args:
        n (int): The value to align.
        align (int): The alignment boundary.

    Returns:
        int: The aligned value.
    """
    return (n + align - 1) // align * align


def assignLVarOffsets(function: Function) -> None:
    """Assigns stack offsets to local variables.

    Args:
        function (Function): The function whose local variables are to be assigned offsets.
    """
    offset = 0

    for var in function.locals:
        offset += 8
        var.offset = -offset

    function.stackSize = alignTo(offset, 16)


class CodeGenerator:
    """Generates x86-64 assembly code from an abstract syntax tree (AST)."""

    def __init__(self, syntax: str = "att"):
        """Initializes the code generator.

        Args:
            syntax (str): Assembly syntax to emit, either "att" or "intel".
        """
        if syntax not in ("att", "intel"):
            error(f"unknown assembly syntax: {syntax}")

        self.depth = 0
        self.labelCount = 1
        self.code: list[str] = []
        self.syntax = syntax

    def mem(self, base: str, disp: int = 0) -> str:
        """Formats a memory operand: dereference `base`, optionally offset by `disp` bytes.

        Args:
            base (str): The bare base register name (e.g. "rbp").
            disp (int): Byte displacement, may be negative.

        Returns:
            str: The formatted memory operand for the current syntax.
        """
        if self.syntax == "att":
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
        return f"%{name}" if self.syntax == "att" else name

    def imm(self, value: int) -> str:
        """Formats an immediate operand for the current syntax.

        Args:
            value (int): The immediate value.

        Returns:
            str: The formatted immediate operand.
        """
        return f"${value}" if self.syntax == "att" else str(value)

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
        if self.syntax == "att":
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

    def count(self) -> int:
        """Returns a unique sequential identifier.

        Returns:
            int: The next unique identifier.
        """
        value = self.labelCount
        self.labelCount += 1
        return value

    def push(self) -> None:
        """Pushes the value in %rax onto the stack."""
        self.emit1("push", self.reg("rax"))
        self.depth += 1

    def pop(self, name: str) -> None:
        """Pops the top value from the stack into the specified register.

        Args:
            name (str): The bare destination register name (e.g. "rdi").
        """
        self.emit1("pop", self.reg(name))
        self.depth -= 1

    def genAddr(self, node: Node) -> None:
        """Generates the absolute address of the specified node.

        Args:
            node (Node): The node whose address is to be generated.

        Raises:
            SystemExit: If the node does not represent an lvalue.
        """
        match node.kind:
            case NodeKind.VAR:
                self.emit2("lea", self.mem("rbp", node.var.offset), self.reg("rax"))
                self.commentLast(node.var.name)
                return

        error("not an lvalue")

    def genExpr(self, node: Node) -> None:
        """Generates assembly code for an expression.

        Args:
            node (Node): The root node of the expression to generate.

        Raises:
            SystemExit: If the expression node kind is invalid.
        """
        match node.kind:
            case NodeKind.NUM:
                self.emit2("mov", self.imm(node.val), self.reg("rax"))
                return

            case NodeKind.NEG:
                self.genExpr(node.lhs)
                self.emit1("neg", self.reg("rax"))
                return

            case NodeKind.VAR:
                self.genAddr(node)
                self.emit2("mov", self.mem("rax"), self.reg("rax"))
                return

            case NodeKind.ASSIGN:
                self.genAddr(node.lhs)
                self.push()
                self.genExpr(node.rhs)
                self.pop("rdi")
                self.emit2("mov", self.reg("rax"), self.mem("rdi"))
                return

        self.genExpr(node.rhs)
        self.push()
        self.genExpr(node.lhs)
        self.pop("rdi")

        match node.kind:
            case NodeKind.ADD:
                self.emit2("add", self.reg("rdi"), self.reg("rax"))
                return

            case NodeKind.SUB:
                self.emit2("sub", self.reg("rdi"), self.reg("rax"))
                return

            case NodeKind.MUL:
                self.emit2("imul", self.reg("rdi"), self.reg("rax"))
                return

            case NodeKind.DIV:
                self.emit0("cqo")
                self.emit1("idiv", self.reg("rdi"))
                return

            case NodeKind.EQ | NodeKind.NE | NodeKind.LT | NodeKind.LE:
                self.emit2("cmp", self.reg("rdi"), self.reg("rax"))

                setInstruction = {
                    NodeKind.EQ: "sete",
                    NodeKind.NE: "setne",
                    NodeKind.LT: "setl",
                    NodeKind.LE: "setle",
                }[node.kind]

                self.emit1(setInstruction, self.reg("al"))

                extendInstruction = "movzx" if self.syntax == "intel" else "movzb"
                self.emit2(extendInstruction, self.reg("al"), self.reg("rax"))
                return

        error("invalid expression")

    def genStmt(self, node: Node) -> None:
        """Generates assembly code for a statement.

        Args:
            node (Node): The statement node to generate.

        Raises:
            SystemExit: If the statement node kind is invalid.
        """
        match node.kind:
            case NodeKind.IF:
                c = self.count()

                self.genExpr(node.cond)
                self.emit2("cmp", self.imm(0), self.reg("rax"))
                self.emit1("je", self.label(f"else.{c}"))

                self.genStmt(node.then)
                self.emit1("jmp", self.label(f"end.{c}"))

                self.emitLabel(f"else.{c}")
                if node.els is not None:
                    self.genStmt(node.els)

                self.emitLabel(f"end.{c}")
                return

            case NodeKind.FOR:
                c = self.count()

                self.genStmt(node.init)

                self.emitLabel(f"begin.{c}")

                if node.cond is not None:
                    self.genExpr(node.cond)
                    self.emit2("cmp", self.imm(0), self.reg("rax"))
                    self.emit1("je", self.label(f"end.{c}"))

                self.genStmt(node.then)

                if node.inc is not None:
                    self.genExpr(node.inc)

                self.emit1("jmp", self.label(f"begin.{c}"))
                self.emitLabel(f"end.{c}")
                return

            case NodeKind.BLOCK:
                for stmt in node.body:
                    self.genStmt(stmt)
                return

            case NodeKind.RETURN:
                self.genExpr(node.lhs)
                self.emit1("jmp", self.label("return"))
                return

            case NodeKind.EXPR_STMT:
                self.empty()
                self.genExpr(node.lhs)
                return

        error("invalid statement")

    def codegen(self, program: Function) -> str:
        """Generates assembly code for the specified program.

        Args:
            program (Function): The program to generate code for.

        Returns:
            str: The generated assembly code.
        """
        assignLVarOffsets(program)

        if self.syntax == "intel":
            self.code.append("\t.intel_syntax noprefix")

        self.code.append("\t.globl main")
        self.code.append("main:")

        # Prologue.
        self.empty()
        self.comment("Prologue")
        self.emit1("push", self.reg("rbp"))
        self.commentLast("save caller's frame pointer")
        self.emit2("mov", self.reg("rsp"), self.reg("rbp"))
        self.commentLast("establish new frame pointer")
        self.emit2("sub", self.imm(program.stackSize), self.reg("rsp"))
        self.commentLast(f"reserve {program.stackSize} bytes for locals")

        if program.locals:
            self.empty()
            self.comment("Stack Frame:")
            for var in program.locals:
                self.comment(f"\t{self.mem('rbp', var.offset)}: {var.name}")

        self.genStmt(program.body)
        assert self.depth == 0

        self.emitLabel("return")
        self.emit2("mov", self.reg("rbp"), self.reg("rsp"))
        self.commentLast("deallocate stack frame")
        self.emit1("pop", self.reg("rbp"))
        self.commentLast("restore caller's frame pointer")
        self.emit0("ret")

        return "\n".join(self.code)

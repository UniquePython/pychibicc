from error import error
from nodes import Node, NodeKind


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
        self.code: list[str] = []
        self.syntax = syntax

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

        # Fast path: if rhs is a bare literal, use it as an immediate operand
        # directly instead of round-tripping it through the stack.
        rhsIsLiteral = node.rhs.kind == NodeKind.NUM

        if rhsIsLiteral:
            self.genExpr(node.lhs)
        else:
            self.genExpr(node.rhs)
            self.push()
            self.genExpr(node.lhs)
            self.pop("rdi")

        match node.kind:
            case NodeKind.ADD:
                rhsOperand = self.imm(node.rhs.val) if rhsIsLiteral else self.reg("rdi")
                self.emit2("add", rhsOperand, self.reg("rax"))
                return

            case NodeKind.SUB:
                rhsOperand = self.imm(node.rhs.val) if rhsIsLiteral else self.reg("rdi")
                self.emit2("sub", rhsOperand, self.reg("rax"))
                return

            case NodeKind.MUL:
                rhsOperand = self.imm(node.rhs.val) if rhsIsLiteral else self.reg("rdi")
                self.emit2("imul", rhsOperand, self.reg("rax"))
                return

            case NodeKind.DIV:
                # idiv cannot take an immediate operand on x86-64, so a literal
                # rhs still needs to be materialized into a register (just via
                # a direct mov, not push/pop).
                if rhsIsLiteral:
                    self.emit2("mov", self.imm(node.rhs.val), self.reg("rdi"))

                self.emit0("cqo")
                self.emit1("idiv", self.reg("rdi"))
                return

            case NodeKind.EQ | NodeKind.NE | NodeKind.LT | NodeKind.LE:
                rhsOperand = self.imm(node.rhs.val) if rhsIsLiteral else self.reg("rdi")
                self.emit2("cmp", rhsOperand, self.reg("rax"))

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
            case NodeKind.EXPR_STMT:
                self.genExpr(node.lhs)
                return

        error("invalid statement")

    def codegen(self, nodes: list[Node]) -> str:
        """Generates assembly code for the specified abstract syntax trees.

        Args:
            nodes (list[Node]): The list of statement nodes.

        Returns:
            str: The generated assembly code.
        """
        if self.syntax == "intel":
            self.code.append("\t.intel_syntax noprefix")

        self.code.append("\t.globl main")
        self.code.append("main:")

        for node in nodes:
            self.genStmt(node)
            assert self.depth == 0

        self.emit0("ret")

        return "\n".join(self.code)

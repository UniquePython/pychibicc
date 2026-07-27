from asm_writer import AsmWriter, Syntax
from error_reporter import ErrorReporter
from functions import Function
from nodes import Node, NodeKind, formatNode


def alignTo(n: int, align: int) -> int:
    """Rounds up a value to the nearest multiple of the specified alignment.

    Args:
        n (int): The value to align.
        align (int): The alignment boundary.

    Returns:
        int: The aligned value.
    """
    return (n + align - 1) // align * align


def assignLVarOffsets(functions: list[Function]) -> None:
    """Assigns stack offsets to local variables.

    Args:
        functions (list[Function]): The parsed functions.
    """
    for function in functions:
        offset = 0

        for var in reversed(function.locals):
            offset += 8
            var.offset = -offset

        function.stackSize = alignTo(offset, 16)


ARG_REGS = ("rdi", "rsi", "rdx", "rcx", "r8", "r9")


class CodeGenerator:
    """Generates x86-64 assembly code from an abstract syntax tree (AST)."""

    def __init__(self, asmWriter: AsmWriter, errorReporter: ErrorReporter):
        """Initializes the code generator.

        Args:
            asmWriter(AsmWriter): The assembly writer initialized with chosen assembly flavor.
            errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
        """
        self.depth = 0
        self.labelCount = 1
        self.currentFunction: Function | None = None

        self.w = asmWriter
        self.errorReporter = errorReporter

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
        self.w.emit1("push", self.w.reg("rax"))
        self.depth += 1

    def pop(self, name: str) -> None:
        """Pops the top value from the stack into the specified register.

        Args:
            name (str): The bare destination register name (e.g. "rdi").
        """
        self.w.emit1("pop", self.w.reg(name))
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
                self.w.emit2(
                    "lea", self.w.mem("rbp", node.var.offset), self.w.reg("rax")
                )
                return

            case NodeKind.DEREF:
                self.genExpr(node.lhs)
                return

        self.errorReporter.errorTok(node.tok, f"{formatNode(node)} is not an lvalue")

    def genExpr(self, node: Node) -> None:
        """Generates assembly code for an expression.

        Args:
            node (Node): The root node of the expression to generate.

        Raises:
            SystemExit: If the expression node kind is invalid.
        """
        match node.kind:
            case NodeKind.NUM:
                self.w.emit2("mov", self.w.imm(node.val), self.w.reg("rax"))
                return

            case NodeKind.NEG:
                self.genExpr(node.lhs)
                self.w.emit1("neg", self.w.reg("rax"))
                return

            case NodeKind.VAR:
                self.genAddr(node)
                self.w.emit2("mov", self.w.mem("rax"), self.w.reg("rax"))
                self.w.commentLast(f"{formatNode(node)}")
                return

            case NodeKind.DEREF:
                self.genExpr(node.lhs)
                self.w.emit2("mov", self.w.mem("rax"), self.w.reg("rax"))
                self.w.commentLast(f"load {formatNode(node)}")
                return

            case NodeKind.ADDR:
                self.genAddr(node.lhs)
                self.w.commentLast(f"{formatNode(node)}")
                return

            case NodeKind.ASSIGN:
                self.w.comment(f"{formatNode(node)}")

                self.genAddr(node.lhs)
                self.push()
                self.w.commentLast(f"save address of {formatNode(node.lhs)}")

                self.genExpr(node.rhs)

                self.pop("rdi")
                self.w.emit2("mov", self.w.reg("rax"), self.w.mem("rdi"))
                self.w.commentLast(f"store into {formatNode(node.lhs)}")
                return

            case NodeKind.FUNCALL:
                self.w.empty()
                self.w.comment(f"--- begin call to {formatNode(node)} ---")

                for i, arg in enumerate(node.args):
                    self.genExpr(arg)
                    self.push()
                    self.w.commentLast(f"arg {i}: {formatNode(arg)}")

                for reg in reversed(ARG_REGS[: len(node.args)]):
                    self.pop(reg)

                self.w.emit2("mov", self.w.imm(0), self.w.reg("rax"))
                self.w.emit1("call", node.funcName)

                self.w.comment(f"--- end call to {formatNode(node)} ---")
                self.w.empty()
                return

        self.genExpr(node.rhs)
        self.push()
        self.w.commentLast(f"save {formatNode(node.rhs)}")
        self.genExpr(node.lhs)
        self.pop("rdi")

        match node.kind:
            case NodeKind.ADD:
                self.w.emit2("add", self.w.reg("rdi"), self.w.reg("rax"))
                self.w.commentLast(formatNode(node))
                return

            case NodeKind.SUB:
                self.w.emit2("sub", self.w.reg("rdi"), self.w.reg("rax"))
                self.w.commentLast(formatNode(node))
                return

            case NodeKind.MUL:
                self.w.emit2("imul", self.w.reg("rdi"), self.w.reg("rax"))
                self.w.commentLast(formatNode(node))
                return

            case NodeKind.DIV:
                self.w.emit0("cqo")
                self.w.commentLast("sign-extend dividend")
                self.w.emit1("idiv", self.w.reg("rdi"))
                self.w.commentLast(formatNode(node))
                return

            case NodeKind.EQ | NodeKind.NE | NodeKind.LT | NodeKind.LE:
                self.w.comment(f"compare {formatNode(node)}")
                self.w.emit2("cmp", self.w.reg("rdi"), self.w.reg("rax"))

                setInstruction = {
                    NodeKind.EQ: "sete",
                    NodeKind.NE: "setne",
                    NodeKind.LT: "setl",
                    NodeKind.LE: "setle",
                }[node.kind]

                self.w.emit1(setInstruction, self.w.reg("al"))

                extendInstruction = (
                    "movzx" if self.w.syntax == Syntax.INTEL else "movzb"
                )
                self.w.emit2(extendInstruction, self.w.reg("al"), self.w.reg("rax"))
                return

        self.errorReporter.errorTok(node.tok, "internal error: invalid expression")

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

                self.w.comment(f"if ({formatNode(node.cond)})")

                self.genExpr(node.cond)
                self.w.emit2("cmp", self.w.imm(0), self.w.reg("rax"))
                self.w.commentLast(f"test {formatNode(node.cond)}")
                self.w.emit1("je", self.w.label(f"if.else.{c}"))

                self.w.comment("then")
                self.genStmt(node.then)
                self.w.emit1("jmp", self.w.label(f"if.end.{c}"))

                self.w.comment("else")
                self.w.emitLabel(f"if.else.{c}")
                if node.els is not None:
                    self.genStmt(node.els)

                self.w.emitLabel(f"if.end.{c}")
                return

            case NodeKind.FOR:
                if node.init is None and node.inc is None:
                    self.w.comment(f"while ({formatNode(node.cond)})")
                else:
                    self.w.comment(
                        f"for ({formatNode(node.init)}; "
                        f"{formatNode(node.cond)}; "
                        f"{formatNode(node.inc)})"
                    )

                c = self.count()

                if node.init is not None:
                    self.genStmt(node.init)

                self.w.emitLabel(f"for.begin.{c}")

                if node.cond is not None:
                    self.genExpr(node.cond)
                    self.w.commentLast(f"evaluate {formatNode(node.cond)}")
                    self.w.comment(f"test {formatNode(node.cond)}")
                    self.w.emit2("cmp", self.w.imm(0), self.w.reg("rax"))
                    self.w.emit1("je", self.w.label(f"for.end.{c}"))

                self.genStmt(node.then)

                if node.inc is not None:
                    self.w.comment(f"increment: {formatNode(node.inc)}")
                    self.genExpr(node.inc)

                self.w.emit1("jmp", self.w.label(f"for.begin.{c}"))
                self.w.emitLabel(f"for.end.{c}")
                return

            case NodeKind.BLOCK:
                for stmt in node.body:
                    self.genStmt(stmt)
                return

            case NodeKind.RETURN:
                self.genExpr(node.lhs)
                self.w.emit1("jmp", self.w.label(f"return.{self.currentFunction.name}"))
                return

            case NodeKind.EXPR_STMT:
                self.w.empty()
                self.genExpr(node.lhs)
                return

        self.errorReporter.errorTok(node.tok, "internal error: invalid statement")

    def codegen(self, program: list[Function]) -> str:
        """Generates assembly code for the specified program.

        Args:
            program (list[Function]): The program to generate code for.

        Returns:
            str: The generated assembly code.
        """
        assignLVarOffsets(program)

        if self.w.syntax == Syntax.INTEL:
            self.w.directive(".intel_syntax noprefix")

        for function in program:
            self.currentFunction = function

            self.w.empty()
            self.w.comment("==========================================================")
            self.w.comment(f"Function: {function.name}")
            self.w.comment(f"Stack size: {function.stackSize}")
            self.w.comment("==========================================================")
            self.w.empty()

            self.w.directive(f".globl {function.name}")
            self.w.raw(f"{function.name}:")

            # Prologue.
            self.w.empty()
            self.w.comment("--- Prologue ---")
            self.w.emit1("push", self.w.reg("rbp"))
            self.w.commentLast("save caller's frame pointer")
            self.w.emit2("mov", self.w.reg("rsp"), self.w.reg("rbp"))
            self.w.commentLast("establish new frame pointer")
            self.w.emit2("sub", self.w.imm(function.stackSize), self.w.reg("rsp"))
            self.w.commentLast(f"reserve {function.stackSize} bytes for locals")

            if function.locals:
                self.w.empty()
                self.w.comment("--- Stack Frame ---")
                for var in function.locals:
                    self.w.comment(f"\t{self.w.mem('rbp', var.offset)}: {var.name}")

            # Save passed-by-register arguments to their stack slots.
            for i, var in enumerate(function.params):
                self.w.emit2(
                    "mov", self.w.reg(ARG_REGS[i]), self.w.mem("rbp", var.offset)
                )
                self.w.commentLast(f"store parameter '{var.name}'")

            self.w.empty()
            self.w.comment("--- Body ---")
            self.genStmt(function.body)

            assert self.depth == 0, (
                f"unbalanced push/pop: depth={self.depth} at end of codegen"
            )

            # Epilogue.
            self.w.empty()
            self.w.comment("--- Epilogue ---")
            self.w.emitLabel(f"return.{function.name}")
            self.w.emit2("mov", self.w.reg("rbp"), self.w.reg("rsp"))
            self.w.commentLast("deallocate stack frame")
            self.w.emit1("pop", self.w.reg("rbp"))
            self.w.commentLast("restore caller's frame pointer")
            self.w.emit0("ret")

            self.w.empty()

        return self.w.getValue()

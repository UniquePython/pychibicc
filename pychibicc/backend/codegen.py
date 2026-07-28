from pychibicc.backend.asm_writer import AsmWriter, Syntax
from pychibicc.ctype.cint import CInt
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.syntax.dtypes import Dtype, DtypeKind
from pychibicc.syntax.nodes import Node, NodeKind, formatDtype, formatNode
from pychibicc.syntax.objects import Obj


def _alignTo(n: CInt, align: CInt) -> CInt:
    """Rounds up a value to the nearest multiple of the specified alignment.

    Args:
        n (CInt): The value to align.
        align (CInt): The alignment boundary.

    Returns:
        CInt: The aligned value.
    """
    return (n + align - 1) // align * align


def _assignLVarOffsets(program: list[Obj]) -> None:
    """Assigns stack offsets to local variables.

    Args:
        program (list[Obj]): The global objects.
    """
    for function in program:
        if not function.isFunction:
            continue

        offset = 0

        for var in reversed(function.locals):
            offset += var.dtype.size
            var.offset = -offset

        function.stackSize = _alignTo(offset, 16)


_ARG_REGS_8 = ("dil", "sil", "dl", "cl", "r8b", "r9b")
_ARG_REGS_64 = ("rdi", "rsi", "rdx", "rcx", "r8", "r9")


class CodeGenerator:
    """Generates x86-64 assembly code from an abstract syntax tree (AST)."""

    def __init__(self, asmWriter: AsmWriter, errorReporter: ErrorReporter):
        """Initializes the code generator.

        Args:
            asmWriter(AsmWriter): The assembly writer initialized with chosen assembly flavor.
            errorReporter (ErrorReporter): The error reporter initialized with the source code that produced the token stream.
        """
        self._depth = 0
        self._labelCount = 1
        self._currentFunction: Obj | None = None

        self._w = asmWriter
        self._errorReporter = errorReporter

    def _count(self) -> CInt:
        """Returns a unique sequential identifier.

        Returns:
            CInt: The next unique identifier.
        """
        value = self._labelCount
        self._labelCount += 1
        return value

    def _push(self) -> None:
        """Pushes the value in %rax onto the stack."""
        self._w.emit1("push", self._w.reg("rax"))
        self._depth += 1

    def _pop(self, name: str) -> None:
        """Pops the top value from the stack into the specified register.

        Args:
            name (str): The bare destination register name (e.g. "rdi").
        """
        self._w.emit1("pop", self._w.reg(name))
        self._depth -= 1

    def _load(self, dtype: Dtype) -> None:
        """Loads the value pointed to by %rax into %rax.

        Arrays are not loaded. In C, evaluating an array expression yields the
        address of its first element (array-to-pointer decay) rather than the
        array itself.

        Args:
            dtype (Dtype): The type of the value pointed to by %rax.
        """
        if dtype.kind == DtypeKind.ARRAY:
            # Arrays are not loaded into registers. Their value is their address,
            # implementing array-to-pointer decay.
            return

        if dtype.size == 1:
            self._w.emit2("movsbq", self._w.mem("rax"), self._w.reg("rax"))
        else:
            self._w.emit2("mov", self._w.mem("rax"), self._w.reg("rax"))

    def _store(self, dtype: Dtype) -> None:
        """Stores %rax into the address at the top of the stack.

        Args:
            dtype (Dtype): The type of the value pointed to by %rax.
        """
        self._pop("rdi")

        if dtype.size == 1:
            self._w.emit2("mov", self._w.reg("al"), self._w.mem("rdi"))
        else:
            self._w.emit2("mov", self._w.reg("rax"), self._w.mem("rdi"))

    def _genAddr(self, node: Node) -> None:
        """Generates the absolute address of the specified node.

        Args:
            node (Node): The node whose address is to be generated.

        Raises:
            SystemExit: If the node does not represent an lvalue.
        """
        match node.kind:
            case NodeKind.VAR:
                if node.var.isLocal:
                    # Local variable
                    self._w.emit2(
                        "lea", self._w.mem("rbp", node.var.offset), self._w.reg("rax")
                    )
                else:
                    # Global variable
                    self._w.emit2(
                        "lea", self._w.mem("rip", node.var.name), self._w.reg("rax")
                    )
                return

            case NodeKind.DEREF:
                self._genExpr(node.lhs)
                return

        self._errorReporter.errorTok(node.tok, f"{formatNode(node)} is not an lvalue")

    def _genExpr(self, node: Node) -> None:
        """Generates assembly code for an expression.

        Args:
            node (Node): The root node of the expression to generate.

        Raises:
            SystemExit: If the expression node kind is invalid.
        """
        match node.kind:
            case NodeKind.NUM:
                self._w.emit2("mov", self._w.imm(node.val), self._w.reg("rax"))
                return

            case NodeKind.NEG:
                self._genExpr(node.lhs)
                self._w.emit1("neg", self._w.reg("rax"))
                return

            case NodeKind.VAR:
                self._genAddr(node)
                self._load(node.dtype)
                self._w.commentLast(f"load {formatNode(node)}")
                return

            case NodeKind.DEREF:
                self._genExpr(node.lhs)
                self._load(node.dtype)
                self._w.commentLast(f"load {formatNode(node)}")
                return

            case NodeKind.ADDR:
                self._genAddr(node.lhs)
                self._w.commentLast(f"{formatNode(node)}")
                return

            case NodeKind.ASSIGN:
                self._w.comment(f"{formatNode(node)}")

                self._genAddr(node.lhs)
                self._push()
                self._w.commentLast(f"save address of {formatNode(node.lhs)}")

                self._genExpr(node.rhs)

                self._store(node.dtype)
                self._w.commentLast(f"store into {formatNode(node.lhs)}")
                return

            case NodeKind.FUNCALL:
                self._w.empty()
                self._w.comment(f"--- begin call to {formatNode(node)} ---")

                for i, arg in enumerate(node.args):
                    self._genExpr(arg)
                    self._push()
                    self._w.commentLast(f"arg {i}: {formatNode(arg)}")

                for reg in reversed(_ARG_REGS_64[: len(node.args)]):
                    self._pop(reg)

                self._w.emit2("mov", self._w.imm(0), self._w.reg("rax"))
                self._w.emit1("call", node.funcName)

                self._w.comment(f"--- end call to {formatNode(node)} ---")
                self._w.empty()
                return

        self._genExpr(node.rhs)
        self._push()
        self._w.commentLast(f"save {formatNode(node.rhs)}")
        self._genExpr(node.lhs)
        self._pop("rdi")

        match node.kind:
            case NodeKind.ADD:
                self._w.emit2("add", self._w.reg("rdi"), self._w.reg("rax"))
                self._w.commentLast(formatNode(node))
                return

            case NodeKind.SUB:
                self._w.emit2("sub", self._w.reg("rdi"), self._w.reg("rax"))
                self._w.commentLast(formatNode(node))
                return

            case NodeKind.MUL:
                self._w.emit2("imul", self._w.reg("rdi"), self._w.reg("rax"))
                self._w.commentLast(formatNode(node))
                return

            case NodeKind.DIV:
                self._w.emit0("cqo")
                self._w.commentLast("sign-extend dividend")
                self._w.emit1("idiv", self._w.reg("rdi"))
                self._w.commentLast(formatNode(node))
                return

            case NodeKind.EQ | NodeKind.NE | NodeKind.LT | NodeKind.LE:
                self._w.comment(f"compare {formatNode(node)}")
                self._w.emit2("cmp", self._w.reg("rdi"), self._w.reg("rax"))

                setInstruction = {
                    NodeKind.EQ: "sete",
                    NodeKind.NE: "setne",
                    NodeKind.LT: "setl",
                    NodeKind.LE: "setle",
                }[node.kind]

                self._w.emit1(setInstruction, self._w.reg("al"))

                extendInstruction = (
                    "movzx" if self._w.syntax == Syntax.INTEL else "movzb"
                )
                self._w.emit2(extendInstruction, self._w.reg("al"), self._w.reg("rax"))
                return

        self._errorReporter.errorTok(node.tok, "internal error: invalid expression")

    def _genStmt(self, node: Node) -> None:
        """Generates assembly code for a statement.

        Args:
            node (Node): The statement node to generate.

        Raises:
            SystemExit: If the statement node kind is invalid.
        """
        match node.kind:
            case NodeKind.IF:
                c = self._count()

                self._w.comment(f"if ({formatNode(node.cond)})")

                self._genExpr(node.cond)
                self._w.emit2("cmp", self._w.imm(0), self._w.reg("rax"))
                self._w.commentLast(f"test {formatNode(node.cond)}")
                self._w.emit1("je", self._w.label(f"if.else.{c}"))

                self._w.comment("then")
                self._genStmt(node.then)
                self._w.emit1("jmp", self._w.label(f"if.end.{c}"))

                self._w.comment("else")
                self._w.emitLabel(f"if.else.{c}")
                if node.els is not None:
                    self._genStmt(node.els)

                self._w.emitLabel(f"if.end.{c}")
                return

            case NodeKind.FOR:
                if node.init is None and node.inc is None:
                    self._w.comment(f"while ({formatNode(node.cond)})")
                else:
                    self._w.comment(
                        f"for ({formatNode(node.init)}; "
                        f"{formatNode(node.cond)}; "
                        f"{formatNode(node.inc)})"
                    )

                c = self._count()

                if node.init is not None:
                    self._genStmt(node.init)

                self._w.emitLabel(f"for.begin.{c}")

                if node.cond is not None:
                    self._genExpr(node.cond)
                    self._w.commentLast(f"evaluate {formatNode(node.cond)}")
                    self._w.comment(f"test {formatNode(node.cond)}")
                    self._w.emit2("cmp", self._w.imm(0), self._w.reg("rax"))
                    self._w.emit1("je", self._w.label(f"for.end.{c}"))

                self._genStmt(node.then)

                if node.inc is not None:
                    self._w.comment(f"increment: {formatNode(node.inc)}")
                    self._genExpr(node.inc)

                self._w.emit1("jmp", self._w.label(f"for.begin.{c}"))
                self._w.emitLabel(f"for.end.{c}")
                return

            case NodeKind.BLOCK:
                for stmt in node.body:
                    self._genStmt(stmt)
                return

            case NodeKind.RETURN:
                self._genExpr(node.lhs)
                self._w.emit1(
                    "jmp", self._w.label(f"return.{self._currentFunction.name}")
                )
                return

            case NodeKind.EXPR_STMT:
                self._w.empty()
                self._genExpr(node.lhs)
                return

        self._errorReporter.errorTok(node.tok, "internal error: invalid statement")

    def _emitData(self, program: list[Obj]) -> None:
        """Emits assembly for the program's global variables.

        Global variables are placed in the data section, exported if
        necessary, labeled, and allocated zero-initialized storage.

        Args:
            program (list[Obj]): The program's global objects.
        """
        for var in program:
            if var.isFunction:
                continue

            self._w.comment(
                "=========================================================="
            )
            self._w.comment(f"Global variable: {var.name}")
            self._w.comment(f"Type: {formatDtype(var.dtype)}")
            self._w.comment(f"Size: {var.dtype.size} bytes")
            self._w.comment(
                "=========================================================="
            )
            self._w.empty()

            self._w.directive(".data")
            self._w.directive(f".globl {var.name}")
            self._w.raw(f"{var.name}:")
            self._w.directive(f".zero {var.dtype.size}")
            self._w.commentLast(f"reserve {var.dtype.size} bytes")
            self._w.empty()

    def _emitText(self, program: list[Obj]) -> None:
        """Emits assembly for the program's functions.

        Each function is emitted into the text section along with its
        prologue, stack frame setup, parameter handling, body, and
        epilogue.

        Args:
            program (list[Obj]): The program's global objects.
        """
        for function in program:
            if not function.isFunction:
                continue

            self._currentFunction = function

            self._w.empty()
            self._w.comment(
                "=========================================================="
            )
            self._w.comment(f"Function: {function.name}")
            self._w.comment(f"Stack size: {function.stackSize}")
            self._w.comment(
                "=========================================================="
            )
            self._w.empty()

            self._w.directive(f".globl {function.name}")
            self._w.directive(".text")
            self._w.raw(f"{function.name}:")

            # Prologue.
            self._w.empty()
            self._w.comment("--- Prologue ---")
            self._w.emit1("push", self._w.reg("rbp"))
            self._w.commentLast("save caller's frame pointer")
            self._w.emit2("mov", self._w.reg("rsp"), self._w.reg("rbp"))
            self._w.commentLast("establish new frame pointer")
            self._w.emit2("sub", self._w.imm(function.stackSize), self._w.reg("rsp"))
            self._w.commentLast(f"reserve {function.stackSize} bytes for locals")

            if function.locals:
                self._w.empty()
                self._w.comment("--- Stack Frame ---")
                for var in function.locals:
                    self._w.comment(f"\t{self._w.mem('rbp', var.offset)}: {var.name}")

            # Save passed-by-register arguments to their stack slots.
            for i, var in enumerate(function.params):
                if var.dtype.size == 1:
                    self._w.emit2(
                        "mov",
                        self._w.reg(_ARG_REGS_8[i]),
                        self._w.mem("rbp", var.offset),
                    )
                else:
                    self._w.emit2(
                        "mov",
                        self._w.reg(_ARG_REGS_64[i]),
                        self._w.mem("rbp", var.offset),
                    )
                self._w.commentLast(f"store parameter '{var.name}'")

            self._w.empty()
            self._w.comment("--- Body ---")
            self._genStmt(function.body)

            assert self._depth == 0, (
                f"unbalanced push/pop: depth={self._depth} at end of codegen"
            )

            # Epilogue.
            self._w.empty()
            self._w.comment("--- Epilogue ---")
            self._w.emitLabel(f"return.{function.name}")
            self._w.emit2("mov", self._w.reg("rbp"), self._w.reg("rsp"))
            self._w.commentLast("deallocate stack frame")
            self._w.emit1("pop", self._w.reg("rbp"))
            self._w.commentLast("restore caller's frame pointer")
            self._w.emit0("ret")

            self._w.empty()

    def codegen(self, program: list[Obj]) -> str:
        """Generates assembly code for the specified program.

        Args:
            program (list[Obj]): The program to generate code for.

        Returns:
            str: The generated assembly code.
        """
        _assignLVarOffsets(program)

        if self._w.syntax == Syntax.INTEL:
            self._w.directive(".intel_syntax noprefix")

        self._emitData(program)
        self._emitText(program)

        return self._w.getValue()

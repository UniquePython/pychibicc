#!/usr/bin/env python3
"""Fast in-process test runner for pychibicc.

Reads test cases from list.tests, one per line, in the form:

    <expected-result> <code>

e.g.:

    42 int main() { return 42; }

Runs each case by calling the compiler pipeline directly (no per-case
`python3 main.py ...` subprocess), then assembles+links+executes the
result with gcc. Compared to a naive shell-script runner, this avoids:
  - paying Python interpreter/import startup cost per test case
  - static linking (dynamic linking is meaningfully faster and is fine
    here since we run the binary immediately after building it)
and additionally runs cases across a process pool for free parallelism
on multi-core machines.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from pychibicc.backend.asm_writer import AsmWriter, Syntax
from pychibicc.backend.codegen import CodeGenerator
from pychibicc.diagnostics.error_reporter import ErrorReporter
from pychibicc.frontend.tokenizer import Tokenizer
from pychibicc.parser.parser import Parser

TESTS_FILE = SCRIPT_DIR / "list.tests"
BUILD_DIR = REPO_ROOT / "build"

# Helper functions test cases call into.
HELPER_SRC = """
int ret3() { return 3; }
int ret5() { return 5; }
int add(int x, int y) { return x+y; }
int sub(int x, int y) { return x-y; }

int add6(int a, int b, int c, int d, int e, int f) {
    return a+b+c+d+e+f;
}
"""


def load_cases(path: Path = TESTS_FILE) -> list[tuple[int, str]]:
    """Parses `<expected> <code>` lines out of a .tests file.

    Blank lines and lines starting with '#' are skipped, so the file can
    have breathing room / comments without confusing the parser.
    """
    cases: list[tuple[int, str]] = []
    for lineno, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        expected_str, _, code = line.partition(" ")
        if not code:
            raise ValueError(
                f"{path}:{lineno}: expected '<int> <code>', got: {raw_line!r}"
            )
        try:
            expected = int(expected_str)
        except ValueError as e:
            raise ValueError(
                f"{path}:{lineno}: expected leading integer, got: {expected_str!r}"
            ) from e

        cases.append((expected, code))

    return cases


def compile_source(source: str, syntax: Syntax) -> str:
    """Runs the pychibicc pipeline in-process (no subprocess/import cost)."""
    error_reporter = ErrorReporter(source)
    tokens = Tokenizer(error_reporter).tokenize()
    program = Parser(error_reporter, tokens).parse()
    asm_writer = AsmWriter(syntax)
    code_generator = CodeGenerator(asm_writer, error_reporter)
    return code_generator.codegen(program)


@dataclass
class CaseResult:
    index: int
    syntax: str
    source: str
    expected: int
    actual: int | None
    ok: bool
    error: str | None


def run_case(
    index: int,
    source: str,
    expected: int,
    syntax_name: str,
    helper_obj: str,
    build_dir: str,
) -> CaseResult:
    syntax = Syntax(syntax_name)

    try:
        asm = compile_source(source, syntax)
    except SystemExit as e:
        return CaseResult(
            index, syntax_name, source, expected, None, False, f"compile error: {e}"
        )

    work = Path(build_dir) / syntax_name / str(index)
    asm_path = work.with_suffix(".s")
    bin_path = work
    asm_path.write_text(asm)

    # No -static: dynamic link, meaningfully faster for local iteration.
    link = subprocess.run(
        ["gcc", "-o", str(bin_path), str(asm_path), helper_obj],
        capture_output=True,
        text=True,
        check=False,
    )
    if link.returncode != 0:
        return CaseResult(
            index,
            syntax_name,
            source,
            expected,
            None,
            False,
            f"link error: {link.stderr.strip()}",
        )

    run = subprocess.run([str(bin_path)], check=False)
    actual = run.returncode
    return CaseResult(
        index, syntax_name, source, expected, actual, actual == expected, None
    )


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "tests_file",
        nargs="?",
        default=str(TESTS_FILE),
        help="Path to the .tests file (default: list.tests).",
    )
    cli.add_argument(
        "--full",
        action="store_true",
        help="Also check intel syntax (default: att only).",
    )
    cli.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=None,
        help="Worker processes (default: os.cpu_count()).",
    )
    args = cli.parse_args()

    cases = load_cases(Path(args.tests_file))
    syntaxes = ["att", "intel"] if args.full else ["att"]

    # Wipe any previous run's output so stale files (e.g. from an older,
    # differently-ordered list.tests) can never be mistaken for fresh ones.
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    build_dir = str(BUILD_DIR)
    for syntax in syntaxes:
        (BUILD_DIR / syntax).mkdir(parents=True, exist_ok=True)

    helper_obj = str(BUILD_DIR / "helpers.o")
    subprocess.run(
        ["gcc", "-xc", "-c", "-o", helper_obj, "-"],
        input=HELPER_SRC,
        text=True,
        check=True,
    )

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(run_case, i, src, expected, syntax, helper_obj, build_dir)
            for i, (expected, src) in enumerate(cases, start=1)
            for syntax in syntaxes
        ]
        results = [f.result() for f in futures]
    elapsed = time.perf_counter() - t0

    results.sort(key=lambda r: (r.index, r.syntax))
    failures = [r for r in results if not r.ok]

    for r in failures:
        detail = r.error or f"expected {r.expected}, got {r.actual}"
        print(f"[{r.syntax}] test #{r.index}: {r.source!r} => {detail}")

    total = len(results)
    passed = total - len(failures)
    status = "OK" if not failures else "FAILED"
    print(
        f"\n{status}: {passed}/{total} passed in {elapsed:.2f}s "
        f"({len(cases)} cases x {len(syntaxes)} syntax(es))"
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

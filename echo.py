#!/usr/bin/env python3
"""
EchoLang — The Palindrome Esoteric Language
==============================================

Every program MUST be a palindrome (after stripping whitespace and
non-instruction characters).  The interpreter runs in two phases:

  Phase 1 — UNDO: scan the RIGHT half from right-to-left, applying
             the *reverse* semantics of every instruction.
  Phase 2 — DO:   scan the LEFT half (including the centre character
             if the length is odd) from left-to-right, applying the
             *normal* semantics.

Because the source is a palindrome, Phase 1 executes exactly the same
sequence of instructions as Phase 2 (minus the centre), but with every
operation inverted — and crucially, with the pointer starting at 0 in
each phase independently.  A `+` in Phase 1 subtracts; the same `+`
in Phase 2 adds.  If the pointer never moves, they cancel perfectly.
To leave a non-zero value behind you MUST arrange the pointer so that
the undo and the do land on different cells.

Instruction set (only three characters):
    +    DO: mem[ptr] += 1        UNDO: mem[ptr] -= 1
    >    DO: ptr += 1             UNDO: ptr -= 1
    ?    DO: output mem[ptr] as ASCII char
         UNDO: read one byte from stdin into mem[ptr]

Memory: 30000 cells, 8-bit unsigned (wrap on overflow/underflow).
Pointer: wraps around modulo 30000.
All other characters are comments and ignored for palindrome checking.
"""

import sys

MEMORY_SIZE = 30000
VALID_INSTRUCTIONS = set("+>?")


# ---------------------------------------------------------------------------
# Palindrome validation
# ---------------------------------------------------------------------------

def clean_source(raw: str) -> str:
    """Strip whitespace and non-instruction characters; return the code."""
    return "".join(ch for ch in raw if ch in VALID_INSTRUCTIONS)


def check_palindrome(code: str) -> None:
    """Raise SyntaxError with a helpful mismatch report if not a palindrome."""
    n = len(code)
    for i in range(n // 2):
        left = code[i]
        right = code[n - 1 - i]
        if left != right:
            raise SyntaxError(
                f"EchoLang programs must be palindromes.\n"
                f"  Mismatch at symmetric positions {i} and {n - 1 - i}:\n"
                f"    left  = '{left}'\n"
                f"    right = '{right}'\n"
                f"  Full code: {code}\n"
                f"  Hint: every instruction must mirror around the centre."
            )


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class EchoVM:
    def __init__(self, input_data: bytes = b"", debug: bool = False):
        self.mem = [0] * MEMORY_SIZE
        self.ptr = 0
        self.input_data = input_data
        self.input_pos = 0
        self.output: list[str] = []
        self.debug = debug
        self._step = 0

    # -- low-level operations ------------------------------------------------

    def _read_byte(self) -> int:
        if self.input_pos < len(self.input_data):
            b = self.input_data[self.input_pos]
            self.input_pos += 1
            return b
        return 0  # EOF → 0

    def _log(self, phase: str, idx: int, ch: str, desc: str) -> None:
        if self.debug:
            print(
                f"  [{phase} #{self._step:04d}] pos={idx:3d}  '{ch}'  "
                f"ptr={self.ptr:5d}  mem[ptr]={self.mem[self.ptr]:3d}  "
                f"| {desc}",
                file=sys.stderr,
            )
            self._step += 1

    # -- semantics -----------------------------------------------------------

    def do_plus(self, phase: str, idx: int) -> None:
        self.mem[self.ptr] = (self.mem[self.ptr] + 1) & 0xFF
        self._log(phase, idx, "+", "mem[ptr] += 1")

    def undo_plus(self, phase: str, idx: int) -> None:
        self.mem[self.ptr] = (self.mem[self.ptr] - 1) & 0xFF
        self._log(phase, idx, "+", "mem[ptr] -= 1  (UNDO)")

    def do_shift(self, phase: str, idx: int) -> None:
        self.ptr = (self.ptr + 1) % MEMORY_SIZE
        self._log(phase, idx, ">", "ptr += 1")

    def undo_shift(self, phase: str, idx: int) -> None:
        self.ptr = (self.ptr - 1) % MEMORY_SIZE
        self._log(phase, idx, ">", "ptr -= 1  (UNDO)")

    def do_output(self, phase: str, idx: int) -> None:
        ch = chr(self.mem[self.ptr])
        self.output.append(ch)
        self._log(phase, idx, "?", f"output '{ch}' (ord={self.mem[self.ptr]})")

    def undo_input(self, phase: str, idx: int) -> None:
        b = self._read_byte()
        self.mem[self.ptr] = b & 0xFF
        self._log(phase, idx, "?", f"input byte {b} → mem[ptr]  (UNDO)")

    # -- dispatch tables -----------------------------------------------------

    DO_TABLE = {
        "+": do_plus,
        ">": do_shift,
        "?": do_output,
    }

    UNDO_TABLE = {
        "+": undo_plus,
        ">": undo_shift,
        "?": undo_input,
    }

    # -- main run ------------------------------------------------------------

    def run(self, code: str) -> str:
        n = len(code)
        mid = (n + 1) // 2  # length of left half including centre

        if self.debug:
            print(f"--- code length={n}, left-half (with centre)={mid} ---",
                  file=sys.stderr)

        # Phase 1 — UNDO: right half, right-to-left, reverse semantics
        if self.debug:
            print("=== PHASE 1: UNDO (right half, right-to-left) ===",
                  file=sys.stderr)
        self.ptr = 0  # pointer resets at phase boundary
        for i in range(n - 1, mid - 1, -1):
            ch = code[i]
            self.UNDO_TABLE[ch](self, "UNDO", i)

        # Phase 2 — DO: left half (incl. centre), left-to-right, normal semantics
        if self.debug:
            print("=== PHASE 2: DO (left half, left-to-right) ===",
                  file=sys.stderr)
        self.ptr = 0  # pointer resets at phase boundary
        for i in range(mid):
            ch = code[i]
            self.DO_TABLE[ch](self, "DO", i)

        return "".join(self.output)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="echo",
        description="EchoLang interpreter — the palindrome esoteric language.",
    )
    parser.add_argument("file", nargs="?", help="EchoLang source file (.echo)")
    parser.add_argument("-e", "--exec", metavar="CODE",
                        help="run CODE directly instead of reading a file")
    parser.add_argument("-i", "--input", metavar="STR",
                        help="input string to feed to UNDO-phase '?' reads")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="print execution trace to stderr")
    args = parser.parse_args()

    if args.exec is not None:
        raw = args.exec
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        parser.print_help()
        sys.exit(1)

    code = clean_source(raw)
    if not code:
        print("error: no EchoLang instructions found (valid chars: + > ?)",
              file=sys.stderr)
        sys.exit(1)

    try:
        check_palindrome(code)
    except SyntaxError as e:
        print(f"SyntaxError: {e}", file=sys.stderr)
        sys.exit(1)

    # Input source: -i flag takes priority; otherwise read from stdin pipe.
    if args.input is not None:
        input_data = args.input.encode("utf-8")
    elif not sys.stdin.isatty():
        input_data = sys.stdin.buffer.read()
    else:
        input_data = b""
    vm = EchoVM(input_data=input_data, debug=args.debug)
    result = vm.run(code)
    sys.stdout.write(result)
    if result and not result.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()

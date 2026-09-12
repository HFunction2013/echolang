# EchoLang — The Palindrome Esoteric Language

> *Every instruction you write will first be undone, then done. To make
> anything stick, you must outrun your own echo.*

EchoLang is an esoteric programming language where **every program must be
a palindrome**.  Unlike naive "execute the first half" designs, EchoLang
makes *both halves semantically active*: the right half runs first with
**inverted** operations (UNDO), then the left half runs with normal
operations (DO).  Because the source is a palindrome, the two halves
contain the same instructions — so every non-centre instruction is
executed twice, once as its own inverse.

The result: a language with only **three instructions** that is fiendishly
difficult to write in, because nothing you do survives unless you arrange
the pointer so that the undo and the do land on *different memory cells*.

---

## Instruction Set

Only three characters are valid instructions.  All other characters are
comments and are ignored (including for palindrome checking).

| Char | DO semantics (left half, L→R) | UNDO semantics (right half, R→L) |
|------|-------------------------------|-----------------------------------|
| `+`  | `mem[ptr] += 1`               | `mem[ptr] -= 1`                   |
| `>`  | `ptr += 1`                     | `ptr -= 1`                         |
| `?`  | output `mem[ptr]` as ASCII    | read one byte from input → `mem[ptr]` |

- **Memory**: 30,000 cells, each an 8-bit unsigned integer (wraps on
  overflow / underflow).
- **Pointer**: wraps around modulo 30,000.
- **Input EOF**: reads as `0`.

---

## Execution Model

A program of length `n` is split at its centre:

```
<-------- left half (n+1)/2 chars --------><---- right half ---->
  instructions run with DO semantics          instructions run with
  left-to-right                                UNDO semantics, right-to-left
```

### Phase 1 — UNDO

The pointer is reset to `0`.  The **right half** is scanned from
**right to left**, and every instruction is executed with its **inverse**
semantics:

- `+` becomes *subtract*
- `>` becomes *shift left*
- `?` becomes *read input*

### Phase 2 — DO

The pointer is reset to `0` again.  The **left half** (including the
centre character if `n` is odd) is scanned from **left to right** with
**normal** semantics.

### Why the centre is special

If the program length is odd, the centre character belongs only to the
left half and is executed **once** (DO only).  This is the only
"safe" position — an instruction here is never undone.

If the length is even, *every* instruction is executed in both phases.

---

## The Core Insight: Why It's Hard

Consider the simplest possible program: `+?+` (a palindrome of length 3).

```
UNDO:  right half = "+" (R→L), ptr starts at 0
       '+' → mem[0] -= 1  →  mem[0] = 255

DO:    left half = "+?" (L→R), ptr reset to 0
       '+' → mem[0] += 1  →  mem[0] = 0
       '?' → output mem[0] → outputs NUL (0)
```

The `+` cancelled itself out perfectly.  **Without pointer movement, every
arithmetic operation in EchoLang is a no-op.**

To leave a non-zero value, you must make the UNDO-phase `-1` and the
DO-phase `+1` hit **different cells**.  The `>` instruction is the key:
in UNDO it shifts *left*, in DO it shifts *right* — so from the same
starting position of `0`, the two phases diverge immediately.

### The canonical trick

```
> +...+ ? +...+ >
```

**UNDO phase** (right half R→L: `>`, then `+`×N):
1. `>` (UNDO = shift left) → ptr = 29999
2. `+`×N (UNDO = subtract) → mem[29999] = (0 − N) mod 256

**DO phase** (left half L→R: `>`, then `+`×N, then `?`):
1. `>` (DO = shift right) → ptr = 1
2. `+`×N (DO = add) → mem[1] = N
3. `?` → output mem[1] = N

The UNDO-phase subtraction landed on cell 29999; the DO-phase addition
landed on cell 1.  They never met.  The output is `N`.

To output the character `'A'` (ASCII 65): `>` + `+`×65 + `?` + `+`×65 + `>`.

---

## Examples

### `A.echo` — Output the letter A

```
>+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++?+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++>
```

Output: `A`

### `Hi.echo` — Output "Hi"

Builds on the same pattern, using a fresh cell for each character:

```
> +×72 ? > +×105 ? +×105 > ? +×72 >
```

The first `?` (non-centre) outputs in DO and reads a byte in UNDO
(harmless if no input is provided).  The second `?` (centre) outputs only.

Output: `Hi`

### `hello.echo` — Output "Hello, World!"

13 characters, 2309 instructions.  Each character uses the
`> +×N ?` pattern on its own cell.

Output: `Hello, World!`

### `cat_byte.echo` — Echo one byte of input

The shortest useful program: `??`

```
UNDO: right half = "?" (R→L)
      '?' (UNDO = read) → mem[0] = input byte

DO:   left half = "?" (L→R)
      '?' (DO = output) → output mem[0]
```

```bash
echo -n "Z" | python3 echo.py examples/cat_byte.echo
# Output: Z
```

Only one byte can be read because there is no loop.

---

## Usage

```bash
# Run a file
python3 echo.py program.echo

# Run inline code
python3 echo.py -e "??"

# Provide input via -i
python3 echo.py -e "??" -i "X"

# Pipe input
echo -n "data" | python3 echo.py program.echo

# Debug trace (prints every step to stderr)
python3 echo.py -d examples/A.echo
```

### Command-line options

| Flag | Description |
|------|-------------|
| `file` | EchoLang source file |
| `-e, --exec CODE` | Run CODE directly instead of a file |
| `-i, --input STR` | Input string for UNDO-phase `?` reads |
| `-d, --debug` | Print full execution trace to stderr |

---

## Why This Language Is Infuriating (and Fun)

1. **Everything cancels by default.**  Without pointer gymnastics, your
   program is an elaborate no-op.

2. **The pointer resets between phases.**  You cannot carry pointer state
   from UNDO into DO.  Each phase must independently navigate to where it
   needs to be.

3. **`>` moves in opposite directions per phase.**  The same `>` that takes
   you to cell 1 in DO takes you to cell 29999 in UNDO.  This is the
   entire trick — and the entire headache.

4. **Only one safe slot.**  The centre character is the only instruction
   that executes once.  Everything else is a do-undo pair.

5. **No loops, no conditionals, no multiplication.**  Three instructions,
   all linear.  Every output byte must be hand-built with repeated `+`.

6. **Input happens before output.**  All `?` reads occur in UNDO (phase 1);
   all `?` writes occur in DO (phase 2).  Input can influence output, but
   only if you route the value to the right cell through the phase barrier.

7. **The palindrome constraint is structural, not cosmetic.**  You cannot
   append a mirror of your code as dead weight — the mirror *runs*.  Every
   character you write in the left half forces an identical character in the
   right half that will actively try to undo your work.

---

## Language Specification Summary

| Property | Value |
|----------|-------|
| Instructions | `+`, `>`, `?` |
| Program constraint | Must be a palindrome (after comment stripping) |
| Memory | 30,000 × 8-bit cells, initialised to 0 |
| Pointer | Starts at 0 each phase, wraps modulo 30,000 |
| Execution | Phase 1 UNDO (right half R→L, inverse ops) → Phase 2 DO (left half L→R, normal ops) |
| Centre char | Executed in DO only (odd-length programs) |
| Input | Read during UNDO-phase `?`; EOF = 0 |
| Output | Written during DO-phase `?` as ASCII |
| Comments | Any character not in `+>?` |

---

## Files

```
echolang/
├── echo.py              # The interpreter
├── README.md            # This document
└── examples/
    ├── A.echo           # Outputs 'A' (133 chars)
    ├── Hi.echo          # Outputs 'Hi' (361 chars)
    ├── hello.echo       # Outputs 'Hello, World!' (2309 chars)
    └── cat_byte.echo    # Echoes one input byte (2 chars)
```

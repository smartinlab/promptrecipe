"""Refuse an interpreter too old to import promptrecipe, with a usable message.

promptfoo spawns Python by name, so it runs whatever `python3` resolves to on
PATH — on macOS that is the system 3.9, well under this project's 3.11 floor.
Without this check the failure surfaces as
`TypeError: dataclass() got an unexpected keyword argument 'slots'`, six times,
which names neither the cause nor the fix.

Kept syntactically 3.9-compatible on purpose: a guard that cannot be parsed by
the interpreter it is guarding against does nothing.
"""

import sys

MINIMUM = (3, 11)


def require() -> None:
    if sys.version_info >= MINIMUM:
        return
    running = ".".join(str(n) for n in sys.version_info[:3])
    wanted = ".".join(str(n) for n in MINIMUM)
    raise RuntimeError(
        f"promptfoo is running Python {running} ({sys.executable}), but promptrecipe "
        f"needs >= {wanted}.\n"
        "promptfoo spawns `python3` from PATH, which is not this project's venv.\n"
        "Fix it with either:\n"
        "  ./run_eval.sh                                  (picks the repo venv)\n"
        "  PROMPTFOO_PYTHON=/path/to/.venv/bin/python npx promptfoo eval"
    )

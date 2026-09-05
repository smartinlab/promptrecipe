"""promptrecipe — compose prompts from path-addressed fragments.

Invariants enforced throughout this package:
- All I/O is confined to the `custody` subpackage. Everything else is pure.
- Fragment content is never evaluated. It is inert text.
- Assembly is deterministic: identical inputs yield byte-identical output.
- `eval`, `exec`, `compile`, and `__import__` never appear in this package.
"""

__version__ = "0.1.0"

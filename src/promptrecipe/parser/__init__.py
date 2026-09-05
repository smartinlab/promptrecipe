"""Recipe parsing.

The grammar is a CLOSED LIST and is the package's security boundary
(ADR-003). It contains no function call, no loop, and no I/O production, so
evaluation is total by construction. Adding a production here is a security
decision, not a convenience — it must be justified against E1-E7.
"""

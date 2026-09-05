"""Adapters to external tooling.

Deliberately thin and OPTIONAL. Gate 0 found both integration targets
changed ownership within eight months, so the core must survive either
disappearing: nothing in `promptrecipe` outside this subpackage imports them,
and importing the core never imports these.
"""

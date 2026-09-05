import inspect

from promptrecipe.errors import Position
from promptrecipe.parser import nodes
from promptrecipe.parser.nodes import (
    And,
    Equals,
    Expect,
    In,
    Literal,
    Load,
    Order,
    PathLiteral,
    PathVar,
    Recipe,
    Text,
    Var,
)

POS = Position(line=1, column=1)


def test_a_recipe_holds_prose_and_directives():
    r = Recipe([Text("You are helpful.\n"), Load(PathLiteral("core/tone"), POS)])
    assert len(r.statements) == 2


def test_expectations_are_reachable_before_assembly():
    r = Recipe([Expect(Var("language", POS), POS), Text("prose")])
    assert len(r.expectations) == 1


def test_declared_order_is_readable():
    r = Recipe([Order(["role", "tone", "rules"], POS)])
    assert r.declared_order == ["role", "tone", "rules"]


def test_an_address_variable_names_a_path_not_text():
    """Amendment 9: an address variable resolves to a fragment path."""
    assert isinstance(Load(PathVar("tone_fragment", POS), POS).path, PathVar)


def test_membership_and_boolean_expressions_compose():
    expr = And(
        In(Var("language", POS), [Literal("pt"), Literal("en")]),
        Equals(Var("model", POS), Literal("claude")),
    )
    assert isinstance(expr, And)


def test_the_grammar_contains_no_dangerous_production():
    """THE structural guard on ADR-003.

    If no node type can express a call, loop, or I/O, no recipe can contain
    one — and evaluation is total by construction rather than by sandbox.
    """
    forbidden = {"Call", "Invoke", "Apply", "Loop", "While", "For", "Exec", "Eval", "Import"}
    defined = {
        name
        for name, obj in inspect.getmembers(nodes, inspect.isclass)
        if obj.__module__ == nodes.__name__
    }
    assert not (defined & forbidden), f"dangerous grammar production added: {defined & forbidden}"

"""An untaken condition swallows the rest of its line.

Found by assembling a realistic multi-line library, not by a unit fixture:
recipes in tests were single-line, so nobody saw that `[if x][load y]` on its
own line still emitted the trailing newline. Three unmet conditions produced
three stray blank lines in the finished prompt.

The rule is narrow on purpose — only whitespace up to and including the FIRST
newline, and only directly after an untaken condition.
"""

from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.resolve import Resolver

LIB = {"core/a": "A", "core/b": "B", "core/c": "C"}


def run(recipe: str, **controls):
    r = Resolver().register("core", "mem", MemoryCustody({**LIB, "core/r": recipe}))
    return get_prompt("core/r", Params(controls=controls), r).text


RECIPE = "[load core/a]\n[if want_b][load core/b]\n[load core/c]\n"


def test_an_untaken_condition_leaves_no_blank_line():
    assert run(RECIPE, want_b=False) == "A\nC\n"


def test_a_taken_condition_keeps_its_line():
    assert run(RECIPE, want_b=True) == "A\nB\nC\n"


def test_several_untaken_conditions_leave_no_gap():
    recipe = (
        "[load core/a]\n"
        "[if x][load core/b]\n"
        "[if y][load core/b]\n"
        "[if z][load core/b]\n"
        "[load core/c]\n"
    )
    assert run(recipe, x=False, y=False, z=False) == "A\nC\n"


def test_blank_lines_the_author_wrote_are_untouched():
    """Only the untaken condition's own line is suppressed — deliberate
    spacing between other statements survives."""
    recipe = "[load core/a]\n\n[load core/c]\n"
    assert run(recipe) == "A\n\nC\n"


def test_real_content_after_an_untaken_condition_survives():
    """Suppression stops at the first thing that is not whitespace."""
    recipe = "[if x][load core/b] kept\n[load core/c]\n"
    assert run(recipe, x=False) == " kept\nC\n"


def test_suppression_does_not_cross_into_the_next_line():
    recipe = "[if x][load core/b]\n\n[load core/c]\n"
    # The condition's own newline goes; the author's blank line stays.
    assert run(recipe, x=False) == "\nC\n"


def test_the_last_statement_being_an_untaken_condition_is_fine():
    assert run("[load core/a]\n[if x][load core/b]", x=False) == "A\n"


def test_whitespace_suppression_does_not_change_the_fragment_set():
    """Cosmetic only: which fragments loaded is unaffected."""
    with_gap = run(RECIPE, want_b=False)
    assert "B" not in with_gap

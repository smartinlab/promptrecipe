"""T-012 — a fragment may reference another fragment.

This is where P3 comes under real pressure. Inclusion means the assembler now
reads INSIDE fragment text, so the guarantee has to be stated more precisely
than "fragment content is never touched":

  A fragment may name a sibling with a fixed `[load path]` reference.
  Nothing else in fragment text is interpreted — no conditions, no order,
  no expectations, no variable paths, no re-parsing of substituted values.

Recognising one fixed reference form is not evaluating the fragment: there is
no expression to evaluate and no branch to take. The tests below hold that
line by trying to cross it.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import MAX_INCLUSION_DEPTH, Params
from promptrecipe.errors import (
    CyclicInclusion,
    DepthLimitExceeded,
    FragmentDirectiveNotAllowed,
    FragmentNotFound,
)
from promptrecipe.resolve import Resolver


def run(entries: dict[str, str], params: Params | None = None):
    return get_prompt(
        "core/r", params or Params(), Resolver().register("core", "mem", MemoryCustody(entries))
    )


# --- inclusion works -------------------------------------------------------


def test_a_fragment_can_reference_another_fragment():
    out = run(
        {
            "core/r": "[load core/outer]",
            "core/outer": "OUTER<[load core/inner]>",
            "core/inner": "INNER",
        }
    )
    assert out.text == "OUTER<INNER>"


def test_inclusion_nests_several_levels_deep():
    out = run(
        {
            "core/r": "[load core/a]",
            "core/a": "a[load core/b]",
            "core/b": "b[load core/c]",
            "core/c": "c",
        }
    )
    assert out.text == "abc"


def test_a_fragment_can_reference_the_same_sibling_twice():
    out = run(
        {
            "core/r": "[load core/pair]",
            "core/pair": "[load core/x]-[load core/x]",
            "core/x": "X",
        }
    )
    assert out.text == "X-X"


def test_nested_fragments_appear_in_provenance():
    """A dependency that reached the output must be named, whether or not the
    recipe mentioned it directly (SD13, FR-002)."""
    out = run(
        {
            "core/r": "[load core/outer]",
            "core/outer": "[load core/inner]",
            "core/inner": "I",
        }
    )
    paths = [p for p, _ in out.fragments]
    assert paths == ["core/outer", "core/inner"]
    assert len(out.attestation.resolved_dependencies) == 2


def test_a_missing_nested_fragment_fails_naming_it():
    with pytest.raises(FragmentNotFound) as exc:
        run({"core/r": "[load core/a]", "core/a": "[load core/absent]"})
    assert "core/absent" in str(exc.value)


# --- cycles ---------------------------------------------------------------


def test_a_self_reference_reports_the_cycle():
    with pytest.raises(CyclicInclusion) as exc:
        run({"core/r": "[load core/a]", "core/a": "[load core/a]"})
    assert "core/a -> core/a" in str(exc.value)


def test_a_multi_node_cycle_reports_the_actual_path():
    """The quality bar Gate 0 set: report `a -> b -> c -> a`, not merely that
    a cycle exists. The anti-pattern it named — silently dropping the cycle
    and continuing — would be far worse here."""
    with pytest.raises(CyclicInclusion) as exc:
        run(
            {
                "core/r": "[load core/a]",
                "core/a": "[load core/b]",
                "core/b": "[load core/c]",
                "core/c": "[load core/a]",
            }
        )
    assert "core/a -> core/b -> core/c -> core/a" in str(exc.value)


def test_a_cycle_emits_no_partial_output():
    """P4 still holds through the new code path."""
    with pytest.raises(CyclicInclusion):
        run(
            {
                "core/r": "PROSE[load core/a]MORE",
                "core/a": "A[load core/a]",
            }
        )


def test_a_diamond_is_not_a_cycle():
    """Two paths to the same fragment are fine — only a path back to a node
    already on the current stack is a cycle."""
    out = run(
        {
            "core/r": "[load core/top]",
            "core/top": "[load core/left][load core/right]",
            "core/left": "L[load core/shared]",
            "core/right": "R[load core/shared]",
            "core/shared": "S",
        }
    )
    assert out.text == "LSRS"


def test_an_absurdly_deep_chain_fails_with_a_limit_not_a_stack_overflow():
    entries = {"core/r": "[load core/f0]"}
    for i in range(MAX_INCLUSION_DEPTH + 5):
        entries[f"core/f{i}"] = f"[load core/f{i + 1}]"
    entries[f"core/f{MAX_INCLUSION_DEPTH + 5}"] = "END"

    with pytest.raises(DepthLimitExceeded):
        run(entries)


# --- P3: the line inclusion must not cross -------------------------------


def test_a_condition_inside_fragment_text_is_rejected():
    """A fragment may name a sibling. It may NOT branch.

    Leaving this literal was the first design and it was wrong: the inner
    load would still fire, so the text would LOOK conditional while loading
    unconditionally. Rejecting is the only reading that is not silently wrong.
    """
    with pytest.raises(FragmentDirectiveNotAllowed) as exc:
        run(
            {
                "core/r": "[load core/a]",
                "core/a": '[if model == "x"] [load core/secret]',
                "core/secret": "LEAKED",
            }
        )
    assert "core/a" in str(exc.value)
    assert "if" in str(exc.value)


def test_an_order_directive_inside_fragment_text_never_reorders_anything():
    """The fragment holds no reference, so it can fire nothing and the text is
    left literal. What matters is that it does NOT reorder the assembly."""
    out = run(
        {
            "core/r": "[load core/a][load core/b]",
            "core/a": "A[order: b, a]",
            "core/b": "B",
        }
    )
    assert out.text == "A[order: b, a]B", "fragment text must not reorder the assembly"


def test_an_expectation_inside_fragment_text_never_fails_an_assembly():
    out = run({"core/r": "[load core/a]", "core/a": "[expect never] kept"})
    assert out.text == "[expect never] kept"


def test_ordinary_bracketed_prose_is_untouched():
    """Only the four directive keywords are directives. Brackets are common
    in prompt text and must stay usable."""
    out = run(
        {
            "core/r": "[load core/a]",
            "core/a": "See [1] and [TODO] and [appendix B].",
        }
    )
    assert out.text == "See [1] and [TODO] and [appendix B]."


def test_a_variable_path_inside_fragment_text_is_not_resolved():
    """A reference must be QUALIFIED. A bare identifier is not one, so it
    stays literal — honouring it would let untrusted fragment content read
    from the caller's address space."""
    out = run(
        {"core/r": "[load core/a]", "core/a": "[load secret_slot]", "core/x": "X"},
        Params(addresses={"secret_slot": "core/x"}),
    )
    assert out.text == "[load secret_slot]"
    assert "X" not in out.text, "the caller's address space must stay unreachable"


def test_a_directive_shaped_bracket_is_rejected_once_the_fragment_can_load():
    """The narrowed rule's other half: the same text IS refused when the
    fragment holds a real reference, because then the load would fire while
    the text reads as conditional."""
    with pytest.raises(FragmentDirectiveNotAllowed):
        run(
            {
                "core/r": "[load core/a]",
                "core/a": "[order: x]\n[load core/b]",
                "core/b": "B",
            }
        )


def test_a_substituted_value_is_never_scanned_for_references():
    """ADR-006 survives inclusion: substitution still runs last, over the
    already-expanded text, and its output is never re-read."""
    out = run(
        {"core/r": "[load core/a]", "core/a": "{{payload}}", "core/hidden": "HIDDEN"},
        Params(values={"payload": "[load core/hidden]"}),
    )
    assert out.text == "[load core/hidden]"
    assert "HIDDEN" not in out.text
    assert [p for p, _ in out.fragments] == ["core/a"]

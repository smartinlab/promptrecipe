"""T-019 / FR-004 — where each fragment landed in the output.

The attestation names the fragments that took part. The span map says WHERE
each one is. The difference matters when a prompt misbehaves: you want the
file to open, not a list of eleven candidates.
"""

import pytest
from conftest import MemoryCustody
from hypothesis import given
from hypothesis import strategies as st

from promptrecipe import Params, get_prompt
from promptrecipe.errors import UnencodableValue
from promptrecipe.resolve import Resolver

LIB = {
    "core/recipe": "HEAD\n[load core/role]\nTAIL",
    "core/role": "ROLE({{who}})\n[load core/tone]",
    "core/tone": "TONE",
    "core/twice": "[load core/tone]-[load core/tone]",
}


def library():
    return Resolver().register("core", "mem", MemoryCustody(LIB))


def assembled(path="core/recipe", **values):
    return get_prompt(path, Params(values=values), library())


def test_every_character_is_attributed():
    """A partition, not a set of highlights. An unclaimed offset would be
    output nobody can account for — the situation this map exists to prevent."""
    result = assembled()
    assert result.spans.covers(result.text)


def test_a_span_points_at_the_fragment_that_contains_the_text():
    result = assembled()
    offset = result.text.index("TONE")
    assert result.spans.source_of(offset).path == "core/tone"


def test_the_innermost_fragment_wins():
    """core/tone sits INSIDE core/role's expansion. Attributing that text to
    core/role would send you to the wrong file."""
    result = assembled()
    role_text = "".join(s.slice(result.text) for s in result.spans.spans_for("core/role"))
    assert "TONE" not in role_text
    assert "ROLE(" in role_text


def test_recipe_prose_is_attributed_to_no_fragment():
    """The honest answer, and a useful one: it says open the recipe rather
    than hunt for a fragment that does not exist."""
    result = assembled()
    span = result.spans.source_of(result.text.index("HEAD"))
    assert span.from_recipe
    assert span.path == ""


def test_a_fragment_loaded_twice_lands_twice():
    result = assembled("core/twice")
    assert len(result.spans.spans_for("core/tone")) == 2


def test_a_span_carries_the_fragment_identity():
    """The path says which file; the identity says which CONTENT. A span map
    that only carried the path would go stale the moment the file changed."""
    result = assembled()
    span = result.spans.source_of(result.text.index("TONE"))
    expected = next(fid.hex for path, fid in result.fragments if path == "core/tone")
    assert span.identity == expected


# --- the reason this is hard ---------------------------------------------


def test_offsets_survive_value_substitution():
    """Substitution runs LAST (ADR-006) and changes the text's length, so
    every offset collected during assembly is stale by the time assembly
    finishes. This is the whole difficulty of FR-004."""
    result = assembled(who="a-very-much-longer-name-than-the-placeholder")

    offset = result.text.index("TONE")
    assert result.spans.source_of(offset).path == "core/tone"
    assert result.spans.covers(result.text)


def test_a_substituted_value_is_attributed_to_the_fragment_that_asked_for_it():
    result = assembled(who="Aria")
    assert result.spans.source_of(result.text.index("Aria")).path == "core/role"


def test_a_shorter_substitution_shifts_offsets_backwards():
    """The remap has to handle both directions — a value shorter than its
    placeholder moves everything after it LEFT."""
    result = assembled(who="")
    assert result.spans.covers(result.text)
    assert result.spans.source_of(result.text.index("TAIL")).from_recipe


def test_an_unbound_placeholder_shifts_nothing():
    result = assembled()
    assert "{{who}}" in result.text
    assert result.spans.source_of(result.text.index("{{who}}")).path == "core/role"


def test_the_annotated_view_names_every_origin():
    result = assembled(who="Aria")
    annotated = result.spans.annotate(result.text)
    assert "core/tone" in annotated
    assert "(recipe)" in annotated


def test_adjacent_text_from_one_fragment_reads_as_one_span():
    """Expansion splits a fragment at every reference it makes. Once the
    children are attributed to themselves, the parent's remaining pieces are
    continuous again and should not read as fragments of a fragment."""
    result = assembled()
    tone = result.spans.spans_for("core/tone")
    assert len(tone) == 1


# --- the partition invariant, over generated substitutions ----------------


TEXT = st.text(
    alphabet=st.characters(blacklist_characters="{}[]", blacklist_categories=("Cs",)),
    max_size=40,
)


@given(TEXT, TEXT)
def test_the_map_stays_a_partition_whatever_the_values(who: str, unused: str) -> None:
    """Substitution length is caller-controlled, so the remap must hold for
    values of any length — including empty and much-longer-than-placeholder."""
    result = assembled(who=who, unused=unused)
    assert result.spans.covers(result.text)
    for earlier, later in zip(result.spans.spans, result.spans.spans[1:], strict=False):
        assert earlier.end == later.start


def test_a_value_that_is_not_encodable_text_fails_before_anything_is_produced():
    """A lone surrogate is a `str` with no UTF-8 encoding. It used to escape
    as a bare UnicodeEncodeError from the middle of assembly — outside the
    documented error contract, and after work was done. Found by the property
    test above, which generated one."""
    with pytest.raises(UnencodableValue):
        assembled(who="\ud800")

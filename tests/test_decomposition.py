"""T-016 — decompose an existing prompt without changing what it produces.

The adoption path (FR-035): extract one fragment, verify nothing changed,
repeat. Byte-identity is unforgiving because prompt text is full of
significant whitespace — which is exactly why the check must be mechanical
rather than eyeballed.
"""

from conftest import MemoryCustody

from promptrecipe import DecompositionResult, Params, Resolver, verify_decomposition

ORIGINAL = (
    "You are a technical support assistant for Acme Cloud.\n"
    "\n"
    "Be concise. Lead with the answer.\n"
    "Never invent product features that do not exist.\n"
)


def resolver(entries):
    return Resolver().register("core", "mem", MemoryCustody(entries))


def test_a_fully_decomposed_prompt_reassembles_byte_identically():
    r = resolver(
        {
            "core/r": "[load core/role]\n[load core/tone]\n[load core/safety]\n",
            "core/role": "You are a technical support assistant for Acme Cloud.\n",
            "core/tone": "Be concise. Lead with the answer.",
            "core/safety": "Never invent product features that do not exist.",
        }
    )
    result = verify_decomposition(ORIGINAL, "core/r", Params(), r)
    assert result.identical, str(result)


def test_a_partially_decomposed_prompt_is_valid():
    """Extraction is incremental: one fragment out, the rest still inline."""
    r = resolver(
        {
            "core/r": (
                "[load core/role]\n"
                "\n"
                "Be concise. Lead with the answer.\n"
                "Never invent product features that do not exist.\n"
            ),
            "core/role": "You are a technical support assistant for Acme Cloud.",
        }
    )
    assert verify_decomposition(ORIGINAL, "core/r", Params(), r).identical


def test_a_single_missing_newline_is_reported_with_its_position():
    """The failure mode this exists to catch: whitespace drift that a human
    reading the two side by side would miss."""
    r = resolver(
        {
            "core/r": "[load core/role][load core/rest]",
            "core/role": "You are a technical support assistant for Acme Cloud.\n",
            # The blank line is gone.
            "core/rest": "Be concise. Lead with the answer.\n"
            "Never invent product features that do not exist.\n",
        }
    )
    result = verify_decomposition(ORIGINAL, "core/r", Params(), r)

    assert not result.identical
    assert result.first_difference == len("You are a technical support assistant for Acme Cloud.\n")
    assert "differs at character" in str(result)


def test_values_are_substituted_before_comparison():
    """A decomposition that parameterises a literal must still match."""
    r = resolver(
        {
            "core/r": "[load core/role]\n\n[load core/tone]\n[load core/safety]\n",
            "core/role": "You are a technical support assistant for {{product}}.",
            "core/tone": "Be concise. Lead with the answer.",
            "core/safety": "Never invent product features that do not exist.",
        }
    )
    result = verify_decomposition(ORIGINAL, "core/r", Params(values={"product": "Acme Cloud"}), r)
    assert result.identical, str(result)


def test_a_length_difference_is_reported_even_at_the_very_end():
    r = resolver({"core/r": "[load core/a]", "core/a": "short"})
    result = verify_decomposition("short and then more", "core/r", Params(), r)
    assert not result.identical
    assert result.original_length > result.assembled_length


def test_the_result_reads_clearly_when_identical():
    r = resolver({"core/r": "[load core/a]", "core/a": "same"})
    result = verify_decomposition("same", "core/r", Params(), r)
    assert isinstance(result, DecompositionResult)
    assert str(result) == "identical (4 characters)"

"""Markdown survives in fragments, and bracketed prose is not a directive.

Fragment content is inert text: nothing markdown-specific is parsed, and the
`.md` extension is only a default (any extension works — editors and diffs
just read it better).

The subtlety is that markdown uses square brackets and so do directives. The
rule: directive-shaped prose is only dangerous in a fragment that can
ACTUALLY LOAD something. Without a reference, nothing can fire regardless of
what the text looks like, so the brackets are left alone.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import Params, Resolver, get_prompt
from promptrecipe.errors import FragmentDirectiveNotAllowed

MARKDOWN = [
    ("heading", "# Title\n## Subtitle"),
    ("emphasis", "**strong** and *emphasis* and `code`"),
    ("bullet list", "- one\n- two\n  - nested"),
    ("numbered list", "1. first\n2. second"),
    ("fenced code", "```python\nx = 1\n```"),
    ("blockquote", "> quoted"),
    ("table", "| a | b |\n|---|---|\n| 1 | 2 |"),
    ("horizontal rule", "---"),
    ("link", "see [the docs](https://example.com)"),
    ("image", "![alt](img.png)"),
    ("task list", "- [ ] pending\n- [x] done"),
]


def assemble(fragment: str, extra: dict | None = None) -> str:
    library = {"core/r": "[load core/f]", "core/f": fragment, **(extra or {})}
    resolver = Resolver().register("core", "mem", MemoryCustody(library))
    return get_prompt("core/r", Params(), resolver).text


@pytest.mark.parametrize(("label", "source"), MARKDOWN, ids=[m[0] for m in MARKDOWN])
def test_markdown_passes_through_verbatim(label, source):
    assert assemble(source) == source


def test_nothing_markdown_specific_is_parsed():
    """The extension is a convention. No renderer runs, no syntax is
    validated, and malformed markdown is simply text."""
    broken = "**unclosed emphasis and [an unclosed link("
    assert assemble(broken) == broken


# --- brackets: prose vs directive ------------------------------------------

PROSE_WITH_BRACKETS = [
    ("footnote marker", "see [1] below"),
    ("todo marker", "[TODO] revisit this"),
    ("markdown link starting with a keyword", "use the [load balancer](https://x.com)"),
    ("conditional-sounding prose", "[if necessary] escalate to a human"),
    ("order-sounding prose", "see [order details] below"),
    ("expect-sounding prose", "[expected behaviour] is documented"),
]


@pytest.mark.parametrize(
    ("label", "source"), PROSE_WITH_BRACKETS, ids=[p[0] for p in PROSE_WITH_BRACKETS]
)
def test_bracketed_prose_survives_when_the_fragment_loads_nothing(label, source):
    """A fragment with no reference cannot fire anything, whatever its text
    looks like. Rejecting these would be a false positive on writing people
    legitimately want — `[load balancer](url)` is a plausible markdown link."""
    assert assemble(source) == source


def test_the_dangerous_case_is_still_rejected():
    """A condition-shaped bracket in a fragment that CAN load is refused:
    the load would fire unconditionally while reading as conditional."""
    with pytest.raises(FragmentDirectiveNotAllowed):
        assemble("[if x] some text\n[load core/y]", {"core/y": "Y"})


def test_a_markdown_link_alongside_a_real_reference_is_also_refused():
    """The remaining false positive, kept deliberately and documented: once a
    fragment references a sibling, every directive-shaped bracket in it is
    treated as suspect. Narrowing further would require guessing intent."""
    with pytest.raises(FragmentDirectiveNotAllowed):
        assemble("see the [load balancer](https://x.com)\n[load core/y]", {"core/y": "Y"})


def test_the_error_explains_both_halves_of_the_rule():
    with pytest.raises(FragmentDirectiveNotAllowed) as exc:
        assemble("[if x]\n[load core/y]", {"core/y": "Y"})
    message = str(exc.value)
    assert "also references another fragment" in message
    assert "ordinary prose" in message


def test_a_value_placeholder_inside_markdown_is_still_substituted():
    """Values are content: they fill in wherever they appear, including
    inside markdown structure."""
    library = {"core/r": "[load core/f]", "core/f": "| product | {{product}} |"}
    resolver = Resolver().register("core", "mem", MemoryCustody(library))
    out = get_prompt("core/r", Params(values={"product": "Acme"}), resolver)
    assert out.text == "| product | Acme |"

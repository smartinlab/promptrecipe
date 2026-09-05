import pytest

from promptrecipe.custody import FragmentContent
from promptrecipe.custody.fs import FsCustody
from promptrecipe.errors import FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@pytest.fixture
def custody(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "tone.md").write_text("Be concise and direct.")
    (core / "safety.md").write_text("Refuse harmful requests.")
    return FsCustody().with_namespace("core", core)


def test_reads_a_fragment_and_returns_its_identity(custody):
    content = custody.read(FragmentPath.parse("core/tone"))
    assert content.text == "Be concise and direct."
    assert content.id == FragmentId.of(b"Be concise and direct.")


def test_missing_fragment_names_the_path_and_namespaces(custody):
    with pytest.raises(FragmentNotFound) as exc:
        custody.read(FragmentPath.parse("core/absent"))
    assert "core/absent" in str(exc.value)


def test_unknown_namespace_lists_the_known_ones(custody):
    with pytest.raises(UnknownNamespace) as exc:
        custody.read(FragmentPath.parse("nope/tone"))
    assert "core" in str(exc.value)


def test_list_is_sorted_and_not_filesystem_ordered(custody):
    """TRD §4: filesystem enumeration order must never leak into output."""
    assert [str(p) for p in custody.list("core")] == ["core/safety", "core/tone"]


def test_exists_reports_presence_without_reading(custody):
    assert custody.exists(FragmentPath.parse("core/tone"))
    assert not custody.exists(FragmentPath.parse("core/absent"))


def test_identical_content_at_two_paths_yields_one_identity(tmp_path):
    """SD1: identity is content, not location."""
    core = tmp_path / "core"
    core.mkdir()
    (core / "a.md").write_text("shared rule")
    (core / "b.md").write_text("shared rule")
    custody = FsCustody().with_namespace("core", core)
    assert (
        custody.read(FragmentPath.parse("core/a")).id
        == custody.read(FragmentPath.parse("core/b")).id
    )


def test_fragment_content_text_is_never_parsed():
    """ADR-003: content is inert. Directive-shaped text stays text."""
    content = FragmentContent.of(b"[load core/evil] {{injected}}")
    assert content.text == "[load core/evil] {{injected}}"

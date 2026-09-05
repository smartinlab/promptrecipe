import pytest

from promptrecipe.errors import PathEscapesNamespace, PromptRecipeError
from promptrecipe.paths import FragmentPath


def test_splits_namespace_from_segments():
    p = FragmentPath.parse("core/tone/formal")
    assert p.namespace == "core"
    assert p.segments == ("tone", "formal")
    assert str(p) == "core/tone/formal"


def test_canonicalization_is_idempotent():
    """Determinism (TRD §4): canonicalizing a canonical form returns itself."""
    once = FragmentPath.parse("core//tone/./formal")
    assert FragmentPath.parse(str(once)) == once
    assert str(once) == "core/tone/formal"


def test_dot_dot_resolves_lexically_within_the_namespace():
    assert str(FragmentPath.parse("core/tone/../safety")) == "core/safety"


def test_escaping_the_namespace_root_is_rejected():
    with pytest.raises(PathEscapesNamespace):
        FragmentPath.parse("core/../../etc/passwd")


def test_leading_slashes_are_stripped_not_treated_as_absolute():
    assert str(FragmentPath.parse("/core/tone")) == "core/tone"


def test_empty_path_is_rejected():
    with pytest.raises(PromptRecipeError):
        FragmentPath.parse("   ")


def test_a_namespace_alone_is_a_valid_path():
    p = FragmentPath.parse("core")
    assert p.namespace == "core"
    assert p.segments == ()


def test_paths_are_hashable_and_sortable():
    a = FragmentPath.parse("core/a")
    b = FragmentPath.parse("core/b")
    assert sorted([b, a]) == [a, b]
    assert len({a, FragmentPath.parse("core/a")}) == 1


def test_canonicalization_never_touches_the_filesystem(monkeypatch):
    """ADR-001: only the custody layer performs I/O."""
    import os

    def explode(*args, **kwargs):
        raise AssertionError("path parsing must not touch the filesystem")

    monkeypatch.setattr(os.path, "realpath", explode)
    monkeypatch.setattr(os.path, "exists", explode)
    assert str(FragmentPath.parse("core/does/not/exist")) == "core/does/not/exist"

from promptrecipe.errors import (
    AmbiguousReference,
    CyclicInclusion,
    ExpectationFailed,
    FragmentNotFound,
    IdentityMismatch,
    Position,
    PromptRecipeError,
)


def test_not_found_names_the_path_and_where_it_looked():
    err = FragmentNotFound(path="core/tone", namespaces=["core", "shared"])
    msg = str(err)
    assert "core/tone" in msg
    assert "core" in msg and "shared" in msg


def test_ambiguity_names_every_candidate_and_refuses_to_pick():
    err = AmbiguousReference(path="tone", candidates=["core/tone", "shared/tone"])
    msg = str(err)
    assert "core/tone" in msg
    assert "shared/tone" in msg
    assert "never picks silently" in msg


def test_expectation_failure_names_expected_and_actual():
    err = ExpectationFailed(
        position=Position(line=3, column=5),
        expected="language in ['pt', 'en']",
        actual="language was 'fr'",
    )
    msg = str(err)
    assert "line 3, column 5" in msg
    assert "language in ['pt', 'en']" in msg
    assert "'fr'" in msg


def test_cycle_reports_the_whole_path_not_just_its_existence():
    assert "a -> b -> c -> a" in str(CyclicInclusion(cycle=["a", "b", "c", "a"]))


def test_identity_mismatch_refuses_substitution():
    err = IdentityMismatch(path="core/tone", expected="abc123", found="def456")
    assert "refusing to substitute" in str(err)


def test_every_error_is_catchable_as_one_base_type():
    for err in [
        FragmentNotFound(path="p", namespaces=[]),
        AmbiguousReference(path="p", candidates=[]),
        CyclicInclusion(cycle=["a", "a"]),
    ]:
        assert isinstance(err, PromptRecipeError)


def test_errors_are_raisable():
    """Dataclass __init__ overrides Exception.__init__; raising must still work."""
    try:
        raise FragmentNotFound(path="core/x", namespaces=["core"])
    except PromptRecipeError as exc:
        assert "core/x" in str(exc)

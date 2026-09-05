from promptrecipe.identity import FragmentId


def test_identical_bytes_yield_identical_identity():
    assert FragmentId.of(b"you are a helpful assistant") == FragmentId.of(
        b"you are a helpful assistant"
    )


def test_one_changed_byte_changes_the_identity():
    assert FragmentId.of(b"be concise") != FragmentId.of(b"be concise.")


def test_identity_does_not_depend_on_where_content_came_from():
    """The property that lets custody change safely (SD1)."""
    assert FragmentId.of(b"shared safety rule") == FragmentId.of(b"shared safety rule")


def test_hex_is_64_chars_and_short_is_12():
    fid = FragmentId.of(b"anything")
    assert len(fid.hex) == 64
    assert len(fid.short) == 12
    assert fid.hex.startswith(fid.short)


def test_empty_content_still_has_an_identity():
    assert len(FragmentId.of(b"").hex) == 64


def test_identity_is_hashable_and_usable_as_a_dict_key():
    fid = FragmentId.of(b"x")
    assert {fid: "value"}[FragmentId.of(b"x")] == "value"


def test_identity_is_immutable():
    fid = FragmentId.of(b"x")
    try:
        fid.hex = "tampered"  # type: ignore[misc]
    except (AttributeError, TypeError):
        return
    raise AssertionError("FragmentId must be immutable")

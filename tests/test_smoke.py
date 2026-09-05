import promptrecipe


def test_package_imports():
    assert promptrecipe.__version__ == "0.1.0"


def test_the_single_runtime_dependency_resolves():
    """The only runtime dependency. If this breaks, the audit is moot."""
    import blake3

    digest = blake3.blake3(b"promptrecipe").hexdigest()
    assert len(digest) == 64
    # Determinism at the lowest level: same input, same digest.
    assert digest == blake3.blake3(b"promptrecipe").hexdigest()


def test_runtime_dependencies_are_exactly_one():
    """Guards a deliberate property: one runtime dependency.

    A second one is not forbidden forever, but adding it silently is.
    """
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"]
    assert deps == ["blake3==1.0.9"], f"runtime dependencies changed: {deps}"

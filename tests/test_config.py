"""Declaring a library in a file instead of in code.

Registering every namespace by hand was the roughest edge of the API: the
library's shape is a property of the library, not of the program loading it.
"""

import pytest

from promptrecipe import Params, get_prompt, load_config, resolver_from_config
from promptrecipe.config import CONFIG_NAME, ConfigError, find_config


@pytest.fixture
def library(tmp_path):
    for ns in ("core", "policy"):
        (tmp_path / "prompts" / ns).mkdir(parents=True)
    (tmp_path / "prompts" / "core" / "role.md").write_text("ROLE")
    (tmp_path / "prompts" / "core" / "r.md").write_text("[load core/role][load policy/x]")
    (tmp_path / "prompts" / "policy" / "x.md").write_text("POLICY")
    return tmp_path


def write_config(root, body: str):
    path = root / CONFIG_NAME
    path.write_text(body)
    return path


def test_a_declared_library_assembles(library):
    config = write_config(
        library,
        '[namespaces]\ncore = "prompts/core"\npolicy = "prompts/policy"\n',
    )
    resolver = resolver_from_config(config)
    assert get_prompt("core/r", Params(), resolver).text == "ROLEPOLICY"


def test_paths_are_relative_to_the_config_not_the_working_directory(library, monkeypatch):
    """Moving the library moves its configuration with it, and nothing
    depends on where the caller happens to be running from."""
    config = write_config(library, '[namespaces]\ncore = "prompts/core"\n')
    monkeypatch.chdir("/")
    resolver = resolver_from_config(config)
    assert resolver.read.__self__ is resolver  # bound, sanity
    assert get_prompt("core/role", Params(), resolver).text == "ROLE"


def test_the_table_form_carries_precedence_and_extension(library):
    (library / "prompts" / "override").mkdir()
    (library / "prompts" / "override" / "role.txt").write_text("OVERRIDDEN")
    config = write_config(
        library,
        "[namespaces]\n"
        'core = "prompts/core"\n'
        "\n"
        "[namespaces.other]\n"
        'path = "prompts/override"\n'
        "precedence = 10\n"
        'extension = "txt"\n',
    )
    parsed = load_config(config)
    other = next(ns for ns in parsed.namespaces if ns.name == "other")
    assert other.precedence == 10
    assert other.extension == "txt"


def test_a_bad_path_fails_at_load_time_not_at_first_use(library):
    """A typo in a path must not surface later as 'fragment not found'."""
    config = write_config(library, '[namespaces]\ncore = "prompts/typo"\n')
    with pytest.raises(ConfigError) as exc:
        load_config(config)
    assert "not a directory" in str(exc.value)


def test_a_missing_file_says_so(tmp_path):
    with pytest.raises(ConfigError) as exc:
        load_config(tmp_path / "absent.toml")
    assert "does not exist" in str(exc.value)


def test_invalid_toml_names_the_problem(library):
    config = write_config(library, "[namespaces\ncore = broken")
    with pytest.raises(ConfigError) as exc:
        load_config(config)
    assert "invalid TOML" in str(exc.value)


def test_an_empty_namespaces_table_is_rejected(library):
    config = write_config(library, "[namespaces]\n")
    with pytest.raises(ConfigError) as exc:
        load_config(config)
    assert "empty" in str(exc.value)


def test_a_namespace_without_a_path_is_rejected(library):
    config = write_config(library, "[namespaces.core]\nprecedence = 1\n")
    with pytest.raises(ConfigError) as exc:
        load_config(config)
    assert "no 'path'" in str(exc.value)


def test_config_is_discovered_by_walking_up(library):
    """A script deep in a project finds the library at its root without being
    told where it is — the same discovery a build tool does."""
    write_config(library, '[namespaces]\ncore = "prompts/core"\n')
    deep = library / "src" / "app" / "handlers"
    deep.mkdir(parents=True)
    assert find_config(deep) == (library / CONFIG_NAME).resolve()


def test_discovery_failing_says_where_it_looked(tmp_path):
    with pytest.raises(ConfigError) as exc:
        find_config(tmp_path)
    assert CONFIG_NAME in str(exc.value)


def test_namespace_order_is_deterministic(library):
    """Declaration order in the file must not change resolution behaviour."""
    forward = write_config(
        library, '[namespaces]\ncore = "prompts/core"\npolicy = "prompts/policy"\n'
    )
    a = [ns.name for ns in load_config(forward).namespaces]

    backward = write_config(
        library, '[namespaces]\npolicy = "prompts/policy"\ncore = "prompts/core"\n'
    )
    b = [ns.name for ns in load_config(backward).namespaces]

    assert a == b == ["core", "policy"]


def test_the_example_library_ships_a_working_config():
    """The config in the repo must actually load."""
    from pathlib import Path

    config = Path(__file__).resolve().parents[1] / "examples" / "support-agent" / CONFIG_NAME
    resolver = resolver_from_config(config)
    out = get_prompt(
        "core/agent.claude",
        Params(
            controls={"tier": "pro", "language": "en", "tools_enabled": True},
            values={"agent_name": "Aria", "product": "Acme Cloud", "tier": "pro"},
        ),
        resolver,
    )
    assert "Aria" in out.text
    assert len(out.fragments) == 6

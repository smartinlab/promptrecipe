"""The evaluation adapter.

Structure tests run everywhere. The promptfoo end-to-end run is exercised by
`integrations/promptfoo/` and skipped here when the tool is not installed —
the integration is an optional extra and the core must test without it.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe.errors import UndefinedVariable
from promptrecipe.integrations.evaluation import (
    fragment_prompt_function,
    params_from_vars,
    passthrough_provider,
    recipe_prompt_function,
)
from promptrecipe.resolve import Resolver

LIB = {
    "core/r": "[load core/role][if premium][load core/extra]",
    "core/role": "Hello {{name}}",
    "core/extra": " EXTRA",
}


def resolver():
    return Resolver().register("core", "mem", MemoryCustody(LIB))


# --- the three variable roles survive a flat harness dict -------------------


def test_a_flat_var_dict_splits_into_the_three_roles():
    """A harness hands over one flat dict. The prefixes say which role each
    belongs to — the distinction is not cosmetic: controls and addresses
    decide STRUCTURE while values only fill CONTENT."""
    params = params_from_vars({"c_premium": True, "a_tone": "core/tone.claude", "name": "Aria"})
    assert params.controls == {"premium": True}
    assert params.addresses == {"tone": "core/tone.claude"}
    assert params.values == {"name": "Aria"}


def test_an_unprefixed_var_is_a_value_not_a_control():
    """The safe default: an unrecognised variable fills content and cannot
    change which fragments load."""
    params = params_from_vars({"anything": "x"})
    assert params.values == {"anything": "x"}
    assert params.controls == {}


def test_test_data_cannot_change_structure_without_the_control_prefix():
    """A harness that conflated the roles could let test data steer which
    fragments load. The guarantee turns out to be stronger than "the
    condition stays false": an unprefixed variable never becomes a control,
    so the condition has no binding at all and assembly FAILS LOUDLY rather
    than quietly taking the other branch.
    """
    render = recipe_prompt_function("core/r", resolver())

    with pytest.raises(UndefinedVariable):
        render({"vars": {"premium": True, "name": "A"}})

    assert "EXTRA" in render({"vars": {"c_premium": True, "name": "A"}})


def test_an_unbound_control_is_an_error_not_a_false():
    """Treating a missing control as false would make a typo in a variable
    name silently change which fragments load."""
    render = recipe_prompt_function("core/r", resolver())
    with pytest.raises(UndefinedVariable) as exc:
        render({"vars": {"name": "A"}})
    assert "premium" in str(exc.value)


# --- the two evaluable units (SD14) ----------------------------------------


def test_a_recipe_renders_as_a_prompt_function():
    render = recipe_prompt_function("core/r", resolver())
    out = render({"vars": {"c_premium": False, "name": "Aria"}})
    assert out == "Hello Aria"
    assert isinstance(out, str), "a harness expects a plain string"


def test_a_single_fragment_renders_as_its_own_unit():
    """Fragment level catches a bad primitive; recipe level catches bad
    composition. Neither substitutes for the other."""
    render = fragment_prompt_function("core/role", resolver())
    assert render({"vars": {"name": "Aria"}}) == "Hello Aria"


def test_a_prompt_function_tolerates_being_called_without_context():
    """Some harness paths call with no context at all."""
    plain = Resolver().register("core", "mem", MemoryCustody({"core/plain": "no conditions here"}))
    render = recipe_prompt_function("core/plain", plain)
    assert render() == "no conditions here"


# --- the pass-through provider ---------------------------------------------


def test_the_passthrough_provider_returns_the_prompt_unchanged():
    """What makes prompt-content assertions cost zero model execution."""
    assert passthrough_provider("the prompt") == {"output": "the prompt"}


def test_the_library_ships_no_provider_that_calls_a_model():
    """SD10 / FR-027: this library produces prompts and never executes them,
    so the only provider it ships is one that executes nothing."""
    import inspect

    from promptrecipe.integrations import evaluation

    source = inspect.getsource(evaluation)
    for forbidden in ("requests", "httpx", "urllib", "openai", "anthropic"):
        assert forbidden not in source


def test_the_core_does_not_import_the_evaluation_adapter():
    import subprocess
    import sys

    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import promptrecipe, sys; "
            "print('promptrecipe.integrations.evaluation' in sys.modules)",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"


# --- the promptfoo config itself -------------------------------------------


def test_the_promptfoo_config_avoids_the_nunjucks_trap():
    """promptfoo renders ASSERTION VALUES through Nunjucks, so a literal
    '{{' in an assertion is an unterminated expression and the whole eval
    errors before a single assertion runs. Found by running it.
    """
    from pathlib import Path

    config = (
        Path(__file__).resolve().parents[1] / "integrations" / "promptfoo" / "promptfooconfig.yaml"
    )
    text = config.read_text()
    assert 'value: "{{"' not in text, "a bare {{ in an assertion breaks the whole eval"
    assert "not-regex" in text, "the placeholder check must use a regex instead"


@pytest.mark.skipif(not __import__("shutil").which("node"), reason="promptfoo needs Node")
def test_the_prompt_source_module_loads_standalone():
    """The file promptfoo imports must work on its own."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "integrations" / "promptfoo" / "prompt_source.py"
    spec = importlib.util.spec_from_file_location("pf_prompt_source", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    out = module.render_recipe(
        {
            "vars": {
                "c_tier": "free",
                "c_language": "en",
                "c_tools_enabled": False,
                "agent_name": "Aria",
                "product": "Acme Cloud",
                "tier": "free",
            }
        }
    )
    assert "Aria" in out
    assert "{{" not in out

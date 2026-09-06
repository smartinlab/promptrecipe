"""Prompt functions promptfoo loads directly.

Referenced from promptfooconfig.yaml as
`file://prompt_source.py:render_recipe`. promptfoo calls these with a context
dict carrying `vars`; they return a plain string.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
# promptfoo may spawn this from any working directory, so both the sibling
# guard module and the library have to be findable explicitly.
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import _python_floor  # noqa: E402

_python_floor.require()

from promptrecipe.custody.fs import FsCustody  # noqa: E402
from promptrecipe.integrations.evaluation import (  # noqa: E402
    fragment_prompt_function,
    recipe_prompt_function,
)
from promptrecipe.resolve import Resolver  # noqa: E402

PROMPTS = ROOT / "examples" / "support-agent" / "prompts"


def _resolver() -> Resolver:
    return (
        Resolver()
        .register("core", "fs", FsCustody().with_namespace("core", PROMPTS / "core"))
        .register("policy", "fs", FsCustody().with_namespace("policy", PROMPTS / "policy"))
        .register("tools", "fs", FsCustody().with_namespace("tools", PROMPTS / "tools"))
    )


render_recipe = recipe_prompt_function("core/agent.claude", _resolver())
render_recipe_gpt = recipe_prompt_function("core/agent.gpt", _resolver())
render_safety_fragment = fragment_prompt_function("core/safety", _resolver())

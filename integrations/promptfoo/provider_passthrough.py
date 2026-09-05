"""A promptfoo provider that returns the prompt instead of calling a model.

This is what makes prompt-content assertions cost zero model execution
(FR-025), and it is the only provider this library ships: SD10 says
promptrecipe produces prompts and never executes them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from promptrecipe.integrations.evaluation import passthrough_provider  # noqa: E402


def call_api(prompt, options=None, context=None):
    """promptfoo's Python provider contract."""
    return passthrough_provider(prompt)

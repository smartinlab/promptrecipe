# ST-003-04: Recipe parsing end to end

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Prove a realistic recipe parses completely, and that prose stays verbatim inert text.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 56 passed
```

**Files** — Create: `tests/test_recipe_parsing.py`

---

### Step 1 — RED/GREEN: write the integration test (5 min)

The parser already exists, so this suite should pass immediately. If any case fails, the parser has a gap — fix the parser, never the test.

```bash
cat > tests/test_recipe_parsing.py <<'PY'
import pytest

from promptrecipe.errors import ParseError
from promptrecipe.parser.nodes import If, Load, PathVar, Text
from promptrecipe.parser.parse import parse

REALISTIC = """[expect language in ["pt", "en"]]
You are a technical assistant.

[load core/role]
[if model == "claude"] [load core/tone.claude]
[if model == "gpt"] [load core/tone.gpt]
[load core/safety]

[order: role, tone, safety]
"""


def test_a_realistic_recipe_parses_completely():
    assert parse(REALISTIC).statements


def test_expectations_are_reachable_before_any_assembly():
    """TRD §7: expectations run before content, so a violation emits nothing."""
    assert len(parse(REALISTIC).expectations) == 1


def test_the_declared_order_is_read_not_inferred():
    """TRD §4: ordering must never derive from declaration sequence."""
    assert parse(REALISTIC).declared_order == ["role", "tone", "safety"]


def test_prose_is_preserved_verbatim_as_inert_text():
    recipe = parse("Hello [load core/x] world")
    texts = [s.value for s in recipe.statements if isinstance(s, Text)]
    assert texts == ["Hello ", " world"]


def test_text_that_looks_like_a_directive_is_still_just_text():
    """The load-bearing safety case at parse level. Directive-shaped words in
    prose must never become directives (ADR-003)."""
    recipe = parse("The word load and the word if are ordinary words here.")
    assert len(recipe.statements) == 1
    assert isinstance(recipe.statements[0], Text)


def test_conditional_loads_carry_their_condition():
    recipe = parse('[if model == "claude"] [load core/tone.claude]')
    stmt = recipe.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.body, Load)


def test_an_address_variable_load_is_distinguished_from_a_literal_path():
    """Amendment 9: an address variable's value is a path, not text."""
    stmt = parse("[load tone_choice]").statements[0]
    assert isinstance(stmt, Load)
    assert isinstance(stmt.path, PathVar)
    assert stmt.path.name == "tone_choice"


def test_an_unknown_directive_fails_naming_the_valid_ones():
    with pytest.raises(ParseError) as exc:
        parse("[render core/x]")
    msg = str(exc.value)
    assert "load" in msg
    assert "render" in msg
PY

pytest tests/test_recipe_parsing.py
```
Expected: `8 passed`

### Step 2 — Run the whole suite (1 min)

```bash
pytest
```
Expected: all green.

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test(parser): end-to-end recipe parsing

Covers the safety case explicitly: directive-shaped words inside prose
stay prose. Declared order is read, never inferred from declaration
sequence (TRD §4)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_recipe_parsing.py
```

---

## T-003 Definition of Done

- [ ] Lexer emits positioned tokens; prose outside brackets is one inert TEXT token
- [ ] **Grammar is a closed list — two tests enforce it** (no dangerous node type, no dynamic execution)
- [ ] **`grep` confirms `eval`/`exec`/`compile`/`__import__` appear nowhere in the package**
- [ ] Expression precedence correct: `or` < `and` < comparison < primary
- [ ] Every parse error names a position, what was expected, and what was found (E7)
- [ ] Directive-shaped text inside prose stays prose

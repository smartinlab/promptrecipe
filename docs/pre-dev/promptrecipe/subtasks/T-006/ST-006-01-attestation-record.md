# ST-006-01: The attestation record

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Define the record every assembly emits — shaped after supply-chain attestation (subject · resolved dependencies · producer), because that model already solves "bind an output to its exact inputs".

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 100 passed
```

**Files** — Create: `src/promptrecipe/provenance.py`, `tests/test_provenance_record.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_provenance_record.py <<'PY'
import json
from dataclasses import replace

from promptrecipe.provenance import Attestation, Producer, ResolvedDependency


def sample() -> Attestation:
    return Attestation(
        subject="aa" * 32,
        resolved_dependencies=[ResolvedDependency(path="core/tone", identity="bb" * 32)],
        condition_outcomes=[("(model == 'claude')", True)],
        resolved_order=["core/role", "core/tone"],
        address_resolutions=[("tone", "core/tone.claude")],
        value_bindings=[("customer", "Acme")],
        producer=Producer(),
        recorded_at="2026-08-31T12:00:00Z",
        structural_identity="cc" * 32,
        instance_identity="dd" * 32,
    )


def test_an_attestation_round_trips_through_json():
    a = sample()
    assert Attestation.from_json(json.loads(a.to_json())) == a


def test_dependencies_keep_their_assembly_order():
    """SD13: order is part of identity, so this must be a list, not a set."""
    # `replace`, not `**obj.__dict__`: Attestation is a slots dataclass and
    # therefore has no __dict__.
    a = replace(
        sample(),
        resolved_dependencies=[
            ResolvedDependency(path="b", identity="1"),
            ResolvedDependency(path="a", identity="2"),
        ],
    )
    back = Attestation.from_json(json.loads(a.to_json()))
    assert back.resolved_dependencies[0].path == "b", "assembly order must survive"


def test_the_producer_records_the_digest_algorithm():
    """Makes a future algorithm change detectable rather than silent."""
    p = Producer()
    assert p.digest_algorithm == "blake3"
    assert p.name == "promptrecipe"


def test_both_identities_are_distinct_fields():
    a = sample()
    assert a.structural_identity != a.instance_identity
PY

pytest tests/test_provenance_record.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.provenance'`

### Step 2 — GREEN: write the record (4 min)

```bash
cat > src/promptrecipe/provenance.py <<'PY'
"""Provenance — emitted AT assembly time, never reconstructed (SD5).

Reconstruction after the fact cannot recover condition outcomes, and under
amendment 3 a version choice IS a condition outcome. So the record is a
return value of assembly, not something you can query for later.

Shape follows supply-chain attestation: a subject with its digest, the
resolved dependencies each with their digest, and the producer's identity.
The signing/envelope machinery of that standard is deliberately NOT adopted —
it serves cross-organizational trust, which no requirement here calls for.
The shape matches, so adopting it later is a migration, not a rewrite.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from promptrecipe.identity import DIGEST_ALGORITHM


@dataclass(frozen=True, slots=True)
class ResolvedDependency:
    path: str
    identity: str


@dataclass(frozen=True, slots=True)
class Producer:
    name: str = "promptrecipe"
    version: str = "0.1.0"
    # Recorded so a future change of digest algorithm is detectable, not silent.
    digest_algorithm: str = DIGEST_ALGORITHM


@dataclass(frozen=True, slots=True)
class Attestation:
    """The full record of one assembly."""

    subject: str
    """Digest of the assembled output."""

    resolved_dependencies: list[ResolvedDependency] = field(default_factory=list)
    """Every fragment consumed, in assembly ORDER. Ordered, never a set (SD13)."""

    condition_outcomes: list[tuple[str, bool]] = field(default_factory=list)
    """Every condition and its outcome. Without these a branch cannot be replayed (SD6)."""

    resolved_order: list[str] = field(default_factory=list)
    address_resolutions: list[tuple[str, str]] = field(default_factory=list)

    value_bindings: list[tuple[str, str]] = field(default_factory=list)
    """Included in INSTANCE identity, EXCLUDED from STRUCTURAL identity (ADR-005)."""

    producer: Producer = field(default_factory=Producer)

    recorded_at: str | None = None
    """Metadata only — EXCLUDED from both digests (TRD §4, wall-clock leakage)."""

    structural_identity: str = ""
    """Compare across variants. Excludes value bindings."""

    instance_identity: str = ""
    """Reproduce exact text from this. Includes value bindings."""

    def to_json(self) -> str:
        # sort_keys for a stable serialization; the digests themselves are
        # computed from an explicit canonical form, not from this JSON.
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: dict) -> Attestation:
        return cls(
            subject=data["subject"],
            resolved_dependencies=[
                ResolvedDependency(**d) for d in data["resolved_dependencies"]
            ],
            condition_outcomes=[tuple(x) for x in data["condition_outcomes"]],
            resolved_order=list(data["resolved_order"]),
            address_resolutions=[tuple(x) for x in data["address_resolutions"]],
            value_bindings=[tuple(x) for x in data["value_bindings"]],
            producer=Producer(**data["producer"]),
            recorded_at=data.get("recorded_at"),
            structural_identity=data["structural_identity"],
            instance_identity=data["instance_identity"],
        )
PY

pytest tests/test_provenance_record.py
```
Expected: `4 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(provenance): attestation record

Shaped after supply-chain attestation (subject, resolved dependencies,
producer) without its signing machinery, which serves cross-org trust
this library does not need. Dependencies are an ordered list because
order is part of identity (SD13)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/provenance.py tests/test_provenance_record.py
```

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

from promptrecipe.identity import DIGEST_ALGORITHM, FragmentId


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
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_json(cls, data: dict) -> Attestation:
        return cls(
            subject=data["subject"],
            resolved_dependencies=[ResolvedDependency(**d) for d in data["resolved_dependencies"]],
            condition_outcomes=[tuple(x) for x in data["condition_outcomes"]],
            resolved_order=list(data["resolved_order"]),
            address_resolutions=[tuple(x) for x in data["address_resolutions"]],
            value_bindings=[tuple(x) for x in data["value_bindings"]],
            producer=Producer(**data["producer"]),
            recorded_at=data.get("recorded_at"),
            structural_identity=data["structural_identity"],
            instance_identity=data["instance_identity"],
        )


def canonical_structural_form(a: Attestation) -> str:
    """Canonical text for the STRUCTURAL identity.

    Excludes value bindings (ADR-005) and the timestamp (TRD §4).

    Dependency ORDER is preserved because order is part of what the prompt is
    (SD13). Binding-style collections are SORTED because their order is
    incidental. Getting that distinction backwards is the easiest way to
    corrupt every comparison the product will ever produce.
    """
    lines: list[str] = ["deps"]
    # NOT sorted: assembly order is meaningful.
    lines += [f"{d.path}\t{d.identity}" for d in a.resolved_dependencies]

    lines.append("order")
    lines += list(a.resolved_order)

    lines.append("conditions")
    lines += [f"{expr}\t{outcome}" for expr, outcome in sorted(a.condition_outcomes)]

    lines.append("addresses")
    lines += [f"{name}\t{path}" for name, path in sorted(a.address_resolutions)]

    lines.append("producer")
    lines.append(f"{a.producer.name}\t{a.producer.version}\t{a.producer.digest_algorithm}")

    return "\n".join(lines) + "\n"


def canonical_instance_form(a: Attestation) -> str:
    """Canonical text for the INSTANCE identity: the structural form plus the
    value bindings, sorted."""
    lines = [canonical_structural_form(a).rstrip("\n"), "values"]
    lines += [f"{name}\t{value}" for name, value in sorted(a.value_bindings)]
    return "\n".join(lines) + "\n"


def structural_identity(a: Attestation) -> str:
    """The identity to COMPARE by. Excludes value bindings (ADR-005).

    Two assemblies share this when they are the same prompt design. Group A/B
    results by this one.
    """
    return FragmentId.of(canonical_structural_form(a).encode("utf-8")).hex


def instance_identity(a: Attestation) -> str:
    """The identity to REPRODUCE from. Includes value bindings (ADR-005).

    Two assemblies share this only when they are the same rendered text.
    Comparing by this one makes every call unique and groups nothing.
    """
    return FragmentId.of(canonical_instance_form(a).encode("utf-8")).hex

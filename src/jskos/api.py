"""A model for JSKOS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from curies import Converter, Reference
from pydantic import BaseModel, Field

__all__ = [
    "KOS",
    "Concept",
    "InternationalizedStr",
    "LanguageCode",
    "ProcessedConcept",
    "ProcessedKOS",
    "process",
    "read",
]

#: A hint for timeout in :func:`requests.get`
type TimeoutHint = int | float | None | tuple[float | int, float | int]

#: A two-letter language code
type LanguageCode = str

#: A dictionary from two-letter language codes to values in multiple languages
type InternationalizedStr = dict[LanguageCode, str]

_PROTOCOLS: set[str] = {"http", "https"}


class Concept(BaseModel):
    """Represents a concept in JSKOS."""

    id: str
    preferred_label: InternationalizedStr = Field(..., alias="prefLabel")
    narrower: list[Concept] = Field(default_factory=list)


class KOS(BaseModel):
    """A wrapper around a knowledge organization system (KOS)."""

    id: str
    type: str
    title: InternationalizedStr
    description: InternationalizedStr
    has_top_concept: list[Concept] = Field(..., alias="hasTopConcept")


def read(path: str | Path, *, timeout: TimeoutHint = None) -> KOS:
    """Read a JSKOS file."""
    if isinstance(path, str) and any(path.startswith(protocol) for protocol in _PROTOCOLS):
        res = requests.get(path, timeout=timeout or 5)
        res.raise_for_status()
        return _process(res.json())
    raise NotImplementedError


def _process(res_json: dict[str, Any]) -> KOS:
    res_json.pop("@context", {})
    # TODO use context to process
    return KOS.model_validate(res_json)


class ProcessedConcept(BaseModel):
    """A processed JSKOS concept."""

    reference: Reference
    label: InternationalizedStr
    narrower: list[ProcessedConcept] = Field(default_factory=list)


class ProcessedKOS(BaseModel):
    """A processed knowledge organization system."""

    id: str
    type: str
    title: InternationalizedStr
    description: InternationalizedStr
    concepts: list[ProcessedConcept] = Field(default_factory=list)


def process(kos: KOS, converter: Converter) -> ProcessedKOS:
    """Process a KOS."""
    return ProcessedKOS(
        id=kos.id,
        type=kos.type,
        title=kos.title,
        description=kos.description,
        concepts=[_process_concept(concept, converter) for concept in kos.has_top_concept],
    )


def _process_concept(concept: Concept, converter: Converter) -> ProcessedConcept:
    return ProcessedConcept(
        reference=converter.parse_uri(concept.id, strict=True).to_pydantic(),
        label=concept.preferred_label,
        narrower=[_process_concept(n, converter) for n in concept.narrower],
    )

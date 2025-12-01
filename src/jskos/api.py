"""A model for JSKOS."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import requests
from curies import Converter, Reference, SemanticallyProcessable
from pydantic import AnyUrl, BaseModel, Field

__all__ = [
    "KOS",
    "Concept",
    "ConceptBundle",
    "ConceptScheme",
    "Item",
    "LanguageCode",
    "LanguageMap",
    "Mapping",
    "ProcessedConcept",
    "ProcessedKOS",
    "Resource",
    "read",
]

#: A hint for timeout in :func:`requests.get`
type TimeoutHint = int | float | None | tuple[float | int, float | int]

#: A two-letter language code
type LanguageCode = str

#: A dictionary from two-letter language codes to values in multiple languages
type LanguageMap = dict[LanguageCode, str]

type LanguageMapOfList = dict[LanguageCode, list[str]]

_PROTOCOLS: set[str] = {"http", "https"}


class Resource(BaseModel):
    """A resource, based on https://gbv.github.io/jskos/#resource."""

    uri: AnyUrl | None = None
    identifier: list[AnyUrl] | None = None
    type: list[AnyUrl] | None = None
    created: datetime.date | None = None
    issued: datetime.date | None = None
    modified: datetime.date | None = None

    # creator
    # contributor
    # source
    # publisher
    # partOf
    # annotations
    # qualifiedRelations
    # qualifiedDates
    # qualifiedLiterals
    # rank


class Item(Resource):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    url: AnyUrl | None = None
    # notation
    preferred_label: LanguageMap | None = Field(None, alias="prefLabel")
    alternative_label: LanguageMapOfList | None = Field(None, alias="altLabel")
    hidden_label: LanguageMapOfList | None = Field(None, alias="hiddenLabel")
    scope_note: LanguageMapOfList | None = Field(None, alias="scopeNote")
    definition: LanguageMapOfList | None = Field(None)
    example: LanguageMapOfList | None = Field(None)
    # historyNote
    # editorialNote
    # changeNote
    # note
    # startDate
    # endDate
    # relatedDate
    # relatedDates
    # startPlace
    # endPlace
    # place
    # location
    # address
    # replacedBy
    # basedOn
    # subject
    # subjectOf
    # depiction
    # media
    # tool
    # issue
    # issueTracker
    # guidelines
    # version
    # versionOf


class Mapping(Item):
    """A mapping, defined in https://gbv.github.io/jskos/#mapping."""

    from_: ConceptBundle = Field(..., alias="from")
    to: ConceptBundle = Field(...)
    from_scheme: ConceptScheme | None = Field(None)
    to_scheme: ConceptScheme | None = Field(None)
    mapping_relevance: float | None = Field(None, le=1.0, ge=0.0)
    justification: AnyUrl | None = None


class ConceptScheme(Item):
    """A concept scheme, defined in https://gbv.github.io/jskos/#concept-scheme."""


class ConceptBundle(BaseModel):
    """A concept bundle, defined in https://gbv.github.io/jskos/#concept-bundle."""

    member_set: list[Concept] | None = Field(None, alias="memberSet")
    member_list: list[Concept] | None = Field(None, alias="memberList")
    member_choice: list[Concept] | None = Field(None, alias="memberChoice")
    # member_roles


class Concept(Item, ConceptBundle):
    """Represents a concept in JSKOS."""

    narrower: list[Concept] | None = Field(None)
    broader: list[Concept] | None = Field(None)
    related: list[Concept] | None = Field(None)
    # previous
    # next
    # ancestors
    # inScheme
    # topConceptOf
    mappings: list[Mapping] | None = Field(None)
    # occurrences
    deprecated: bool | None = None

    def process(self, converter: Converter) -> ProcessedConcept:
        """Process the concept."""
        return ProcessedConcept(
            references=[
                converter.parse_uri(str(uri), strict=True).to_pydantic() for uri in self.identifier
            ]
            if self.identifier is not None
            else None,
            label=self.preferred_label,
            narrower=[n.process(converter) for n in self.narrower]
            if self.narrower is not None
            else None,
            broader=[n.process(converter) for n in self.broader]
            if self.broader is not None
            else None,
            related=[n.process(converter) for n in self.related]
            if self.related is not None
            else None,
        )


class KOS(BaseModel, SemanticallyProcessable["ProcessedKOS"]):
    """A wrapper around a knowledge organization system (KOS)."""

    id: str
    type: str
    title: LanguageMap
    description: LanguageMap
    has_top_concept: list[Concept] | None = Field(None, alias="hasTopConcept")

    def process(self, converter: Converter) -> ProcessedKOS:
        """Process a KOS."""
        return ProcessedKOS(
            id=self.id,
            type=self.type,
            title=self.title,
            description=self.description,
            concepts=[concept.process(converter) for concept in self.has_top_concept]
            if self.has_top_concept
            else None,
        )


def read(path: str | Path, *, timeout: TimeoutHint = None) -> KOS:
    """Read a JSKOS file."""
    if isinstance(path, str) and any(path.startswith(protocol) for protocol in _PROTOCOLS):
        res = requests.get(path, timeout=timeout or 5)
        res.raise_for_status()
        return _process(res.json())
    with open(path) as file:
        return _process(json.load(file))


def _process(res_json: dict[str, Any]) -> KOS:
    res_json.pop("@context", {})
    # TODO use context to process
    return KOS.model_validate(res_json)


class ProcessedConcept(BaseModel):
    """A processed JSKOS concept."""

    # see https://gbv.github.io/jskos/#concept

    references: list[Reference] | None = None
    label: LanguageMap
    narrower: list[ProcessedConcept] | None = Field(None)
    broader: list[ProcessedConcept] | None = Field(None)
    related: list[ProcessedConcept] | None = Field(None)


class ProcessedKOS(BaseModel):
    """A processed knowledge organization system."""

    id: str
    type: str
    title: LanguageMap
    description: LanguageMap
    concepts: list[ProcessedConcept] = Field(default_factory=list)


ConceptBundle.model_rebuild()

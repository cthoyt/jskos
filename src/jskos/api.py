"""A model for JSKOS."""

from __future__ import annotations

import datetime
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import curies
import requests
from curies import Converter, Reference, SemanticallyProcessable
from curies.mixins import process_many
from pydantic import AliasChoices, AnyUrl, BaseModel, Field

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


class ResourceMixin(BaseModel):
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


class Resource(ResourceMixin, SemanticallyProcessable["ProcessedResource"]):
    """A resource, based on https://gbv.github.io/jskos/#resource."""

    def process(self, converter: curies.Converter) -> ProcessedResource:
        """Process the resource."""
        return ProcessedResource(
            reference=converter.parse_uri(str(self.uri), strict=True)
            if self.uri is not None
            else None,
            identifier=_luri(self.identifier, converter),
            type=self.type,
            created=self.created,
            issued=self.issued,
            modified=self.modified,
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
        )


class ItemMixin(ResourceMixin):
    """An item, defined in https://gbv.github.io/jskos/#item."""

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


class Item(ItemMixin, SemanticallyProcessable["ProcessedItem"]):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    def process(self, converter: curies.Converter) -> ProcessedItem:
        """Process the item."""
        return ProcessedItem(
            reference=converter.parse_uri(str(self.uri), strict=True)
            if self.uri is not None
            else None,
            identifier=_luri(self.identifier, converter),
            type=self.type,
            created=self.created,
            issued=self.issued,
            modified=self.modified,
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
            # --- below this is from Item
            preferred_label=self.preferred_label,
            alternative_label=self.alternative_label,
            hidden_label=self.hidden_label,
            scope_note=self.scope_note,
            definition=self.definition,
            example=self.example,
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
        )


class Mapping(ItemMixin, SemanticallyProcessable["ProcessedMapping"]):
    """A mapping, defined in https://gbv.github.io/jskos/#mapping."""

    subject_bundle: ConceptBundle = Field(
        ..., validation_alias=AliasChoices("source_bundle", "from"), serialization_alias="from"
    )
    object_bundle: ConceptBundle = Field(
        ..., validation_alias=AliasChoices("object_bundle", "to"), serialization_alias="to"
    )
    from_scheme: ConceptScheme | None = Field(
        None,
        validation_alias=AliasChoices("from_scheme", "fromScheme"),
        serialization_alias="fromScheme",
    )
    to_scheme: ConceptScheme | None = Field(
        None, validation_alias=AliasChoices("to_scheme", "toScheme"), serialization_alias="toScheme"
    )
    mapping_relevance: float | None = Field(None, le=1.0, ge=0.0)
    justification: AnyUrl | None = None

    def process(self, converter: curies.Converter) -> ProcessedMapping:
        """Process the mapping."""
        return ProcessedMapping(
            from_bundle=self.subject_bundle.process(converter),
            to_bundle=self.object_bundle.process(converter),
            from_scheme=self.from_scheme.process(converter)
            if self.from_scheme is not None
            else None,
            to_scheme=self.to_scheme.process(converter) if self.to_scheme is not None else None,
            mapping_relevance=self.mapping_relevance,
            justification=converter.parse_uri(str(self.justification), strict=True)
            if self.justification is not None
            else None,
        )


class ConceptScheme(ItemMixin, SemanticallyProcessable["ProcessedConceptScheme"]):
    """A concept scheme, defined in https://gbv.github.io/jskos/#concept-scheme."""

    top_concepts: list[Concept] | None = Field(None, alias="from")
    namespace: AnyUrl | None = None
    uri_pattern: str | None = Field(None, alias="uriPattern")
    notation_pattern: str | None = Field(None, alias="notationPattern")
    notation_examples: list[str] | None = Field(None, alias="notationExamples")

    # concepts
    # types
    # distributions
    # extent
    # languages
    # license

    def process(self, converter: curies.Converter) -> ProcessedConceptScheme:
        """Process the concept scheme."""
        return ProcessedConceptScheme(
            top_concepts=process_many(self.top_concepts, converter),
            namespace=self.namespace,
            uri_pattern=self.uri_pattern,
            notation_pattern=self.notation_pattern,
            notation_examples=self.notation_examples,
            # concepts
            # types
            # distributions
            # extent
            # languages
            # license
        )


class ConceptBundleMixin(BaseModel):
    """A concept bundle, defined in https://gbv.github.io/jskos/#concept-bundle."""

    member_set: list[Concept] | None = Field(None, alias="memberSet")
    member_list: list[Concept] | None = Field(None, alias="memberList")
    member_choice: list[Concept] | None = Field(None, alias="memberChoice")
    # member_roles


class ConceptBundle(ConceptBundleMixin, SemanticallyProcessable["ProcessedConceptBundle"]):
    """A concept bundle, defined in https://gbv.github.io/jskos/#concept-bundle."""

    def process(self, converter: curies.Converter) -> ProcessedConceptBundle:
        """Process the concept bundle."""
        return ProcessedConceptBundle(
            member_set=process_many(self.member_set, converter),
            member_list=process_many(self.member_list, converter),
            member_choice=process_many(self.member_choice, converter),
            # member_roles
        )


def _luri(inp: Sequence[AnyUrl] | None, converter: Converter) -> list[Reference] | None:
    if inp is None:
        return None
    return [converter.parse_uri(str(uri), strict=True).to_pydantic() for uri in inp]


def _lp(inp: Sequence[str] | None, converter: Converter) -> list[Reference] | None:
    if inp is None:
        return None
    return [converter.parse_uri(uri, strict=True).to_pydantic() for uri in inp]


class Concept(ItemMixin, ConceptBundleMixin, SemanticallyProcessable["ProcessedConcept"]):
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
            # TODO fill in item mixin
            narrower=process_many(self.narrower, converter),
            broader=process_many(self.broader, converter),
            related=process_many(self.related, converter),
            mappings=process_many(self.mappings, converter),
            deprecated=self.deprecated,
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
            concepts=process_many(self.has_top_concept, converter),
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


class ProcessedResource(BaseModel):
    """Represents a processed resource."""

    reference: Reference | None = None
    identifier: list[Reference] | None = None
    type: list[Reference] | None = None
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


class ProcessedItem(BaseModel):
    """Represents a processed item."""

    # notation
    preferred_label: LanguageMap | None = Field(None)
    alternative_label: LanguageMapOfList | None = Field(None)
    hidden_label: LanguageMapOfList | None = Field(None)
    scope_note: LanguageMapOfList | None = Field(None)
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


class ProcessedConceptBundle(BaseModel):
    """Represents a processed concept."""

    member_set: list[ProcessedConcept] | None = Field(None)
    member_list: list[ProcessedConcept] | None = Field(None)
    member_choice: list[ProcessedConcept] | None = Field(None)
    # member_roles


class ProcessedConceptScheme(BaseModel):
    """Represents a processed concept schema."""

    top_concepts: list[ProcessedConcept] | None = Field(None)
    namespace: AnyUrl | None = None
    uri_pattern: str | None = Field(None)
    notation_pattern: str | None = Field(None)
    notation_examples: list[str] | None = Field(None)
    # concepts
    # types
    # distributions
    # extent
    # languages
    # license


class ProcessedMapping(BaseModel):
    """Represents a processed mapping."""

    from_bundle: ProcessedConceptBundle = Field(...)
    to_bundle: ProcessedConceptBundle = Field(...)
    from_scheme: ProcessedConceptScheme | None = Field(None)
    to_scheme: ProcessedConceptScheme | None = Field(None)
    mapping_relevance: float | None = Field(None, le=1.0, ge=0.0)
    justification: Reference | None = None


class ProcessedConcept(ProcessedItem, ProcessedConceptBundle):
    """A processed JSKOS concept."""

    narrower: list[ProcessedConcept] | None = Field(None)
    broader: list[ProcessedConcept] | None = Field(None)
    related: list[ProcessedConcept] | None = Field(None)
    # previous
    # next
    # ancestors
    # inScheme
    # topConceptOf
    mappings: list[ProcessedMapping] | None = Field(None)
    # occurrences
    deprecated: bool | None = None


class ProcessedKOS(BaseModel):
    """A processed knowledge organization system."""

    id: str
    type: str
    title: LanguageMap
    description: LanguageMap
    concepts: list[ProcessedConcept] = Field(default_factory=list)

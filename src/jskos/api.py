"""A model for JSKOS."""

from __future__ import annotations

import datetime
import json
from abc import ABC
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

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

type JSKOSSet = list[Resource | None]
type ProcessedJSKOSSet = list[ProcessedResource | None]

#: https://gbv.github.io/jskos/#rank
type Rank = Literal["preferred", "normal", "deprecated"]


class ResourceMixin(BaseModel):
    """A resource, based on https://gbv.github.io/jskos/#resource."""

    context: AnyUrl | list[AnyUrl] | None = Field(None, serialization_alias="@context")
    uri: AnyUrl | None = None
    identifier: list[AnyUrl] | None = None
    type: list[AnyUrl] | None = None
    created: datetime.date | None = None
    issued: datetime.date | None = None
    modified: datetime.date | None = None
    creator: JSKOSSet | None = None
    contributor: JSKOSSet | None = None
    source: JSKOSSet | None = None
    publisher: JSKOSSet | None = None
    part_of: JSKOSSet | None = Field(None, serialization_alias="partOf")
    annotations: list[Annotation] | None = None
    qualified_relations: dict[AnyUrl, QualifiedRelation] | None = Field(
        None, serialization_alias="qualifiedRelations"
    )
    qualified_dates: dict[AnyUrl, QualifiedDate] | None = Field(
        None, serialization_alias="qualifiedDates"
    )
    qualified_literals: dict[AnyUrl, QualifiedLiteral] | None = Field(
        None, serialization_alias="qualifiedLiterals"
    )
    rank: Rank | None = None


class QualifiedValue[X](BaseModel, SemanticallyProcessable[X], ABC):
    """A qualified value, based on https://gbv.github.io/jskos/#qualified-value."""

    start_date: datetime.date | None = Field(None, serialization_alias="startDate")
    end_date: datetime.date | None = Field(None, serialization_alias="endDate")
    source: JSKOSSet | None = None
    rank: Rank | None = None


class ProcessedQualifiedValue(BaseModel):
    """A qualified value, based on https://gbv.github.io/jskos/#qualified-value."""

    start_date: datetime.date | None = Field(None, serialization_alias="startDate")
    end_date: datetime.date | None = Field(None, serialization_alias="endDate")
    source: ProcessedJSKOSSet | None = None
    rank: Rank | None = None


class ProcessedQualifiedRelation(ProcessedQualifiedValue):
    """A processed qualified relation."""

    resource: ProcessedResource


class QualifiedRelation(QualifiedValue[ProcessedQualifiedRelation]):
    """A qualified relation, based on https://gbv.github.io/jskos/#qualified-relation."""

    resource: Resource

    def process(self, converter: Converter) -> ProcessedQualifiedRelation:
        """Process the qualified relation."""
        return ProcessedQualifiedRelation(
            start_date=self.start_date,
            end_date=self.end_date,
            source=_process_jskos_set(self.source, converter),
            rank=self.rank,
            resource=self.resource.process(converter),
        )


class ProcessedQualifiedDate(ProcessedQualifiedValue):
    """A processed qualified date."""

    date: datetime.date
    place: ProcessedJSKOSSet | None = None


class QualifiedDate(QualifiedValue[ProcessedQualifiedDate]):
    """A qualified date, based on https://gbv.github.io/jskos/#qualified-date."""

    date: datetime.date
    place: JSKOSSet | None = None

    def process(self, converter: Converter) -> ProcessedQualifiedDate:
        """Process the qualified date."""
        return ProcessedQualifiedDate(
            start_date=self.start_date,
            end_date=self.end_date,
            source=_process_jskos_set(self.source, converter),
            rank=self.rank,
            date=self.date,
            place=_process_jskos_set(self.place, converter),
        )


class QualifiedLiteralInner(BaseModel):
    """A string with a language."""

    string: str
    language: LanguageCode | None = None


class ProcessedQualifiedLiteral(ProcessedQualifiedValue):
    """A processed qualified literal."""

    literal: QualifiedLiteralInner
    reference: Reference | None = None
    type: list[Reference] | None = None


class QualifiedLiteral(QualifiedValue[ProcessedQualifiedLiteral]):
    """A qualified literal, based on https://gbv.github.io/jskos/#qualified-literal."""

    literal: QualifiedLiteralInner
    uri: AnyUrl | None = None
    type: list[AnyUrl] | None = None

    def process(self, converter: Converter) -> ProcessedQualifiedLiteral:
        """Process the qualified literal."""
        return ProcessedQualifiedLiteral(
            start_date=self.start_date,
            end_date=self.end_date,
            source=_process_jskos_set(self.source, converter),
            rank=self.rank,
            literal=self.literal,
            reference=_parse_optional_url(self.uri, converter),
            type=_parse_optional_urls(self.type, converter),
        )


class ProcessedAnnotation(BaseModel):
    """A processed annotation."""

    context: AnyUrl
    type: str
    reference: Reference  # from `id`
    target: Reference | ProcessedResource | ProcessedAnnotation


class Annotation(BaseModel, SemanticallyProcessable[ProcessedAnnotation]):
    """An annotation, based on https://gbv.github.io/jskos/#annotation."""

    context: AnyUrl = Field(..., serialization_alias="@context")
    type: str
    id: AnyUrl
    target: AnyUrl | Resource | Annotation

    def process(self, converter: Converter) -> ProcessedAnnotation:
        """Process the annotation."""
        target: Reference | ProcessedResource | ProcessedAnnotation
        match self.target:
            case Resource() | Annotation():
                target = self.target.process(converter)
            case AnyUrl():
                target = converter.parse_uri(str(self.target), strict=True).to_pydantic()
            case _:
                raise TypeError
        return ProcessedAnnotation(
            context=self.context,
            type=self.type,  # TODO what is this?
            reference=converter.parse_uri(str(self.id), strict=True).to_pydantic(),
            target=target,
        )


class ProcessedResource(BaseModel):
    """Represents a processed resource."""

    context: AnyUrl | list[AnyUrl] | None = None
    reference: Reference | None = None  # from uri
    identifier: list[Reference] | None = None
    type: list[Reference] | None = None
    created: datetime.date | None = None
    issued: datetime.date | None = None
    modified: datetime.date | None = None
    creator: ProcessedJSKOSSet | None = None
    contributor: ProcessedJSKOSSet | None = None
    source: ProcessedJSKOSSet | None = None
    publisher: ProcessedJSKOSSet | None = None
    part_of: ProcessedJSKOSSet | None = None
    annotations: list[ProcessedAnnotation] | None = None
    qualified_relations: dict[Reference, ProcessedQualifiedRelation] | None = None
    qualified_dates: dict[Reference, ProcessedQualifiedDate] | None = None
    qualified_literals: dict[Reference, ProcessedQualifiedLiteral] | None = None
    rank: Rank | None = None


class Resource(ResourceMixin, SemanticallyProcessable[ProcessedResource]):
    """A resource, based on https://gbv.github.io/jskos/#resource."""

    def process(self, converter: curies.Converter) -> ProcessedResource:
        """Process the resource."""
        return ProcessedResource(
            context=self.context,
            reference=converter.parse_uri(str(self.uri), strict=True)
            if self.uri is not None
            else None,
            identifier=_parse_optional_urls(self.identifier, converter),
            type=self.type,
            created=self.created,
            issued=self.issued,
            modified=self.modified,
            creator=_process_jskos_set(self.creator, converter),
            contributor=_process_jskos_set(self.contributor, converter),
            source=_process_jskos_set(self.source, converter),
            publisher=_process_jskos_set(self.publisher, converter),
            part_of=_process_jskos_set(self.part_of, converter),
            annotations=process_many(self.annotations, converter),
            qualified_relations=_process_dict(self.qualified_relations, converter),
            qualified_dates=_process_dict(self.qualified_dates, converter),
            qualified_literals=_process_dict(self.qualified_literals, converter),
            rank=self.rank,
        )


class ItemMixin(ResourceMixin):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    notation: list[str] | None = None
    preferred_label: LanguageMap | None = Field(None, serialization_alias="prefLabel")
    alternative_label: LanguageMapOfList | None = Field(None, serialization_alias="altLabel")
    hidden_label: LanguageMapOfList | None = Field(None, serialization_alias="hiddenLabel")
    scope_note: LanguageMapOfList | None = Field(None, serialization_alias="scopeNote")
    definition: LanguageMapOfList | None = Field(None)
    example: LanguageMapOfList | None = Field(None)
    history_note: LanguageMapOfList | None = Field(None, serialization_alias="historyNote")
    editorial_note: LanguageMapOfList | None = Field(None, serialization_alias="editorialNote")
    change_note: LanguageMapOfList | None = Field(None, serialization_alias="changeNote")
    note: LanguageMapOfList | None = Field(None)
    start_date: datetime.date | None = Field(None, serialization_alias="startDate")
    end_date: datetime.date | None = Field(None, serialization_alias="endDate")
    related_date: datetime.date | None = Field(None, serialization_alias="relatedDate")
    related_dates: list[datetime.date] | None = Field(None, serialization_alias="relatedDates")
    start_place: JSKOSSet | None = Field(None, serialization_alias="startPlace")
    end_place: JSKOSSet | None = Field(None, serialization_alias="endPlace")
    place: JSKOSSet | None = Field(None)
    # location# TODO
    # address# TODO
    replaced_by: list[Item] | None = Field(None, serialization_alias="replacedBy")
    based_on: list[Item] | None = Field(None, serialization_alias="basedOn")
    subject: JSKOSSet | None = None
    subject_of: JSKOSSet | None = Field(None, serialization_alias="subjectOf")
    depiction: list[Any] | None = None
    # media # TODO
    tool: list[Item] | None = None
    issue: list[Item] | None = None
    issue_tracker: list[Item] | None = Field(None, serialization_alias="issueTracker")
    guidelines: list[Item] | None = None
    version: str | None = None
    version_of: list[Item] | None = Field(None, serialization_alias="versionOf")


class Item(ItemMixin, SemanticallyProcessable["ProcessedItem"]):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    def process(self, converter: curies.Converter) -> ProcessedItem:
        """Process the item."""
        return ProcessedItem(
            reference=_parse_optional_url(self.uri, converter),
            identifier=_parse_optional_urls(self.identifier, converter),
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


class Occurrence(ResourceMixin, ConceptBundleMixin):
    """An occurrence, based on https://gbv.github.io/jskos/#occurrence."""

    database: Item | None = None
    count: int | None = None
    frequency: float | None = Field(None, le=1.0, ge=0.0)
    relation: AnyUrl | None = None
    schemes: list[ConceptScheme] | None = None
    url: AnyUrl | None = None
    template: str | None = None
    separator: str | None = None


class Concept(ItemMixin, ConceptBundleMixin, SemanticallyProcessable["ProcessedConcept"]):
    """Represents a concept in JSKOS."""

    narrower: JSKOSSet | None = None
    broader: JSKOSSet | None = None
    related: JSKOSSet | None = None
    previous: JSKOSSet | None = None
    next: JSKOSSet | None = None
    ancestors: JSKOSSet | None = None
    in_scheme: list[ConceptScheme] | None = Field(None, serialization_alias="inScheme")
    top_concept_of: list[ConceptScheme] | None = Field(None, serialization_alias="topConceptOf")
    mappings: list[Mapping] | None = Field(None)
    occurrences: list[Occurrence] | None = None
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


class ProcessedItem(ProcessedResource):
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


def _process_jskos_set(s: JSKOSSet | None, converter: curies.Converter) -> ProcessedJSKOSSet | None:
    if s is None:
        return None
    return [e.process(converter) if e is not None else None for e in s]


def _process_dict[X](
    i: dict[AnyUrl, SemanticallyProcessable[X]] | None, converter: Converter
) -> dict[Reference, X] | None:
    if i is None:
        return None
    return {
        converter.parse_uri(str(k), strict=True).to_pydantic(): v.process(converter)
        for k, v in i.items()
    }


def _parse_optional_urls(
    urls: Sequence[str | AnyUrl] | None, converter: Converter
) -> list[Reference] | None:
    if urls is None:
        return None
    return [converter.parse_uri(str(url), strict=True).to_pydantic() for url in urls]


def _parse_optional_url(url: str | AnyUrl | None, converter: Converter) -> Reference | None:
    if url is None:
        return None
    return converter.parse_uri(str(url), strict=True).to_pydantic()

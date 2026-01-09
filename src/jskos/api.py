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

type JSKOSSet = list[Resource | None]
type ProcessedJSKOSSet = list[ProcessedResource | None]

#: https://gbv.github.io/jskos/#rank
type Rank = Literal["preferred", "normal", "deprecated"]

type LocationType = Literal[
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
]


class Location(BaseModel):
    """A location, based on https://gbv.github.io/jskos/#location."""

    type: LocationType
    coordinates: list[float]


class Address(BaseModel):
    """An address, based on https://gbv.github.io/jskos/#address."""

    pobox: str | None = None
    ext: str | None = None
    street: str | None = None
    locality: str | None = None
    region: str | None = None
    code: str | None = None
    country: str | None = None


# https://gbv.github.io/jskos/#media isn't super well-defined
type Media = dict[str, Any]


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

    def _process_resource_helper(self, converter: Converter) -> dict[str, Any]:
        return {
            "context": self.context,
            "reference": _parse_optional_url(self.uri, converter),
            "identifier": _parse_optional_urls(self.identifier, converter),
            "type": self.type,
            "created": self.created,
            "issued": self.issued,
            "modified": self.modified,
            "creator": _process_jskos_set(self.creator, converter),
            "contributor": _process_jskos_set(self.contributor, converter),
            "source": _process_jskos_set(self.source, converter),
            "publisher": _process_jskos_set(self.publisher, converter),
            "part_of": _process_jskos_set(self.part_of, converter),
            "annotations": process_many(self.annotations, converter),
            "qualified_relations": _process_dict(self.qualified_relations, converter),  # type:ignore
            "qualified_dates": _process_dict(self.qualified_dates, converter),  # type:ignore
            "qualified_literals": _process_dict(self.qualified_literals, converter),  # type:ignore
            "rank": self.rank,
        }


class QualifiedValue[X](BaseModel, SemanticallyProcessable[X], ABC):
    """A qualified value, based on https://gbv.github.io/jskos/#qualified-value."""

    start_date: datetime.date | None = Field(None, serialization_alias="startDate")
    end_date: datetime.date | None = Field(None, serialization_alias="endDate")
    source: JSKOSSet | None = None
    rank: Rank | None = None

    def _process_helper(self, converter: Converter) -> dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "source": _process_jskos_set(self.source, converter),
            "rank": self.rank,
        }


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
            **self._process_helper(converter),
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
            **self._process_helper(converter),
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
            **self._process_helper(converter),
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
                target = _parse_url(self.target, converter)
            case _:
                raise TypeError
        return ProcessedAnnotation(
            context=self.context,
            type=self.type,  # TODO what is this?
            reference=_parse_url(self.id, converter),
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
        return ProcessedResource(**self._process_resource_helper(converter))


class ItemMixin(ResourceMixin):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    notation: list[str] | None = None
    preferred_label: LanguageMap | None = Field(None, serialization_alias="prefLabel")
    alternative_label: LanguageMapOfList | None = Field(None, serialization_alias="altLabel")
    hidden_label: LanguageMapOfList | None = Field(None, serialization_alias="hiddenLabel")
    scope_note: LanguageMapOfList | None = Field(None, serialization_alias="scopeNote")
    definition: LanguageMapOfList | None = None
    example: LanguageMapOfList | None = None
    history_note: LanguageMapOfList | None = Field(None, serialization_alias="historyNote")
    editorial_note: LanguageMapOfList | None = Field(None, serialization_alias="editorialNote")
    change_note: LanguageMapOfList | None = Field(None, serialization_alias="changeNote")
    note: LanguageMapOfList | None = None
    start_date: datetime.date | None = Field(None, serialization_alias="startDate")
    end_date: datetime.date | None = Field(None, serialization_alias="endDate")
    related_date: datetime.date | None = Field(None, serialization_alias="relatedDate")
    related_dates: list[datetime.date] | None = Field(None, serialization_alias="relatedDates")
    start_place: JSKOSSet | None = Field(None, serialization_alias="startPlace")
    end_place: JSKOSSet | None = Field(None, serialization_alias="endPlace")
    place: JSKOSSet | None = None
    location: Location | None = None
    address: Address | None = None
    replaced_by: list[Item] | None = Field(None, serialization_alias="replacedBy")
    based_on: list[Item] | None = Field(None, serialization_alias="basedOn")
    subject: JSKOSSet | None = None
    subject_of: JSKOSSet | None = Field(None, serialization_alias="subjectOf")
    depiction: list[Any] | None = None
    media: Media | None = None
    tool: list[Item] | None = None
    issue: list[Item] | None = None
    issue_tracker: list[Item] | None = Field(None, serialization_alias="issueTracker")
    guidelines: list[Item] | None = None
    version: str | None = None
    version_of: list[Item] | None = Field(None, serialization_alias="versionOf")

    def _process_item_helper(self, converter: Converter) -> dict[str, Any]:
        return {
            "preferred_label": self.preferred_label,
            "alternative_label": self.alternative_label,
            "hidden_label": self.hidden_label,
            "scope_note": self.scope_note,
            "definition": self.definition,
            "example": self.example,
            "history_note": self.history_note,
            "editorial_note": self.editorial_note,
            "change_note": self.change_note,
            "note": self.note,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "related_date": self.related_date,
            "related_dates": self.related_dates,
            "start_place": _process_jskos_set(self.start_place, converter),
            "end_place": _process_jskos_set(self.end_place, converter),
            "place": _process_jskos_set(self.place, converter),
            "location": self.location,
            "address": self.address,
            "replaced_by": process_many(self.replaced_by, converter),
            "based_on": process_many(self.based_on, converter),
            "subject": _process_jskos_set(self.subject, converter),
            "subject_of": _process_jskos_set(self.subject_of, converter),
            "depiction": self.depiction,
            "media": self.media,
            "tool": process_many(self.tool, converter),
            "issue": process_many(self.issue, converter),
            "issue_tracker": process_many(self.issue_tracker, converter),
            "guidelines": process_many(self.guidelines, converter),
            "version": self.version_of,
            "version_of": process_many(self.version_of, converter),
        }


class ProcessedItem(ProcessedResource):
    """Represents a processed item."""

    notation: list[str] | None = None
    preferred_label: LanguageMap | None = None
    alternative_label: LanguageMapOfList | None = None
    hidden_label: LanguageMapOfList | None = None
    scope_note: LanguageMapOfList | None = None
    definition: LanguageMapOfList | None = None
    example: LanguageMapOfList | None = None
    history_note: LanguageMapOfList | None = None
    editorial_note: LanguageMapOfList | None = None
    change_note: LanguageMapOfList | None = None
    note: LanguageMapOfList | None = None
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    related_date: datetime.date | None = None
    related_dates: list[datetime.date] | None = None
    start_place: ProcessedJSKOSSet | None = None
    end_place: ProcessedJSKOSSet | None = None
    place: ProcessedJSKOSSet | None = None
    location: Location | None = None
    address: Address | None = None
    replaced_by: list[ProcessedItem] | None = None
    based_on: list[ProcessedItem] | None = None
    subject: ProcessedJSKOSSet | None = None
    subject_of: ProcessedJSKOSSet | None = None
    depiction: list[Any] | None = None
    media: Media | None = None
    tool: list[ProcessedItem] | None = None
    issue: list[ProcessedItem] | None = None
    issue_tracker: list[ProcessedItem] | None = None
    guidelines: list[ProcessedItem] | None = None
    version: str | None = None
    version_of: list[ProcessedItem] | None = None


class Item(ItemMixin, SemanticallyProcessable[ProcessedItem]):
    """An item, defined in https://gbv.github.io/jskos/#item."""

    def process(self, converter: curies.Converter) -> ProcessedItem:
        """Process the item."""
        return ProcessedItem(
            **self._process_resource_helper(converter),
            **self._process_item_helper(converter),
        )


class ProcessedMapping(Item):
    """Represents a processed mapping."""

    from_bundle: ProcessedConceptBundle = Field(...)
    to_bundle: ProcessedConceptBundle = Field(...)
    from_scheme: ProcessedConceptScheme | None = None
    to_scheme: ProcessedConceptScheme | None = None
    mapping_relevance: float | None = Field(None, le=1.0, ge=0.0)
    justification: Reference | None = None


class Mapping(ItemMixin, SemanticallyProcessable[ProcessedMapping]):
    """A mapping, defined in https://gbv.github.io/jskos/#mapping."""

    subject_bundle: ConceptBundle = Field(..., serialization_alias="from")
    object_bundle: ConceptBundle = Field(..., serialization_alias="to")
    from_scheme: ConceptScheme | None = Field(None, serialization_alias="fromScheme")
    to_scheme: ConceptScheme | None = Field(None, serialization_alias="toScheme")
    mapping_relevance: float | None = Field(None, le=1.0, ge=0.0)
    justification: AnyUrl | None = None

    def process(self, converter: curies.Converter) -> ProcessedMapping:
        """Process the mapping."""
        return ProcessedMapping(
            **self._process_resource_helper(converter),
            **self._process_item_helper(converter),
            from_bundle=self.subject_bundle.process(converter),
            to_bundle=self.object_bundle.process(converter),
            from_scheme=_safe_process(self.from_scheme, converter),
            to_scheme=_safe_process(self.to_scheme, converter),
            mapping_relevance=self.mapping_relevance,
            justification=_parse_optional_url(self.justification, converter),
        )


class ProcessedConceptScheme(ProcessedItem):
    """Represents a processed concept schema."""

    top_concepts: list[ProcessedConcept] | None = None
    namespace: AnyUrl | None = None
    uri_pattern: str | None = None
    notation_pattern: str | None = None
    notation_examples: list[str] | None = None
    # concepts
    # types
    # distributions
    # extent
    # languages
    # license


class ConceptScheme(ItemMixin, SemanticallyProcessable[ProcessedConceptScheme]):
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
            **self._process_resource_helper(converter),
            **self._process_item_helper(converter),
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
    member_roles: dict[AnyUrl, list[Concept]] | None = Field(None, alias="memberRoles")

    def _process_concept_bundle_helper(self, converter: curies.Converter) -> dict[str, Any]:
        return {
            "member_set": process_many(self.member_set, converter),
            "member_list": process_many(self.member_list, converter),
            "member_choice": process_many(self.member_choice, converter),
            "member_roles": {
                _parse_url(uri, converter): [concept.process(converter) for concept in concepts]
                for uri, concepts in self.member_roles.items()
            }
            if self.member_roles is not None
            else None,
        }


class ProcessedConceptBundle(BaseModel):
    """Represents a processed concept."""

    member_set: list[ProcessedConcept] | None = None
    member_list: list[ProcessedConcept] | None = None
    member_choice: list[ProcessedConcept] | None = None
    member_roles: dict[Reference, list[ProcessedConcept]] | None = None


class ConceptBundle(ConceptBundleMixin, SemanticallyProcessable[ProcessedConceptBundle]):
    """A concept bundle, defined in https://gbv.github.io/jskos/#concept-bundle."""

    def process(self, converter: curies.Converter) -> ProcessedConceptBundle:
        """Process the concept bundle."""
        return ProcessedConceptBundle.model_validate(self._process_concept_bundle_helper(converter))


class ProcessedOccurrence(ResourceMixin, ConceptBundleMixin):
    """An occurrence, based on https://gbv.github.io/jskos/#occurrence."""

    database: ProcessedItem | None = None
    count: int | None = None
    frequency: float | None = Field(None, le=1.0, ge=0.0)
    relation: Reference | None = None
    schemes: list[ProcessedConceptScheme] | None = None
    url: AnyUrl | None = None  # should this be a reference?
    template: str | None = None
    separator: str | None = None


class Occurrence(ResourceMixin, ConceptBundleMixin, SemanticallyProcessable[ProcessedOccurrence]):
    """An occurrence, based on https://gbv.github.io/jskos/#occurrence."""

    database: Item | None = None
    count: int | None = None
    frequency: float | None = Field(None, le=1.0, ge=0.0)
    relation: AnyUrl | None = None
    schemes: list[ConceptScheme] | None = None
    url: AnyUrl | None = None
    template: str | None = None
    separator: str | None = None

    def process(self, converter: curies.Converter) -> ProcessedOccurrence:
        """Process the occurrence."""
        return ProcessedOccurrence(
            **self._process_resource_helper(converter),
            **self._process_concept_bundle_helper(converter),
            database=_safe_process(self.database, converter),
            count=self.count,
            frequency=self.frequency,
            relation=_parse_optional_url(self.relation, converter),
            schemes=process_many(self.schemes, converter),
            url=self.url,
            template=self.template,
            separator=self.separator,
        )


class ProcessedConcept(ProcessedItem, ProcessedConceptBundle):
    """A processed JSKOS concept."""

    narrower: ProcessedJSKOSSet | None = None
    broader: ProcessedJSKOSSet | None = None
    related: ProcessedJSKOSSet | None = None
    previous: ProcessedJSKOSSet | None = None
    next: ProcessedJSKOSSet | None = None
    ancestors: ProcessedJSKOSSet | None = None
    in_scheme: list[ProcessedConceptScheme] | None = None
    top_concept_of: list[ProcessedConcept] | None = None
    mappings: list[ProcessedMapping] | None = None
    occurrences: list[ProcessedOccurrence] | None = None
    deprecated: bool | None = None


class Concept(ItemMixin, ConceptBundleMixin, SemanticallyProcessable[ProcessedConcept]):
    """Represents a concept in JSKOS."""

    narrower: JSKOSSet | None = None
    broader: JSKOSSet | None = None
    related: JSKOSSet | None = None
    previous: JSKOSSet | None = None
    next: JSKOSSet | None = None
    ancestors: JSKOSSet | None = None
    in_scheme: list[ConceptScheme] | None = Field(None, serialization_alias="inScheme")
    top_concept_of: list[ConceptScheme] | None = Field(None, serialization_alias="topConceptOf")
    mappings: list[Mapping] | None = None
    occurrences: list[Occurrence] | None = None
    deprecated: bool | None = None

    def process(self, converter: Converter) -> ProcessedConcept:
        """Process the concept."""
        return ProcessedConcept(
            **self._process_resource_helper(converter),
            **self._process_item_helper(converter),
            **self._process_concept_bundle_helper(converter),
            # TODO fill in item parts
            # TODO fill in concept bundle parts
            narrower=_process_jskos_set(self.narrower, converter),
            broader=_process_jskos_set(self.broader, converter),
            related=_process_jskos_set(self.related, converter),
            previous=_process_jskos_set(self.previous, converter),
            next=_process_jskos_set(self.next, converter),
            ancestors=_process_jskos_set(self.ancestors, converter),
            in_scheme=process_many(self.in_scheme, converter),
            top_concept_of=process_many(self.top_concept_of, converter),
            mappings=process_many(self.mappings, converter),
            occurrences=process_many(self.occurrences, converter),
            deprecated=self.deprecated,
        )


class ProcessedKOS(BaseModel):
    """A processed knowledge organization system."""

    id: str
    type: str
    title: LanguageMap
    description: LanguageMap
    concepts: list[ProcessedConcept] = Field(default_factory=list)


class KOS(BaseModel, SemanticallyProcessable[ProcessedKOS]):
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


def _process_jskos_set(s: JSKOSSet | None, converter: curies.Converter) -> ProcessedJSKOSSet | None:
    if s is None:
        return None
    return [e.process(converter) if e is not None else None for e in s]


def _process_dict[X](
    i: dict[AnyUrl, SemanticallyProcessable[X]] | None, converter: Converter
) -> dict[Reference, X] | None:
    if i is None:
        return None
    return {_parse_url(k, converter): v.process(converter) for k, v in i.items()}


def _safe_process[X](x: SemanticallyProcessable[X] | None, converter: Converter) -> X | None:
    if x is None:
        return None
    return x.process(converter)


def _parse_url(url: str | AnyUrl, converter: Converter) -> Reference:
    return converter.parse_uri(str(url), strict=True).to_pydantic()


def _parse_optional_urls(
    urls: Sequence[str | AnyUrl] | None, converter: Converter
) -> list[Reference] | None:
    if urls is None:
        return None
    return [_parse_url(url, converter) for url in urls]


def _parse_optional_url(url: str | AnyUrl | None, converter: Converter) -> Reference | None:
    if url is None:
        return None
    return _parse_url(url, converter)

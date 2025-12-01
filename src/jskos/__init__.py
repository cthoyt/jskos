"""A data model for JSKOS."""

from .api import KOS, Concept, Mapping, ProcessedConcept, ProcessedKOS, read

__all__ = [
    "KOS",
    "Concept",
    "Mapping",
    "ProcessedConcept",
    "ProcessedKOS",
    "read",
]

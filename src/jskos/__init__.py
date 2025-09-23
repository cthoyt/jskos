"""A data model for JSKOS."""

from .api import KOS, Concept, ProcessedConcept, ProcessedKOS, process, read

__all__ = [
    "KOS",
    "Concept",
    "ProcessedConcept",
    "ProcessedKOS",
    "process",
    "read",
]

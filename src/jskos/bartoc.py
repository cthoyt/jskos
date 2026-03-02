"""A client to BARTOC."""

from typing import ClassVar

from pydantic import Field

from jskos import JSKOSClient

from .api import Address, ConceptScheme, Item

BARTOC_BASE_URL = "https://bartoc.org/api/"

ConceptScheme.model_rebuild()


class BARTOCConceptScheme(ConceptScheme):
    """An JSKOS concept scheme, extended with BARTOC-only fields."""

    access: list[Item] | None = Field(None, alias="ACCESS")
    address: Address | None = Field(None, alias="ADDRESS")
    format: list[Item] | None = Field(None, alias="FORMAT")


BARTOCConceptScheme.model_rebuild()


class BARTOCClient(JSKOSClient):
    """A client for BARTOC."""

    concept_scheme_cls: ClassVar[type[ConceptScheme]] = BARTOCConceptScheme

    def __init__(self) -> None:
        """Initialize the BARTOC client."""
        super().__init__(BARTOC_BASE_URL)


def _demo() -> None:
    rows = []
    client = BARTOCClient()
    _v: BARTOCConceptScheme
    for _v in client.get_concept_schemes(part_of="http://bartoc.org/en/node/18961"):  # type:ignore
        if _v.preferred_label:
            label = (
                _v.preferred_label.get("en")
                or _v.preferred_label.get("und")
                or _v.preferred_label.get("de")
            )
        else:
            label = None
        rows.append(
            (_v.uri, [str(x.uri) for x in _v.format] if _v.format else None, label, _v.namespace)
        )


if __name__ == "__main__":
    _demo()

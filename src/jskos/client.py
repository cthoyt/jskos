"""A client to JSKOS API 2.1."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, TypeAlias

import requests
from pydantic import BaseModel

from .api import ConceptScheme

__all__ = [
    "JSKOSClient",
    "Status",
    "Validation",
]


class Status(BaseModel):
    """A status, see https://github.com/gbv/jskos-server#get-status."""

    # TODO implement based on https://gbv.github.io/jskos-server/status.schema.json


#:
Validation: TypeAlias = list[bool]


class JSKOSClient:
    """A client to JSKOS API 2.1."""

    concept_scheme_cls: ClassVar[type[ConceptScheme]] = ConceptScheme

    def __init__(self, base: str) -> None:
        """Initialize the client with the base URL."""
        self.base = base.rstrip("/")

    def _get(self, end: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = self.base + end
        res = requests.get(url, timeout=10, params=params)
        res.raise_for_status()
        return res

    def get_concept_schemes(
        self,
        *,
        uri: str | list[str] | None = None,
        type: str | None = None,
        languages: str | list[str] | None = None,
        subject: str | list[str] | None = None,
        license: str | list[str] | None = None,
        publisher: str | None = None,
        part_of: str | list[str] | None = None,
        sort: Literal["label", "notation", "created", "modified", "counter"] | None = None,
        order: Literal["asc", "desc"] | None = None,
        notation: str | list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ConceptScheme]:
        """Get concept schemes, see https://github.com/gbv/jskos-server#get-voc.

        If you want to get the NFDI4Objects Terminologies
        collection from BARTOC (https://bartoc.org/en/node/18961), then do

        .. code-block:: python

            from jskos.client import BARTOCClient

            client = BARTOCClient()
            vocabularies = client.get_vocabularies(part_of="https://bartoc.org/en/node/18961")
        """
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        _set(params, "type", type)
        _set(params, "uri", uri)
        _set(params, "languages", languages, sep=",")
        _set(params, "subject", subject)
        _set(params, "license", license)
        _set(params, "publisher", publisher)
        _set(params, "partOf", part_of)
        _set(params, "sort", sort)
        _set(params, "order", order)
        _set(params, "notation", notation)

        res = self._get("/voc", params=params)
        return [self.concept_scheme_cls.model_validate(record) for record in res.json()]


def _set(d: dict[str, Any], key: str, value: str | list[str] | None, sep: str = "|") -> None:
    if value is None:
        return
    elif isinstance(value, str):
        d[key] = value
    elif isinstance(value, list):
        d[key] = sep.join(value)
    else:
        raise TypeError

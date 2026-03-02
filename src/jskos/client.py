"""A client to JSKOS API 2.1."""

from __future__ import annotations

from typing import Any, ClassVar, Literal, TypeAlias, cast

import requests
from pydantic import BaseModel

from .api import ConceptScheme, Item

__all__ = [
    "JSKOSClient",
]


class Status(BaseModel):
    """A status, see https://github.com/gbv/jskos-server#get-status."""

    # TODO implement based on https://gbv.github.io/jskos-server/status.schema.json


#:
Validation: TypeAlias = list[bool]


class JSKOSClient:
    """A client to JSKOS API 2.1.

    .. seealso::

        https://github.com/gbv/jskos-server
    """

    #: The concept scheme class used. Override this
    #: if the JSKOS API extends the results. For example,
    #: BARTOC adds the ``FORMAT`` field in addition to the
    #: base fields.
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

        To get the NFDI4Objects Terminologies collection from BARTOC
        (https://bartoc.org/en/node/18961), do:

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

    def _post(
        self, end: str, params: dict[str, Any] | None = None, data: dict[str, Any] | None = None
    ) -> requests.Response:
        url = self.base + end
        res = requests.post(url, timeout=10, params=params, data=data)
        res.raise_for_status()
        return res

    def get_status(self) -> Status:
        """Get the JSKOS API status, see https://github.com/gbv/jskos-server#get-status."""
        raise NotImplementedError

    def get_check_auth(self):
        """Check whether a user is authorized, see https://github.com/gbv/jskos-server#get-checkauth."""
        raise NotImplementedError

    def get_validate(
        self,
        url: str,
        object_type: type[Item],
        unknown_fields: bool | None = None,
        known_schemes: bool | None = None,
    ) -> Validation:
        """Validate a JSKOS object via a GET request, see https://github.com/gbv/jskos-server#get-validate.

        :param url: The URL for the object to validate.
        :param object_type: See https://gbv.github.io/jskos/#object-types
        :param unknown_fields: If set to true, will disallow unknown fields inside
            objects
        :param known_schemes: If set to true, will allow concepts that are not in
            schemes in the database

        :returns: A validation object
        """
        params: dict[str, Any] = {
            "url": url,
            # FIXME this should probably get an explicit mapping
            "type": object_type.__name__.lower(),
        }
        if unknown_fields is not None:
            params["unknownFields"] = unknown_fields
        if known_schemes is not None:
            params["knownSchemes"] = known_schemes
        res = self._get("/validate", params=params)
        return cast(Validation, res.json())

    def post_validate(
        self,
        obj: Item,
        unknown_fields: bool | None = None,
        known_schemes: bool | None = None,
    ) -> Validation:
        """Validate a JSKOS object via a POST request, see https://github.com/gbv/jskos-server#post-validate.

        :param obj: A JSKOS object
        :param unknown_fields: If set to true, will disallow unknown fields inside
            objects
        :param known_schemes: If set to true, will allow concepts that are not in
            schemes in the database

        :returns: A validation object
        """
        params: dict[str, Any] = {
            "type": obj.__class__.__name__.lower(),
        }
        if unknown_fields is not None:
            params["unknownFields"] = unknown_fields
        if known_schemes is not None:
            params["knownSchemes"] = known_schemes
        res = self._post(
            "/validate", params=params, data=obj.model_dump(exclude_none=True, exclude_unset=True)
        )
        return cast(Validation, res.json())

    def get_data(self, uri: str) -> list[dict[str, Any]]:
        """Get data for entity, passed via URI, see https://github.com/gbv/jskos-server#get-data."""
        res = self._get("/data", params={"uri": uri})
        # TODO how to deal with typing?
        return cast(list[dict[str, Any]], res.json())

    def post_vocabulary(self):
        """Save a concept scheme or multiple concept schemes, see https://github.com/gbv/jskos-server#post-voc."""
        raise NotImplementedError

    def put_vocabulary(self):
        """Overwrite a concept scheme or multiple concept schemes, see https://github.com/gbv/jskos-server#put-voc."""
        raise NotImplementedError


def _set(d: dict[str, Any], key: str, value: str | list[str] | None, sep: str = "|") -> None:
    if value is None:
        return
    elif isinstance(value, str):
        d[key] = value
    elif isinstance(value, list):
        d[key] = sep.join(value)
    else:
        raise TypeError

"""A client to JSKOS API 2.1."""

from __future__ import annotations

from typing import Any, cast

import requests

from jskos import ConceptScheme

__all__ = [
    "BARTOCClient",
    "JSKOSClient",
]


class JSKOSClient:
    """A client to JSKOS API 2.1."""

    def __init__(self, base: str) -> None:
        """Initialize the client with the base URL."""
        self.base = base.rstrip("/")

    def _get(self, end: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = self.base + end
        res = requests.get(url, timeout=10, params=params)
        res.raise_for_status()
        return res

    def get_status(self):
        """Get the JSKOS API status, see https://github.com/gbv/jskos-server#get-status."""
        raise NotImplementedError

    def get_check_auth(self):
        """Check whether a user is authorizeed, see https://github.com/gbv/jskos-server#get-checkauth."""
        raise NotImplementedError

    def get_validate(self):
        """Validate a JSKOS object via a GET request, see https://github.com/gbv/jskos-server#get-validate."""
        raise NotImplementedError

    def post_validate(self):
        """Validate a JSKOS object via a POST request, see https://github.com/gbv/jskos-server#post-validate."""
        raise NotImplementedError

    def get_data(self, uri: str) -> list[dict[str, Any]]:
        """Get data for entity, passed via URI, see https://github.com/gbv/jskos-server#get-data."""
        res = self._get("/data", params={"uri": uri})
        # TODO how to deal with typing?
        return cast(list[dict[str, Any]], res.json())

    def get_vocabularies(self, *, limit: int | None = None) -> list[ConceptScheme]:
        """Get concept schemes, see https://github.com/gbv/jskos-server#get-voc."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        res = self._get("/voc", params=params)
        return [ConceptScheme.model_validate(record) for record in res.json()]

    def post_vocabulary(self):
        """Save a concept scheme or multiple concept schemes, see https://github.com/gbv/jskos-server#post-voc."""
        raise NotImplementedError

    def put_vocabulary(self):
        """Overwrite a concept scheme or multiple concept schemes, see https://github.com/gbv/jskos-server#put-voc."""
        raise NotImplementedError


# Implement the API at https://bartoc.org/api/
# this is a subset of JSKOS API, so maybe this


class BARTOCClient(JSKOSClient):
    """A client for BARTOC."""

    def __init__(self) -> None:
        """Initialize the BARTOC client."""
        super().__init__("https://bartoc.org/api/")

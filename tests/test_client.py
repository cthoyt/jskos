"""Test the JSKOS API client."""

import unittest
from typing import ClassVar

from jskos import JSKOSClient

BARTOC_BASE_URL = "https://bartoc.org/api/"


class TestJSKOSClient(unittest.TestCase):
    """Test the JSKOS API client."""

    client: ClassVar[JSKOSClient]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case."""
        cls.client = JSKOSClient(BARTOC_BASE_URL)

    def test_get_collection(self) -> None:
        """Test getting a collection from BARTOC."""
        vocabularies = self.client.get_concept_schemes(part_of="http://bartoc.org/en/node/18961")
        self.assertLessEqual(80, len(vocabularies))

        # on March 2nd, 2026, there were 85 unique records in the
        # NFDI4Objects collection. this tests for a subset of them
        uris = {str(v.uri) for v in vocabularies}
        self.assertLessEqual(
            {
                "http://bartoc.org/en/node/18653",  # LIDO Terminology Actor Type
                "http://bartoc.org/en/node/2021",  # ORCiD
                "http://bartoc.org/en/node/459",  # Iconclass
            },
            uris,
        )

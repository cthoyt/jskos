"""Test the JSKOS API client."""

import unittest
from typing import ClassVar

from jskos import ConceptScheme, JSKOSClient


class TestJSKOSClient(unittest.TestCase):
    """Test the JSKOS API client."""

    client: ClassVar[JSKOSClient]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case."""
        cls.client = JSKOSClient("https://coli-conc.gbv.de/api/")

    def test_voc(self) -> None:
        """Test getting all concept schemes."""
        results = self.client.get_vocabularies(limit=1)
        self.assertEqual(1, len(results))
        self.assertIsInstance(results[0], ConceptScheme)
        self.assertEqual("http://dewey.info/scheme/edition/e23/", results[0].uri)

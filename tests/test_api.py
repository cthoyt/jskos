"""Test the API."""

import unittest

import curies

import jskos


class TestJSKOS(unittest.TestCase):
    """Test the API."""

    def test_end_to_end(self) -> None:
        """Test parsing and processing JSKOS."""
        url = "https://oer-repo.uibk.ac.at/w3id.org/vocabs/oefos2012/schema.json"
        kos = jskos.read(url)

        converter = curies.Converter.from_prefix_map(
            {
                "oefos2012": "https://w3id.org/oerbase/vocabs/oefos2012/",
            }
        )
        processed_kos = jskos.process(kos, converter)
        self.assertIsNotNone(processed_kos)

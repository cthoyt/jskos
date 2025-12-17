"""Test the API."""

import unittest

import curies
from curies import Reference

import jskos
from jskos import Concept

converter = curies.Converter.from_prefix_map(
    {
        "wikidata": "http://www.wikidata.org/entity/",
    }
)


class TestExamples(unittest.TestCase):
    """Test examples from the documentation."""

    def test_18(self) -> None:
        """Test example 18 from https://gbv.github.io/jskos/#lst-qualified-literal."""
        record = {
            "uri": "http://www.wikidata.org/entity/Q406",
            "qualifiedLiterals": {
                "http://www.w3.org/2008/05/skos-xl#prefLabel": [
                    {
                        "type": ["http://www.w3.org/2008/05/skos-xl#Label"],
                        "literal": {"string": "İstanbul", "language": "tr"},
                        "rank": "preferred",
                    },
                    {
                        "type": ["http://www.w3.org/2008/05/skos-xl#Label"],
                        "literal": {"string": "Constantinople", "language": "en"},
                        "endDate": "1930",
                    },
                ],
                "https://www.wikidata.org/wiki/Property:P395": [{"literal": {"string": "34"}}],
            },
        }
        concept = Concept.model_validate(record)
        processed_concept = concept.process(converter)

        self.assertEqual(
            Reference(prefix="wikidata", identifier="Q406"), processed_concept.reference
        )


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
        processed_kos = kos.process(converter)
        self.assertIsNotNone(processed_kos)

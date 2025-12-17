"""Test the API."""

import unittest

import curies
from curies import Reference

import jskos
from jskos.api import Concept, Occurrence

converter = curies.Converter.from_prefix_map(
    {
        "wikidata": "http://www.wikidata.org/entity/",
    }
)


class TestExamples(unittest.TestCase):
    """Test examples from the documentation."""

    def test_9(self) -> None:
        """Test example 9 from https://gbv.github.io/jskos/#lst-ex2."""
        record = {
            "database": {"uri": "http://uri.gbv.de/database/opac-de-627"},
            "schemes": [{"uri": "http://dewey.info/scheme/ddc/"}],
            "template": "https://opac.k10plus.de/DB=2.299/CMD?ACT=SRCHA&IKT=3011&NOABS=Y&TRM={notation}",
            "separator": "+and+",
        }
        occurrence = Occurrence.model_validate(record)
        self.assertIsNotNone(occurrence)

        occurrences = [
            {
                "database": {"uri": "http://uri.gbv.de/database/gvk"},
                "memberSet": [
                    {
                        "uri": "http://uri.gbv.de/terminology/bk/08.22",
                        "prefLabel": {"de": "Mittelalterliche Philosophie"},
                    }
                ],
                "count": 3657,
                "modified": "2017-11-22",
                "url": "https://gso.gbv.de/DB=2.1/CMD?ACT=SRCHA&IKT=1016&SRT=YOP&TRM=bkl+08.22",
            },
            {
                "database": {"uri": "http://uri.gbv.de/database/gvk"},
                "memberSet": [
                    {
                        "uri": "http://dewey.info/class/610/e23/",
                        "prefLabel": {"en": "Medicine & health"},
                    }
                ],
                "count": 144611,
                "modified": "2017-11-22",
                "url": "https://gso.gbv.de/DB=2.1/CMD?ACT=SRCHA&IKT=1016&SRT=YOP&TRM=ddc+610",
            },
            {
                "database": {"uri": "http://uri.gbv.de/database/gvk"},
                "memberSet": [
                    {"uri": "http://uri.gbv.de/terminology/bk/08.22"},
                    {"uri": "http://dewey.info/class/610/e23/"},
                ],
                "count": 2,
                "modified": "2017-11-22",
                "url": "https://gso.gbv.de/DB=2.1/CMD?ACT=SRCHA&IKT=1016&SRT=YOP&TRM=bkl+08.22+ddc+610",
            },
        ]
        concept = Concept.model_validate({"occurrences": occurrences})
        self.assertIsNotNone(concept)
        self.assertIsNotNone(concept.occurrences)
        self.assertEqual(3, len(concept.occurrences))

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

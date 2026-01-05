"""Tests de rocinante/tripulacio.py. Ús: python tests/test_tripulacio.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rocinante.tripulacio import capita, es_a_bord, noms  # noqa: E402


class TestTripulacio(unittest.TestCase):
    def test_el_capita_es_holden(self):
        self.assertEqual(capita()["nom"], "James Holden")

    def test_la_tripulacio_original_hi_es(self):
        for nom in ("James Holden", "Naomi Nagata", "Amos Burton", "Alex Kamal"):
            self.assertIn(nom, noms())

    def test_es_a_bord(self):
        self.assertTrue(es_a_bord("Amos Burton"))
        self.assertFalse(es_a_bord("Joe Miller"))


if __name__ == "__main__":
    unittest.main()

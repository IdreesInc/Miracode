"""Check that source-generated Regular and Bold form a consistent family.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import unittest
from fontTools.ttLib import TTFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('regular')
parser.add_argument('bold')
args = parser.parse_args()
regular, bold = TTFont(args.regular), TTFont(args.bold)

class StyleTests(unittest.TestCase):
    def test_same_coverage_and_advances(self):
        self.assertEqual(regular.getBestCmap(), bold.getBestCmap())
        self.assertEqual(regular.getGlyphOrder(), bold.getGlyphOrder())
        self.assertEqual({n: m[0] for n, m in regular['hmtx'].metrics.items()},
                         {n: m[0] for n, m in bold['hmtx'].metrics.items()})

    def test_same_ligatures(self):
        self.assertEqual(regular.getTableData('GSUB'), bold.getTableData('GSUB'))

    def test_same_family_metrics(self):
        self.assertEqual(regular['name'].getDebugName(1), bold['name'].getDebugName(1))
        self.assertNotEqual(regular['name'].getDebugName(6), bold['name'].getDebugName(6))
        for table, fields in [('hhea', ['ascent', 'descent', 'lineGap']),
                              ('OS/2', ['sTypoAscender', 'sTypoDescender', 'sTypoLineGap',
                                        'usWinAscent', 'usWinDescent'])]:
            for field in fields:
                with self.subTest(table=table, field=field):
                    self.assertEqual(getattr(regular[table], field), getattr(bold[table], field))

    def test_weight_expands_strokes_evenly(self):
        # The 120-unit stroke increase must expand each side by 60 units.
        # Post-generation emboldening previously dropped O/o/t by 112 units
        # relative to A/a/s/e. Check the source geometry at that actual seam.
        for char in 'AEOaenostp':
            name = regular.getBestCmap()[ord(char)]
            a, b = regular['glyf'][name], bold['glyf'][name]
            with self.subTest(character=char):
                self.assertEqual(b.yMin, a.yMin - 60)
                self.assertEqual(b.yMax, a.yMax + 60)

unittest.main(argv=['check_styles.py'])

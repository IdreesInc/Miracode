"""Check the generated font, including accents defined through references.

Run after generating dist/Miracode.ttf. --baseline compares unchanged glyphs
and advances with an earlier source build rather than another release.
SPDX-License-Identifier: GPL-3.0-or-later
"""
import argparse
import json
from pathlib import Path
import unittest
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('font', type=Path)
parser.add_argument('--baseline', type=Path)
parser.add_argument('--weight', type=int, choices=(400, 700), default=400)
args = parser.parse_args()
font = TTFont(args.font)
cmap = font.getBestCmap()
root = Path(__file__).resolve().parents[1]
characters = json.loads((root / 'src/characters.json').read_text())
accent_references = [char for char in characters if char.get('reference') and char.get('diacritic')]

def outline(font, code):
    glyphs = font.getGlyphSet()
    pen = DecomposingRecordingPen(glyphs)
    glyphs[font.getBestCmap()[code]].draw(pen)
    return pen.value

class GeneratedFontTests(unittest.TestCase):
    def test_nondescending_letters_share_a_bottom(self):
        letters = 'AEO\u00c5\u00c4\u00d6aenost\u00e5\u00e4\u00f6'
        self.assertEqual(len({font['glyf'][cmap[ord(c)]].yMin for c in letters}), 1)

    def test_lowercase_letters_share_an_x_height(self):
        self.assertEqual(len({font['glyf'][cmap[ord(c)]].yMax for c in 'aenosp'}), 1)

    def test_style_metadata(self):
        bold = args.weight == 700
        self.assertEqual(font['OS/2'].usWeightClass, args.weight)
        self.assertEqual(bool(font['OS/2'].fsSelection & 32), bold)
        self.assertEqual(bool(font['OS/2'].fsSelection & 64), not bold)
        self.assertEqual(font['head'].macStyle & 3, 1 if bold else 0)
        self.assertEqual(font['name'].getDebugName(2), 'Bold' if bold else 'Regular')

    def test_explicit_accents_are_present(self):
        for char in accent_references:
            with self.subTest(character=char['character']):
                self.assertNotEqual(outline(font, char['codepoint']), outline(font, char['reference']))

    def test_capital_ring_is_above_base(self):
        self.assertGreater(font['glyf'][cmap[197]].yMax, font['glyf'][cmap[65]].yMax)

    def test_em_dash_has_space_on_both_sides(self):
        name = cmap[0x2014]
        glyph = font['glyf'][name]
        advance = font['hmtx'][name][0]
        self.assertEqual(advance, font['hmtx'][cmap[ord('s')]][0])
        self.assertGreaterEqual(glyph.xMin, 128)
        self.assertGreaterEqual(advance - glyph.xMax, 128)
        # The user's sample: the dash must not touch either adjacent outline.
        self.assertGreater(advance + glyph.xMin - font['glyf'][cmap[ord('s')]].xMax, 0)
        self.assertGreater(advance + font['glyf'][cmap[ord('t')]].xMin - glyph.xMax, 0)

    def test_line_metrics_include_every_outline(self):
        for name in font.getGlyphOrder():
            glyph = font['glyf'][name]
            glyph.recalcBounds(font['glyf'])
            if glyph.numberOfContours:
                with self.subTest(glyph=name):
                    self.assertGreaterEqual(font['OS/2'].sTypoAscender, glyph.yMax)
                    self.assertLessEqual(font['OS/2'].sTypoDescender, glyph.yMin)

    def test_line_metrics_agree(self):
        os2, hhea = font['OS/2'], font['hhea']
        self.assertEqual((hhea.ascent, hhea.descent, hhea.lineGap),
                         (os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap))
        self.assertEqual((os2.usWinAscent, -os2.usWinDescent), (hhea.ascent, hhea.descent))
        self.assertEqual(hhea.lineGap, 0)
        self.assertTrue(os2.fsSelection & 128)

    def test_monospace_metadata_and_advances(self):
        self.assertEqual(font['head'].unitsPerEm, 2304)
        self.assertEqual({font['hmtx'][cmap[code]][0] for code in range(32, 127)}, {1536})
        self.assertEqual(font['post'].isFixedPitch, 1)
        self.assertEqual(font['OS/2'].panose.bProportion, 9)

    @unittest.skipUnless(args.baseline, 'Supply --baseline for comparisons')
    def test_coverage_and_all_advances_preserved(self):
        baseline = TTFont(args.baseline)
        old = baseline.getBestCmap()
        self.assertEqual(set(cmap), set(old))
        self.assertEqual({code: font['hmtx'][name][0] for code, name in cmap.items()},
                         {code: baseline['hmtx'][name][0] for code, name in old.items()})

    @unittest.skipUnless(args.baseline, 'Supply --baseline for comparisons')
    def test_unaffected_outlines_preserved(self):
        baseline = TTFont(args.baseline)
        repaired = {char['codepoint'] for char in accent_references} | {0x2014, 0xC4, 0xD6, 0xE5, 0x2022}
        for code in cmap:
            if code not in repaired:
                with self.subTest(codepoint=hex(code)):
                    self.assertEqual(outline(font, code), outline(baseline, code))

unittest.main(argv=['check_font.py'])

"""Check optical spacing without shrinking the upper A opening.

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

def contours(font, code):
    glyph = font['glyf'][font.getBestCmap()[code]]
    coordinates, ends, _ = glyph.getCoordinates(font['glyf'])
    result, start = [], 0
    for end in ends:
        points = list(coordinates[start:end + 1])
        area = sum(x * v - u * y for (x, y), (u, v) in zip(points, points[1:] + points[:1])) / 2
        xs, ys = zip(*points)
        result.append({'points': points, 'area': area, 'bounds': (min(xs), min(ys), max(xs), max(ys))})
        start = end + 1
    return result

def upper_opening(font, code):
    return min((c for c in contours(font, code) if c['area'] > 0), key=lambda c: c['bounds'][1])

class AccentSpacingTests(unittest.TestCase):
    def test_capital_ring_is_separate_from_body(self):
        for font in [regular, bold]:
            shapes = sorted((c for c in contours(font, 0xC5) if c['area'] < 0), key=lambda c: c['bounds'][1])
            self.assertEqual(len(shapes), 2, 'Ring and A must have separate outer contours')
            self.assertGreaterEqual(shapes[1]['bounds'][1] - shapes[0]['bounds'][3], 128)

    def test_bold_ring_hole_is_readable(self):
        for code in [0xC5, 0xE5]:
            ring = max((c for c in contours(bold, code) if c['area'] > 0), key=lambda c: c['bounds'][1])
            self.assertGreaterEqual(ring['bounds'][2] - ring['bounds'][0], 384)
            self.assertGreaterEqual(ring['bounds'][3] - ring['bounds'][1], 384)

    def test_capital_accent_tops_align(self):
        tops = []
        for font in [regular, bold]:
            cmap = font.getBestCmap()
            tops += [font['glyf'][cmap[code]].yMax for code in [0xC5, 0xC4, 0xD6]]
        self.assertEqual(len(set(tops)), 1)

    def test_upper_opening_is_preserved(self):
        expected = upper_opening(regular, 65)
        for font in [regular, bold]:
            for code in [65, 0xC5, 0xC4]:
                actual = upper_opening(font, code)
                with self.subTest(weight=font['OS/2'].usWeightClass, code=hex(code)):
                    self.assertEqual(actual['area'], expected['area'])
                    self.assertEqual(actual['bounds'][2] - actual['bounds'][0], expected['bounds'][2] - expected['bounds'][0])
                    self.assertEqual(actual['bounds'][3] - actual['bounds'][1], expected['bounds'][3] - expected['bounds'][1])

    def test_capital_a_bodies_are_identical(self):
        def canonical(points):
            return min(tuple(points[index:] + points[:index]) for index in range(len(points)))
        for font in [regular, bold]:
            a = contours(font, 65)
            top = max(c['bounds'][3] for c in a)
            expected = sorted(canonical(c['points']) for c in a)
            for code in [0xC5, 0xC4]:
                body = [c for c in contours(font, code) if c['bounds'][1] < top]
                with self.subTest(weight=font['OS/2'].usWeightClass, code=hex(code)):
                    self.assertEqual(sorted(canonical(c['points']) for c in body), expected)

    def test_regular_ring_is_lighter_than_bold(self):
        for code in [0xC5, 0xE5]:
            holes = [max((c for c in contours(font, code) if c['area'] > 0), key=lambda c: c['bounds'][1])
                     for font in [regular, bold]]
            self.assertGreater(holes[0]['area'], holes[1]['area'])

    def test_bullet_is_centered_on_capitals(self):
        for font in [regular, bold]:
            cmap = font.getBestCmap()
            a, bullet = [font['glyf'][cmap[code]] for code in [65, 0x2022]]
            self.assertEqual(bullet.yMin + bullet.yMax, a.yMin + a.yMax)

unittest.main(argv=['check_accent_spacing.py'])

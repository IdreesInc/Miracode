"""Finalize text metrics without changing units, outlines or glyph advances.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import math
from fontTools.ttLib import TTFont

def finalizeFont(path):
    font = TTFont(path, recalcTimestamp=False)
    # Round outward to a quarter of the source design's 256-unit pixel.
    ascent = math.ceil(font['head'].yMax / 64) * 64
    descent = math.ceil(-font['head'].yMin / 64) * 64
    os2 = font['OS/2']
    os2.version = max(os2.version, 4)
    os2.sTypoAscender = font['hhea'].ascent = os2.usWinAscent = ascent
    os2.sTypoDescender = font['hhea'].descent = -descent
    os2.usWinDescent = descent
    os2.sTypoLineGap = font['hhea'].lineGap = 0
    os2.fsSelection |= 128  # USE_TYPO_METRICS
    os2.panose.bProportion = 9  # Monospaced
    # Ligatures span multiple cells; this does not make the text proportional.
    font['post'].isFixedPitch = 1
    font.save(path)
    font.close()

"""Optical source designs for Swedish accents at small text sizes.

SPDX-License-Identifier: GPL-3.0-or-later
"""
import fontforge

def drawSwedishAccent(glyph, code, characters, diacritics, draw, bold=False):
    capital = code != 0xE5
    ring = code in (0xC5, 0xE5)
    source = fontforge.font()
    try:
        def component(name, data, stroke):
            part = source.createChar(-1, name)
            draw(data, part, part.glyphPen(), stroke=stroke)
            return part

        base_code = {65: 65, 0xC5: 65, 0xC4: 65, 0xD6: 79, 0xE5: 97}[code]
        base = characters[base_code]
        body = component('body', base, 312 if bold else 192)
        opening = None
        if base_code == 65 and bold:
            regular = component('regular', base, 192)
            opening = next(c.dup() for c in regular.foreground if not c.isClockwise())
        layer = fontforge.layer()
        for contour in body.foreground:
            contour = opening.dup() if opening is not None and not contour.isClockwise() else contour.dup()
            layer += contour

        if code == 65:
            glyph.foreground = layer
            glyph.round()
            return

        accent_name = 'ring_above' if ring else 'diaeresis'
        # Start with the original capital mark positions before top alignment;
        # lower the small ring by half a source pixel.
        data = {'pixels': diacritics[accent_name]['pixels'],
                'descent': -7 if capital and ring else (-5.5 if ring else -8)}
        accent = component('accent', data, 192 if ring else (312 if bold else 192))
        # Align capital accent tops, leaving room above the full-height A.
        shift = 2912 - accent.boundingBox()[3] if capital else 0
        for contour in accent.foreground:
            contour = contour.dup()
            if ring and not contour.isClockwise():
                # Keep the accepted outer ring and bold hole. Regular needs
                # a larger hole so its ring is visibly lighter than Bold.
                center_y = 2432 if capital else 2048
                scale = (384 if bold else 448) / 240
                for point in contour:
                    point.x = 640 + (point.x - 640) * scale
                    point.y = center_y + (point.y - center_y) * scale
            for point in contour:
                point.y += shift
            layer += contour
        glyph.foreground = layer
        glyph.round()
    finally:
        source.close()

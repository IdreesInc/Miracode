# Monocraft Vector
# Copyright (C) 2022-2023 Idrees Hassan
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import fontforge
import json
import math
from generate_diacritics import generateDiacritics
from generate_examples import generateExamples
from polygonizer import PixelImage, generatePolygons
from generate_continuous_ligatures import generate_continuous_ligatures 

PIXEL_SIZE = 512

characters = json.load(open("./characters.json"))
diacritics = json.load(open("./diacritics.json"))
ligatures = json.load(open("./ligatures.json"))
# ligatures += generate_continuous_ligatures("./continuous_ligatures.json")

characters = generateDiacritics(characters, diacritics)
charactersByCodepoint = {}

def generateFont():
	monocraft = fontforge.font()
	monocraft.fontname = "Monocraft-Vector"
	monocraft.familyname = "Monocraft Vector"
	monocraft.fullname = "Monocraft Vector"
	monocraft.copyright = "Idrees Hassan, https://github.com/IdreesInc/Monocraft-Vector"
	monocraft.encoding = "UnicodeFull"
	monocraft.version = "1.0"
	monocraft.weight = "Regular"
	monocraft.ascent = PIXEL_SIZE * 8
	monocraft.descent = PIXEL_SIZE
	monocraft.em = PIXEL_SIZE * 9
	monocraft.upos = -PIXEL_SIZE # Underline position
	monocraft.addLookup("ligatures", "gsub_ligature", (), (("liga",(("dflt",("dflt")),("latn",("dflt")))),))
	monocraft.addLookupSubtable("ligatures", "ligatures-subtable")

	count = 0
	for character in characters:
		count += 1
		# if count > 40:
		# 	break
		charactersByCodepoint[character["codepoint"]] = character
		monocraft.createChar(character["codepoint"], character["name"])
		pen = monocraft[character["name"]].glyphPen()
		top = 0
		drawn = character

		drawCharacter(character, monocraft[character["name"]], pen)

		monocraft[character["name"]].width = PIXEL_SIZE * 6
	print(f"Generated {len(characters)} characters")

	outputDir = "../dist/"
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)

	monocraft.generate(outputDir + "Monocraft-Vector-no-ligatures.ttf")
	for ligature in ligatures:
		lig = monocraft.createChar(-1, ligature["name"])
		pen = monocraft[ligature["name"]].glyphPen()
		drawCharacter(ligature, lig, pen)
		monocraft[ligature["name"]].width = PIXEL_SIZE * len(ligature["sequence"]) * 6
		lig.addPosSub("ligatures-subtable", tuple(map(lambda codepoint: charactersByCodepoint[codepoint]["name"], ligature["sequence"])))
	print(f"Generated {len(ligatures)} ligatures")

	monocraft.generate(outputDir + "Monocraft-Vector.ttf")
	monocraft.generate(outputDir + "Monocraft-Vector.otf")

def get(pixel, row , col):
	if row < 0 or col < 0:
		return 0
	if row >= len(pixel) or col >= len(pixel[0]):
		return 0
	return pixel[row][col]

def generateEdges(character):
	if not character.get("pixels"):
		return
	pixels = character["pixels"]
	edges = []

	drawDiagonals = True

	numOfCols = len(pixels[0])
	numOfRows = len(pixels)
	for row in range(numOfRows):
		for col in range(numOfCols):
			if pixels[row][col] == 1:
				# Check if there is a pixel to the right
				if col < numOfCols - 1 and pixels[row][col + 1] == 1:
					if drawDiagonals and get(pixels, row + 1, col) == 1 and get(pixels, row - 1, col + 2) == 1:
						# Disallowed (W)
						# 1 0 1
						# X 1 0
						# 1 0 0
						pass
					elif drawDiagonals and get(pixels, row - 1, col - 1) == 1 and get(pixels, row + 1, col + 1) == 1:
						# Disallowed
						#  1 0 1
						#  0 X 1
						#  0 0 1
						pass
					else:
						edges.append(((col, row), (col + 1, row)))
				# Check if there is a pixel below
				if row < numOfRows - 1 and pixels[row + 1][col] == 1:
					edges.append(((col, row), (col, row + 1)))
				if not drawDiagonals:
					continue
				# Check if there is a pixel to the bottom right
				if col < numOfCols - 1 and row < numOfRows - 1 and pixels[row + 1][col + 1] == 1:
					if not ignoreDiagonal(pixels, row, col, False):
						edges.append(((col, row), (col + 1, row + 1)))
				# Check if there is a pixel to the bottom left
				if col > 0 and row < numOfRows - 1 and pixels[row + 1][col - 1] == 1:
					if not ignoreDiagonal(pixels, row, col, True):
						edges.append(((col, row), (col - 1, row + 1)))
	return edges

def ignoreDiagonal(pixels, row , col, flipped):
	colMod = -1 if flipped else 1
	if get(pixels, row + 1, col) == 1 and (get(pixels, row - 1, col - colMod) != 1 or get(pixels, row + 2, col) == 1):
		# Disallowed (H)
		# X 0 0 
		# 1 1 1
		# 1 0 0
		# Disallowed (f)
		# 1 0 0 
		# 0 X 0
		# 1 1 1
		# 0 1 0
		# Allowed (z)
		# 1 0 0
		# 0 X 0
		# 1 1 1
		return True
	elif get(pixels, row, col + colMod) == 1 and get(pixels, row + 2, col + colMod) == 1 and get(pixels, row - 1, col) != 0:
		# Disallowed (l)
		# 0 X 1
		# 0 0 1
		# 0 0 1
		# Allowed (W)
		# 1 0 1
		# 0 X 1
		# 0 0 1
		return True
	elif get(pixels, row - 1, col - colMod) != 1 and get(pixels, row + 2, col + 2 * colMod) != 1 and get(pixels, row, col + colMod) == 1:
		# Disallowed (H)
		# 0 0 1
		# 1 X 1
		# 0 0 1
		# Allowed (W)
		# 1 0 1
		# 0 X 1
		# 0 0 1
		# Allowed (z)
		# X 1 1
		# 0 1 0
		# 0 0 1
		return True
	return False

def countNeighbors(pixels, row, col):
	count = 0
	if get(pixels, row - 1, col) == 1:
		count += 1
	if get(pixels, row, col - 1) == 1:
		count += 1
	if get(pixels, row + 1, col) == 1:
		count += 1
	if get(pixels, row, col + 1) == 1:
		count += 1
	if get(pixels, row - 1, col - 1) == 1:
		count += 1
	if get(pixels, row - 1, col + 1) == 1:
		count += 1
	if get(pixels, row + 1, col - 1) == 1:
		count += 1
	if get(pixels, row + 1, col + 1) == 1:
		count += 1
	return count

def countEnds(pixels, row, col):
	count = 0
	if get(pixels, row - 1, col) != get(pixels, row + 1, col):
		count += 1
	if get(pixels, row, col - 1) != get(pixels, row, col + 1):
		count += 1
	if get(pixels, row - 1, col - 1) != get(pixels, row + 1, col + 1):
		count += 1
	if get(pixels, row - 1, col + 1) != get(pixels, row + 1, col - 1):
		count += 1
	return count

def drawCharacter(character, glyph, pen):
	# print("Drawing character", character["name"])
	if not character.get("pixels"):
		# print(f"Character {character['name']} has no pixels")
		return
	edges = generateEdges(character)

	edgesPerPoint = {}
	for edge in edges:
		if edge[0] not in edgesPerPoint:
			edgesPerPoint[edge[0]] = []
		edgesPerPoint[edge[0]].append(edge)
		if edge[1] not in edgesPerPoint:
			edgesPerPoint[edge[1]] = []
		edgesPerPoint[edge[1]].append(edge)

	descent = 0
	if "descent" in character:
		descent = character["descent"]
	top = (len(character["pixels"]) - descent) * PIXEL_SIZE

	# Draw the dots
	pixels = character["pixels"]
	for row in range(len(pixels)):
		for col in range(len(pixels[0])):
			if pixels[row][col] == 1:
				if countNeighbors(pixels, row, col) == 0:
					pen.moveTo(col * PIXEL_SIZE + PIXEL_SIZE / 2, top - row * PIXEL_SIZE + PIXEL_SIZE / 2)
					pen.endPath()

	STROKE = 400
	HALF = STROKE / 2
	SQRT_TWO = 1.41421

	# Expand the stroke for the dots
	glyph.stroke("circular", STROKE * 1.2)

	# Draw the paths
	for edge in edges:
		startX = edge[0][0] * PIXEL_SIZE + PIXEL_SIZE / 2
		startY = top - (edge[0][1] * PIXEL_SIZE - PIXEL_SIZE / 2)
		endX = edge[1][0] * PIXEL_SIZE + PIXEL_SIZE / 2
		endY = top - (edge[1][1] * PIXEL_SIZE - PIXEL_SIZE / 2)
		if startX == endX:
			# Down
			pen.moveTo(startX - HALF, startY)
			pen.lineTo(startX + HALF, startY)
			pen.lineTo(startX + HALF, endY)
			pen.lineTo(startX - HALF, endY)
			pen.closePath()
		elif startY == endY:
			# Right
			pen.moveTo(startX, startY - HALF)
			pen.lineTo(startX, startY + HALF)
			pen.lineTo(endX, startY + HALF)
			pen.lineTo(endX, startY - HALF)
			pen.closePath()
		elif startX < endX:
			# Diagonal right
			pen.moveTo(startX - HALF / SQRT_TWO, startY - HALF / SQRT_TWO)
			pen.lineTo(startX + HALF / SQRT_TWO, startY + HALF / SQRT_TWO)
			pen.lineTo(endX + HALF / SQRT_TWO, endY + HALF / SQRT_TWO)
			pen.lineTo(endX - HALF / SQRT_TWO, endY - HALF / SQRT_TWO)
			pen.closePath()
		else:
			# Diagonal left
			pen.moveTo(startX - HALF / SQRT_TWO, startY + HALF / SQRT_TWO)
			pen.lineTo(startX + HALF / SQRT_TWO, startY - HALF / SQRT_TWO)
			pen.lineTo(endX + HALF / SQRT_TWO, endY - HALF / SQRT_TWO)
			pen.lineTo(endX - HALF / SQRT_TWO, endY + HALF / SQRT_TWO)
			pen.closePath()

	# Merge intersecting paths
	glyph.simplify()

def interp(p1, p2, t):
	return (p1[0] + (p2[0] - p1[0]) * t, p1[1] + (p2[1] - p1[1]) * t)

generateFont()
generateExamples(characters, ligatures, charactersByCodepoint)

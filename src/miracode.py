# Miracode
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

PIXEL_SIZE = 256
SQRT_TWO = math.sqrt(2)

characters = json.load(open("./characters.json"))
diacritics = json.load(open("./diacritics.json"))
ligatures = json.load(open("./ligatures.json"))
# ligatures += generate_continuous_ligatures("./continuous_ligatures.json")

characters = generateDiacritics(characters, diacritics)
charactersByCodepoint = {}

def generateFont():
	miracode = fontforge.font()
	miracode.fontname = "Miracode"
	miracode.familyname = "Miracode"
	miracode.fullname = "Miracode"
	miracode.copyright = "Idrees Hassan, https://github.com/IdreesInc/Miracode"
	miracode.encoding = "UnicodeFull"
	miracode.version = "1.0"
	miracode.weight = "Regular"
	miracode.ascent = PIXEL_SIZE * 8
	miracode.descent = PIXEL_SIZE
	miracode.em = PIXEL_SIZE * 9
	miracode.upos = -PIXEL_SIZE # Underline position
	miracode.addLookup("ligatures", "gsub_ligature", (), (("liga",(("dflt",("dflt")),("latn",("dflt")))),))
	miracode.addLookupSubtable("ligatures", "ligatures-subtable")

	for character in characters:
		charactersByCodepoint[character["codepoint"]] = character
		miracode.createChar(character["codepoint"], character["name"])
		pen = miracode[character["name"]].glyphPen()
		top = 0
		drawn = character

		drawCharacter(character, miracode[character["name"]], pen)

		miracode[character["name"]].width = PIXEL_SIZE * 6
	print(f"Generated {len(characters)} characters")

	outputDir = "../dist/"
	if not os.path.exists(outputDir):
		os.makedirs(outputDir)

	# Generate the font without ligatures
	# print("Generating TTF font without ligatures...")
	# miracode.generate(outputDir + "Miracode-no-ligatures.ttf")

	for ligature in ligatures:
		if ligature.get("pixels"):
			# Basic ligature
			lig = miracode.createChar(-1, ligature["name"])
			pen = miracode[ligature["name"]].glyphPen()
			drawCharacter(ligature, lig, pen)
			miracode[ligature["name"]].width = PIXEL_SIZE * len(ligature["sequence"]) * 6
		elif ligature.get("chain"):
			# Chain ligature
			chain = ligature["chain"]
			lig = miracode.createChar(-1, ligature["name"])
			pen = miracode[ligature["name"]].glyphPen()
			xOffset = 0
			print("Lig: ", ligature["name"])
			for character in chain:
				if character.get("pixels"):
					xOffset = drawCharacter(character, lig, pen, xOffset)
				elif character.get("reference"):
					linkedCharacter = charactersByCodepoint[character["reference"]]
					xOffset = drawCharacter(linkedCharacter, lig, pen, xOffset)
				else:
					print(f"Unexpected character in ligature {ligature['name']}: {character}")
				xOffset += PIXEL_SIZE
			miracode[ligature["name"]].width = round(xOffset - PIXEL_SIZE)
		lig.addPosSub("ligatures-subtable", tuple(map(lambda codepoint: charactersByCodepoint[codepoint]["name"], ligature["sequence"])))

	print(f"Generated {len(ligatures)} ligatures")
	print("Generating TTF font...")
	miracode.generate(outputDir + "Miracode.ttf")
	# print("Generating OTF font...")
	# miracode.generate(outputDir + "Miracode.otf")

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
	if character.get("diagonals") == False:
		drawDiagonals = False

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
	if get(pixels, row + 1, col) == 1 and (get(pixels, row - 1, col - colMod) != 1 or get(pixels, row + 2, col) == 1) and (get(pixels, row + 2, col + 2 * colMod) != 1 or get(pixels, row, col + 2 * colMod) == 1):
		# Disallowed (H)
		# X 0 0 
		# 1 1 1
		# 1 0 0
		# Disallowed (f)
		# 1 0 0 
		# 0 X 0
		# 1 1 1
		# 0 1 0
		# Disallowed (k)
		# X 0 1
		# 1 1 0
		# 1 0 1
		# Allowed (z)
		# 1 0 0
		# 0 X 0
		# 1 1 1
		# Allowed (M)
		# X 0 0
		# 1 1 0
		# 1 0 1
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

def drawCircle(pen, x, y, radius):
	# Draw clockwise
	VAL = 0.5522847498 # This is (4/3) * (sqrt(2) - 1)
	pen.moveTo(x, y + radius)
	pen.curveTo(x + radius * VAL, y + radius, x + radius, y + radius * VAL, x + radius, y)
	pen.curveTo(x + radius, y - radius * VAL, x + radius * VAL, y - radius, x, y - radius)
	pen.curveTo(x - radius * VAL, y - radius, x - radius, y - radius * VAL, x - radius, y)
	pen.curveTo(x - radius, y + radius * VAL, x - radius * VAL, y + radius, x, y + radius)
	pen.closePath()


def drawOctagon(pen, x, y, radius):
	# Draw clockwise
	VAL = (1 + SQRT_TWO) / 2
	sideLength = radius / VAL
	OCTAGON = [
		(1/2, VAL),
		(VAL, 1/2),
		(VAL, -1/2),
		(1/2, -VAL),
		(-1/2, -VAL),
		(-VAL, -1/2),
		(-VAL, 1/2),
		(-1/2, VAL)
	]
	pen.moveTo(x + sideLength * OCTAGON[0][0], y + sideLength * OCTAGON[0][1])
	for i in range(1, len(OCTAGON)):
		pen.lineTo(x + sideLength * OCTAGON[i][0], y + sideLength * OCTAGON[i][1])
	pen.closePath()

def drawHeart(pen, x, y, radius):
	# Draw clockwise
	HEART = [
		(0, 0.9),
		(0.8, 1.6),
		(1.6, 0.9),
		(1.6, 0.2),
		(0, -1),
		(-1.6, 0.2),
		(-1.6, 0.9),
		(-0.8, 1.6)
	]
	SCALE = 1.2
	radius *= SCALE
	pen.moveTo(x + radius * HEART[0][0], y + radius * HEART[0][1])
	for i in range(1, len(HEART)):
		pen.lineTo(x + radius * HEART[i][0], y + radius * HEART[i][1])
	pen.closePath()

def drawCharacter(character, glyph, pen, xOffset = 0):
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

	leftMargin = 0
	if "leftMargin" in character:
		leftMargin += character["leftMargin"]
	left = leftMargin * PIXEL_SIZE + xOffset

	STROKE = 192
	HALF = STROKE / 2
	DOT_RADIUS = HALF * 1.5

	# Draw the paths
	for edge in edges:
		startX = edge[0][0] * PIXEL_SIZE + PIXEL_SIZE / 2 + left
		startY = top - (edge[0][1] * PIXEL_SIZE - PIXEL_SIZE / 2)
		endX = edge[1][0] * PIXEL_SIZE + PIXEL_SIZE / 2 + left
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


	jointAtPoint = {}
	# Calculate if each point has any joints that aren't in a straight line
	# For instance, a joint coming from the left and a joint coming from the top or just a joint coming from the left
	for point, edges in edgesPerPoint.items():
		if len(edges) == 1:
			# End cap
			jointAtPoint[point] = 1
		elif len(edges) == 2:
			# Determine if the edges are in a straight line
			edge1 = edges[0]
			edge2 = edges[1]
			if edge1[0][0] == edge1[1][0] and edge2[0][0] == edge2[1][0]:
				# Vertical
				jointAtPoint[point] = 0
			elif edge1[0][1] == edge1[1][1] and edge2[0][1] == edge2[1][1]:
				# Horizontal
				jointAtPoint[point] = 0
		else:
			# Joint
			jointAtPoint[point] = 1

	# Draw the dots
	pixels = character["pixels"]
	for row in range(len(pixels)):
		for col in range(len(pixels[0])):
			x = col * PIXEL_SIZE + PIXEL_SIZE / 2 + left
			y = top - row * PIXEL_SIZE + PIXEL_SIZE / 2
			if pixels[row][col] == 1:
				if countNeighbors(pixels, row, col) == 0:
					# Isolated dot
					drawCircle(pen, x, y, DOT_RADIUS)
					continue
				elif jointAtPoint.get((col, row)) == 0:
					# No joint or end cap
					continue
				drawOctagon(pen, x, y, HALF)
			elif pixels[row][col] == 2:
				# Heart
				drawHeart(pen, x, y, HALF)

	# Merge intersecting paths
	glyph.simplify()
	glyph.round()
	glyph.removeOverlap()

	# Return the rightmost edge of the character
	return xOffset + len(pixels[0]) * PIXEL_SIZE

generateFont()
generateExamples(characters, ligatures, charactersByCodepoint)

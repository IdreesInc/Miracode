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

def generateDiacritics(characters, diacritics):
    # Create dictionaries for faster lookup
    charactersByName = {}
    charactersByCodepoint = {}
    diacriticsByCodepoint = {}
    for c in characters:
        charactersByName[c["name"]] = c["codepoint"]
        charactersByCodepoint[c["codepoint"]] = c
    for d in diacritics:
        diacriticsByCodepoint[d] = diacritics[d]

    # Explicit accented references are skipped by the Unicode-name generator.
    # Resolve their base first so the renderer receives the accent as pixels,
    # rather than drawing only the referenced unaccented character.
    for char in characters:
        if not (char.get("reference") and char.get("diacritic")):
            continue
        base = charactersByCodepoint[char["reference"]]
        visited = {char["codepoint"]}
        while base.get("reference"):
            if base["codepoint"] in visited:
                raise ValueError("Circular character reference: " + char["name"])
            visited.add(base["codepoint"])
            base = charactersByCodepoint[base["reference"]]
        pixels = composeDiacritic(base, diacriticsByCodepoint[char["diacritic"]],
                                  char.get("diacriticSpace", 1))
        if pixels is None:
            raise ValueError("Cannot compose diacritic for " + char["name"])
        for key in ("descent", "leftMargin", "diagonals"):
            if key in base and key not in char:
                char[key] = base[key]
        char["pixels"] = pixels
        del char["reference"]

    # List to store generated dictionary
    charList = []

    # Parse the text file
    lines = open("./unicode.txt").readlines()
    for line in lines:
        # Find all lines with a WITH in them
        if not "WITH" in line:
            continue
        # Get the diacritic name
        splitOnWith = line.split("WITH")
        diacritic = splitOnWith[1].split(';')[0].strip().lower().replace(" ", "_")
        name = splitOnWith[0].split(';')[1].strip().lower().replace(" ", "_")
        newName = name + "_with_" + diacritic
        if not diacritic in diacriticsByCodepoint or not name in charactersByName or newName in charactersByName:
            continue
        codepoint = int(line.split(";")[0].strip(), 16)
        baseChar = charactersByCodepoint[charactersByName[name]]
        # Store in a dictionary for serialization
        char = {}
        char["character"] = chr(codepoint)
        char["name"] = name + "_with_" + diacritic
        char["codepoint"] = codepoint
        # char["reference"] = charactersByName[name]
        # char["diacritic"] = diacritic
        # char["diacriticSpace"] = 1
        pixels = composeDiacritic(baseChar, diacriticsByCodepoint[diacritic])
        if pixels is None:
            continue
        char["pixels"] = pixels
        charList.append(char)

    for c in charList:
        characters.append(c)

    print("Added " + str(len(charList)) + " diacritic combinations")
    return characters


def composeDiacritic(base, diacritic, space=1):
    if not base.get("pixels"):
        return None
    pixels = [row.copy() for row in base["pixels"]]
    pixels = pixels[determineTop(pixels):]
    width = len(pixels[0])
    accent = diacritic["pixels"]
    if len(accent[0]) > width:
        return None
    prefix = [row.copy() + [0] * (width - len(row)) for row in accent]
    return prefix + [[0] * width for _ in range(space)] + pixels


def determineTop(pixels):
    # Determine the top of the character
    top = 0
    for row in pixels:
        for col in row:
            if col == 1:
                return top
        top += 1
    return top

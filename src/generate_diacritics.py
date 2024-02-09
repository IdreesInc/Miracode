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
        pixels = []
        if "pixels" in baseChar:
            pixels = baseChar["pixels"].copy()
            top = determineTop(pixels)
            # Trim whitespace from the top
            if top > 0:
                for i in range(top):
                    pixels.pop(0)
            # Add a space for the diacritic
            pixels.insert(0, [0] * len(pixels[0]))
            # Add the diacritic to the base character
            diacriticPixels = diacriticsByCodepoint[diacritic]["pixels"]
            lengthDiff = len(pixels[0]) - len(diacriticPixels[0])
            if lengthDiff < 0:
                print("Diacritic " + diacritic + " is wider than " + name + ", skipping")
                continue
            else:
                # Add the diacritic to the base character
                prefix = []
                for row in diacriticPixels:
                    newRow = row.copy()
                    # Add padding to the right
                    for i in range(lengthDiff):
                        newRow.append(0)
                    prefix.append(newRow)
                pixels = prefix + pixels
        else:
            continue
        char["pixels"] = pixels
        charList.append(char)

    for c in charList:
        characters.append(c)

    print("Added " + str(len(charList)) + " diacritic combinations")
    return characters


def determineTop(pixels):
    # Determine the top of the character
    top = 0
    for row in pixels:
        for col in row:
            if col == 1:
                return top
        top += 1
    return top

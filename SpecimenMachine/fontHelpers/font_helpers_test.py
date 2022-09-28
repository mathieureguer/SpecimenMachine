import fontHelpers
import pprint

import specimenMachine

f = fontHelpers.FontWrapper("/Users/mathieu/Dropbox/10 current work/00 clients/Formagari/2022 specimen machine/00 sources/target fonts/Insitu-Bold.otf")

cat = specimenMachine.SMGlyphSorter()

c = cat.categorise_glyph_for_font(f)

pprint.pprint(c)
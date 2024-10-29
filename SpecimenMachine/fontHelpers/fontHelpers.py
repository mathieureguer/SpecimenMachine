from fontTools.ttLib import TTFont

import yaml
import pathlib
import datetime
import time
import unicodedata

import hyperglot.parse
import hyperglot.languages
# import hyperglot.main

# ----------------------------------------

NAME_TABLE_DESCRIPTION_PATH = "fontspecs/name_table_description.yaml"
OS2_TABLE_WIDTH_PATH = "fontspecs/os2_table_widthclass.yaml"
OS2_TABLE_WEIGHT_PATH = "fontspecs/os2_table_weightclass.yaml"
OS2_TABLE_FSSELECTION_PATH = "fontspecs/os2_table_fsselection.yaml"
OS2_TABLE_PANOSE_PATH = "fontspecs/os2_table_panose.yaml"
HEAD_TABLE_MACSTYLE_PATH = "fontspecs/os2_table_fsselection.yaml"
UNICODE_BLOCS_PATH = "fontspecs/unicode_blocs.txt"
FEATURE_DESCRIPTIONS_PATH = "fontspecs/feature_descriptions.yaml"
NAME_TABLE_DESCRIPTION_PATH = "fontspecs/name_table_description.yaml"
OS2_TABLE_WIDTH_PATH = "fontspecs/os2_table_widthclass.yaml"
OS2_TABLE_WEIGHT_PATH = "fontspecs/os2_table_weightclass.yaml"
OS2_TABLE_FSSELECTION_PATH = "fontspecs/os2_table_fsselection.yaml"
OS2_TABLE_PANOSE_PATH = "fontspecs/os2_table_panose.yaml"
HEAD_TABLE_MACSTYLE_PATH = "fontspecs/os2_table_fsselection.yaml"
UNICODE_BLOCS_PATH = "fontspecs/unicode_blocs.txt"
FEATURE_DESCRIPTIONS_PATH = "fontspecs/feature_descriptions.yaml"

def load_yaml_from_path(path):
    p = pathlib.Path(__file__).parent / path
    with open(p, "r") as file:
        return yaml.safe_load(file)

name_specs = load_yaml_from_path(NAME_TABLE_DESCRIPTION_PATH)
os2_width_specs = load_yaml_from_path(OS2_TABLE_WIDTH_PATH)
os2_weight_specs = load_yaml_from_path(OS2_TABLE_WEIGHT_PATH)
os2_fsSelection_specs = load_yaml_from_path(OS2_TABLE_FSSELECTION_PATH)
os2_panose_specs = load_yaml_from_path(OS2_TABLE_PANOSE_PATH)
head_macstyle_specs = load_yaml_from_path(HEAD_TABLE_MACSTYLE_PATH)
feature_descriptions = load_yaml_from_path(FEATURE_DESCRIPTIONS_PATH)

# ----------------------------------------

def load_font_dir(path, sort=True):
    font_paths = walk_font_dir(path)
    return load_fonts_from_paths(font_paths, sort=sort)

def load_font_list(list_of_path, sort=False):
    font_paths = []
    for p in list_of_path:
        p = pathlib.Path(p)
        font_paths += walk_font_dir(p)
    return load_fonts_from_paths(font_paths, sort=sort)
    return fonts

def load_fonts_from_paths(list_of_paths, sort=True):
    fonts = [FontWrapper(p) for p in list_of_paths]
    if sort:
        fonts = sorted(fonts, key=lambda f: f.get_sorting_score())
    return fonts


def walk_font_dir(path):
    file_types = [".otf", ".ttf", ".woff", ".woff2"]
    path = pathlib.Path(path)
    if not path.exists():
        raise FileNotFoundError(f"'{path}' does not exist")
        return []
    if path.is_dir():
        fonts = []
        for ext in file_types:
            fonts += path.glob("*" + ext)
        return fonts
    if path.is_file():
        assert path.suffix in file_types, f"{path.name} is not a font file"
        return [path]

# ----------------------------------------

class HyperglotAssistant:

    def __init__(self):
        t = time.time()
        strict_iso = False
        self.langs = hyperglot.languages.Languages(strict=strict_iso)
        # print(f"loaded langs in {time.time()-t} sec")

    def collect_language_support(self, font_path, speaker_threshold=0):
        support = "base"
        decomposed = False
        marks = False
        validity = "draft"
        include_all_orthographies = False
        include_historical = False
        include_constructed = False

        t = time.time()
        chars = hyperglot.parse.parse_font_chars(font_path)
        # print(f"parsed font chars in {time.time()-t} sec")

        t = time.time()
        supported = self.langs.supported(chars, support, validity,
                                    decomposed, marks,
                                    include_all_orthographies,
                                    include_historical,
                                    include_constructed)
        # print(f"identified supported langs in {time.time()-t} sec")

        out = {}
        for script, langs in supported.items():
            # out[script] = [f"{lang.get_name()} ({iso})" for iso, lang in langs.items()]
            out[script] = [f"{lang.get_name()}" for iso, lang in langs.items() if lang.get("speakers", 0)>=speaker_threshold]
        return out

# ----------------------------------------

class CatGlyph():

    SUFFIX_CATEGORIES = {
        "smcp": ["smcp", "sc", "small"],
        "numr": ["numr", "numerator"],
        "dnom": ["dnom", "dnominator"],
        "sups": ["sup", "sups", "superior", "superiors"],
        "sinf": ["sinf", "inf", "inferior", "infs"],
        "onum.tnum": ["ot", "OT", "onum.tnum", "tnum.onum", "tosf"],
        "onum.pnum": ["op", "OP", "onum.pnum", "pnum.onum", "osf"],
        "lnum.tnum": ["lt", "LT", "lnum.tnum", "tnum.lnum", "tf"],
        "lnum.pnum": ["lf", "Lf", "lnum.pnum", "tnum.pnum", "lf"],
        "case": ["case", "cap"]
    } 

    def __init__(self, name, font):
        self.name = name
        self.font = font

        self._set_pseudo_unicode_and_suffix()


    def _set_pseudo_unicode_and_suffix(self):
        unicode = self.font.rcmap.get(self.name, None)
        if unicode:
            self.unicode = list(unicode)[0]
        else:
            self.unicode = None
        for root, suffix in self._root_suffix_find(self.name):
            pseudo_unicode = self.font.rcmap.get(root, None)
            if pseudo_unicode:
                self.pseudo_unicode = list(pseudo_unicode)[0]
            else:
                self.pseudo_unicode = None
            self.suffix = suffix
            self.root = root

    def _root_suffix_find(self, name, sep="."):
        parts = name.split(sep)
        roots_suffixes = [(sep.join(parts), None)]
        for i in range(1, len(parts)):
            roots_suffixes.append((sep.join(parts[:-i]), parts[-i:]))    
        return roots_suffixes
            

    @property
    def unicode_category(self):
        if self.pseudo_unicode:
            return unicodedata.category(chr(self.pseudo_unicode))
    
    @property
    def suffix_category(self):
        if self.suffix:
            for s in self.suffix:
                for cat, suffixes in self.SUFFIX_CATEGORIES.items():
                    if s in suffixes:
                        return cat

    @property
    def is_composed_character(self):
        if self.pseudo_unicode:
            return unicodedata.decomposition(chr(self.pseudo_unicode)) != ""
        else:
            return False




# ----------------------------------------

class FontWrapper(TTFont):
    """
    FontWrapper is wrapping a fonttools TTFont object
    in order to add a few handy helper methods 
    it also keep track of the font file path

    this is not a comprehensive wrapper, things are being added as needed
    """

    def __init__(self, path):
        self.path = pathlib.Path(path)
        super().__init__(path)

    # caching tables
    @property
    def os2(self):
        if not hasattr(self, "_os2"):
            self._os2 = self["OS/2"]
        return self._os2

    @property
    def name(self):
        if not hasattr(self, "_name"):
            self._name = self["name"]
        return self._name

    @property
    def head(self):
        if not hasattr(self, "_head"):
            self._head = self["head"]
        return self._head

    @property
    def cmap(self):
        if not hasattr(self, "_cmap"):
            self._cmap = self["cmap"]
        return self._cmap

    @property
    def rcmap(self):
        if not hasattr(self, "_rcmap"):
            self._rcmap = self.cmap.buildReversed()
        return self._rcmap


    @property
    def fsSelection(self):
        if not hasattr(self, "_fsSelection"):
            d = self._get_bits_based_dict(self.os2.fsSelection, os2_fsSelection_specs)
            self._fsSelection = d
        return self._fsSelection


    @property
    def year_created(self):
        return self.date_created.strftime("%Y")

    @property
    def date_created(self):
        # wtf
        time_stamp = self.head.created
        reference_time = datetime.datetime(1904, 1, 1, 0, 0)
        epoch_time = datetime.datetime(1970, 1, 1, 0, 0)
        delta = reference_time - epoch_time
        return datetime.datetime.fromtimestamp(time_stamp) + delta

    @property
    def prefered_family_name(self):
        out = self.name.getDebugName(16)
        if out == None:
            return self.name.getDebugName(1)
        else:
            return out

    @property
    def prefered_style_name(self):
        out = self.name.getDebugName(17)
        if out == None:
            return self.name.getDebugName(2)
        else:
            return out

    @property
    def designer(self):
        return self.name.getDebugName(9)

    @property
    def copyright(self):
        return self.name.getDebugName(0)


    @property
    def version(self):
        return round(float(self.head.fontRevision), 3)

    @property
    def language_support(self):
        hyperglot = HyperglotAssistant()
        return hyperglot.collect_language_support(self.path)

    def get_language_support(self, speaker_threshold=0):
        hyperglot = HyperglotAssistant()
        return hyperglot.collect_language_support(self.path, speaker_threshold=speaker_threshold)

    # handy methods

    def is_italic(self):
        return self.fsSelection["Italic"]

    def is_bold(self):
        return self.fsSelection["Bold"]

    def get_sorting_score(self):
        return (self.os2.usWidthClass, self.os2.usWeightClass, self.is_italic())

    # unicode and glyph order

    @property
    def glyph_order(self):
        return self.getGlyphOrder()

    def get_cat_glyphs(self):
        return [CatGlyph(n, self) for n in self.glyph_order]


    #   features

    @property
    def gsub(self):
        if not hasattr(self, "_gsub"):
            self._gsub = self["GSUB"]
        return self._gsub

    @property
    def gpos(self):
        if not hasattr(self, "_gpos"):
            self._gpos = self["GPOS"]
        return self._gpos

    @property
    def features(self):
        relevant_keys = ["friendly name", "function"]
        out = {}
        for fea in self.feature_tags:
            fea_specs = feature_descriptions[fea]
            out[fea] = {key: fea_specs[key] for key in relevant_keys}
        return out
    
    @property
    def feature_tags(self):
        features = set()
        tables = [self.gsub, self.gpos]
        for table in tables:
            if table != None:
                for fea in table.table.FeatureList.FeatureRecord:
                    features.add(fea.FeatureTag)
        return sorted(list(features))


    # misc 

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.path.name}>"

    # fontspecs helpers 

    def get_fsSelection_as_dict(self):
        return self._get_bits_based_dict(self.os2.fsSelection, os2_fsSelection_specs)


    def _num_to_selected_bits(self, num, bits=32):
        sel = []
        for i in range(bits):
            if num & 1 << i:
                sel.append(i)
        return sel

    def _get_bits_based_dict(self, num, description_map):
        flaged = self._num_to_selected_bits(num, bits=16)
        out = {}
        for bit_, value in description_map.items():
            if bit_ in flaged:
                out[value] = True
            else:
                out[value] = False
        return out


# ----------------------------------------
 


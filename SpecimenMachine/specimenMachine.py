# import drawbotgrid.grid as dbgrid
from . import fontHelpers

import drawBot as db
from fontTools.ttLib import TTFont
from addict import Dict

from collections import OrderedDict, ChainMap
import yaml
import pathlib
import datetime
import copy

# ----------------------------------------

SETTINGS_FILE_NAME = "settings.yaml"
AUTO_TOKEN  = "<auto>"
FILL_TOKEN  = "<fill>"

# ----------------------------------------

def path_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))

yaml.add_representer(pathlib.PosixPath, path_presenter)

# ----------------------------------------
# dict helpers

def nested_get(dic, keys):    
    for key in keys:
        dic = dic[key]
    return dic
def nested_set(dic, keys, value):
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value

def nested_keys(dic):
    return [k for k, v in nested_items(dic)]

def nested_items(dic, parent_keys=[]):
    items = []
    for k, v in dic.items():
        if isinstance(v, dict):
            new_parent_keys = parent_keys[:]
            new_parent_keys.append(k)
            items += nested_items(v, new_parent_keys)
        else:
            items.append((parent_keys+[k], v))
    return items
# ----------------------------------------

class SMBase():
    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class SMSettings(SMBase):

    defaults = {}
    
    # ----------------------------------------
    
    def __init__(self, director, user_settings):
        self.director = director
        self.user_settings = user_settings

        self._load_settings_raw()
        
        self._will_autofill_private()
        self.will_autofill()

        self._autofill_settings()

        self.did_autofill()
        self._did_autofill_private()

    # ----------------------------------------
    # housekeeping 

    def _will_autofill_private(self):
        pass

    def will_autofill(self):
        pass

    def _did_autofill_private(self):
        pass

    def did_autofill(self):
        pass

    # ----------------------------------------
    # load settings

    def _load_settings_raw(self):
        self.settings_raw = {}
        self.settings_raw.update(self.defaults)
        self.settings_raw.update(self.user_settings)
    
    def _autofill_settings(self):
        """
        this autofill values for both autofill tokens of key at a time 
        (allowing autofill functions to reference preveious keys)
        """
        self.settings_fill = Dict()
        self.settings = Dict()

        for chained_keys, value in nested_items(self.settings_raw):
            if value == AUTO_TOKEN:
                auto_value = self._get_autofill_value(chained_keys)
                nested_set(self.settings, chained_keys, auto_value)
                nested_set(self.settings_fill, chained_keys, value)
            elif value == FILL_TOKEN:
                fill_value = self._get_autofill_value(chained_keys)
                nested_set(self.settings_fill, chained_keys, fill_value)
                nested_set(self.settings, chained_keys, fill_value)
            else:
                nested_set(self.settings_fill, chained_keys, value)
                nested_set(self.settings, chained_keys, value)


    def _load_recursive_autofill_dict(self, output_dic, input_dic, token):
        for chained_keys, value in nested_items(input_dic):
            if value == token:
                value = self._get_autofill_value(chained_keys)               
            nested_set(output_dic, chained_keys, value)

    # ----------------------------------------
    # autofill

    def _auto_fill_key(self, dic, chained_keys):
        value = self._get_autofill_value(chained_keys)
        nested_set(dic, chained_keys, value)

    def _get_autofill_value(self, chained_keys):
        if isinstance(chained_keys, str):
            chained_keys = [chained_keys]
        autofill_key = self._get_autofill_funct_name(chained_keys)
        if hasattr(self, autofill_key):
            autofill_func = getattr(self, autofill_key)
            return autofill_func()
        else:
            try:
                return nested_get(self.defaults, chained_keys)
            except:
                raise KeyError

    def _get_autofill_funct_name(self, chained_keys):
        return f"autofill_{'_'.join(chained_keys)}"
 

class SMFontCollection(SMSettings):
    defaults = {
        "font_directory": AUTO_TOKEN, 
        "font_paths": AUTO_TOKEN,
        }

    # ----------------------------------------

    def _will_autofill_private(self):
        self._fonts_need_sorting = False
        
    def _did_autofill_private(self):
        self.load_fonts()
        font_paths = [str(f.path.relative_to(self.director.root_dir)) for f in self.fonts]
        self.settings.font_paths = font_paths

    # ----------------------------------------
    
    def autofill_font_directory(self):
        return self.director.input_path
  
    def autofill_font_paths(self):
        font_path_unsorted = fontHelpers.walk_font_dir(self.settings["font_directory"])
        self.fonts = fontHelpers.load_font_list(font_path_unsorted, sort=True)
        font_paths_sorted = [str(f.path.relative_to(self.director.root_dir)) for f in self.fonts]
        return font_paths_sorted
        
    # ----------------------------------------
    
    def load_fonts(self):
        self.fonts = fontHelpers.load_font_list(self.absolute_font_paths)

    @property
    def absolute_font_paths(self):
        dir_ = pathlib.Path(self.settings.font_directory)
        return [dir_ / font_path for font_path in self.settings.font_paths]
    
    # ----------------------------------------
    
    def get_common_fonts_attribute(self, attribute):
        attrs = [getattr(f, attribute) for f in self.fonts]
        return self._remove_duplicate_in_list(attrs)

    def _remove_duplicate_in_list(self, list_):
        # python > 3.5 preserve order of keys in a dict. Yay.
        return list(dict.fromkeys(list_))
    
    # ----------------------------------------
    
    @property
    def common_family_name(self):
        return self.get_common_fonts_attribute("prefered_family_name")

    @property
    def common_style_name(self):
        return self.get_common_fonts_attribute("prefered_style_name")

    @property
    def copyright(self):
        return list(set([f.copyright for f in self.fonts]))

    def get_language_support(self, speaker_threshold=0):
        # for efficiency reasons, only the first font languge support is processed here
        # i am not sure what should happen if language support are inconsistents accross the font collection
        return self.fonts[0].get_language_support(speaker_threshold=speaker_threshold)


    @property
    def font_collection_name(self):
        family_names = self.common_family_name
        style_names = self.common_style_name
        if len(style_names) > 1:
            font_collection_name = f"{''.join(family_names)}"
        else:
            font_collection_name = f"{''.join(family_names)}-{''.join(style_names)}"
        return font_collection_name
    
    @property
    def font_collection_filename(self):
        return self.font_collection_name.replace(" ", "")
    
    # ----------------------------------------
    # formatted strings
        
    def get_font_names_as_formatted_string(self, sep="\n", **kwargs):
        if not sep:
            sep = ""

        fs = db.FormattedString()
        for i, font in enumerate(self.fonts):
            fs.append(f"{font.prefered_family_name} {font.prefered_style_name}",
                      font=font.path, **kwargs)
            if i+1 < len(font):
                fs.append(sep)
        return fs

    def get_font_sample_as_formatted_string(self, sample_str, sep="\n", **kwargs):
        if not sep:
            sep = ""
        fs = db.FormattedString()
        for i, font in enumerate(self.fonts):
            fs.append(sample_str,
                      font=font.path, **kwargs)
            if i+1 < len(font):
                fs.append(sep, 
                          font=font.path, **kwargs)
        return fs

    # ----------------------------------------
    # access font

    def get_font_by_family_style_name(self, name):
        for font in self.fonts:
            if f"{font.prefered_family_name} {font.prefered_style_name}" == name:
                return font
        return self.fonts[0]

    def get_fonts_by_style_name(self, style):
        return [f for f in self.fonts if f.prefered_style_name == style]

    # ----------------------------------------
    
    def draw(self):
        pass


class SMGlyphSorterQuery(SMBase):

    def __init__(self, target_attribute, target_value, equality="=="):
        self.target_attribute = target_attribute
        self.target_value = target_value
        self.equality = equality

    def test_glyph(self, glyph):
        value = getattr(glyph, self.target_attribute)
        if self.equality == "==":
            if value:
                return value == self.target_value
        elif self.equality == ">=":
            if value:
                return value >= self.target_value
        elif self.equality == "<=":
            if value:
                return value <= self.target_value
        elif self.equality == "!=":
            if value:
                return value != self.target_value
        elif self.equality == ">":
            if value:
                return value > self.target_value
        elif self.equality == "<":
            if value:
                return value < self.target_value
        elif self.equality == "in":
            if value:
                return value in self.target_value
        elif self.equality == "not in":
            if value:
                return value not in self.target_value
        return False


class SMGlyphSorter(SMBase):
    category_queries = {
        "Uppercases": [SMGlyphSorterQuery("unicode", 65, equality=">="), SMGlyphSorterQuery("unicode", 90, equality="<=")],
        "Accented Uppercases": [SMGlyphSorterQuery("unicode_category", "Lu")],
        "Lowercases": [SMGlyphSorterQuery("unicode", 97, equality=">="), SMGlyphSorterQuery("unicode", 122, equality="<=")],
        "Accented Lowercases": [SMGlyphSorterQuery("unicode_category", "Ll")],
        "Case Sensitive Forms": [SMGlyphSorterQuery("suffix_category", "case"), SMGlyphSorterQuery("unicode_category", ["Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps"], equality="in")],
        "Punctuation": [SMGlyphSorterQuery("unicode_category", ["Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps"], equality="in")],
        "Proportional Oldstyle Figures": [SMGlyphSorterQuery("suffix_category", "onum.pnum"), SMGlyphSorterQuery("unicode_category", ["Nd", "Sc"], equality="in")], 
        "Proportional Lining Figures": [SMGlyphSorterQuery("suffix_category", "lnum.pnum"), SMGlyphSorterQuery("unicode_category", ["Nd", "Sc"], equality="in")], 
        "Tabular Oldstyle Figures": [SMGlyphSorterQuery("suffix_category", "onum.tnum"), SMGlyphSorterQuery("unicode_category", ["Nd", "Sc"], equality="in")],
        "Tabular Lining Figures": [SMGlyphSorterQuery("suffix_category", "lnum.tnum"), SMGlyphSorterQuery("unicode_category", ["Nd", "Sc"], equality="in")],
        "Default Figures": [SMGlyphSorterQuery("unicode_category", ["Nd", "Sc"], equality="in")],
        "Mathematical Symbols": [SMGlyphSorterQuery("unicode_category", "Sm")],
        "Arrows & Other Symbols": [SMGlyphSorterQuery("unicode_category", "So")],
        "Marks": [SMGlyphSorterQuery("unicode_category", ["Mc", "Me", "Mn"], equality="in")],
        "Other Figures": [SMGlyphSorterQuery("unicode_category", "No")],
    }

    def categorise_glyph_for_font(self, font, ignore=[".notdef", ".null", "CR", "space", "uni00A0", "uni2009"]):
        categories = OrderedDict()
        for glyph in font.get_cat_glyphs():
            if glyph.name not in ignore:
                categorized = False
                for category, queries in self.category_queries.items():
                    results = [querie.test_glyph(glyph) for querie in queries]
                    if False not in results:
                        categories.setdefault(category, []).append(glyph.name)
                        categorized = True
                        break
                if not categorized:
                    categories.setdefault("Other", []).append(glyph.name)
        return categories


class SMTemplate(SMSettings):

    # def __init__(self, director, settings):
    #     super().__init__(director, settings)

    def draw(self):
        print(f"-- drawing {self}")
        self._draw()

    def _draw():
        print(f"must overide {self}._draw()")


class SMTemplateAllPages(SMTemplate):

    def draw(self):
        print(f"-- drawing {self}")
        for page in db.pages():
            with page:
                self._draw()

# ----------------------------------------

FONT_COLLECTION_SECTION_IDENTIFIER = "fonts"

class SMDirector(SMBase):

    template_map = {
        "fonts" : SMFontCollection
        }

    defaults = []

    def __init__(self, input_path, single_font_mode=False):

        assert FONT_COLLECTION_SECTION_IDENTIFIER in self.template_map

        # ----------------------------------------
        
        self.input_path = pathlib.Path(input_path)
        if self.input_path.is_dir():
            self.root_dir = self.input_path
        else:
            self.root_dir = self.input_path.parent

        self.settings_path =  self.root_dir/SETTINGS_FILE_NAME
        self.load_settings()
        
        # ----------------------------------------
        
        self.templates = []
        self.load_font_collection()
        self.load_templates()

        # should this be dealt with at a higher level?
        self.single_font_mode = single_font_mode

    # ----------------------------------------
    
    def load_settings(self):
        setting_paths = list(self.root_dir.glob("*" + SETTINGS_FILE_NAME))
        if len(setting_paths) == 0:
            print(f"-- No setting file found, creating {self.settings_path.relative_to(self.root_dir)}")
            self.settings = self.defaults
            self.yaml_write_settings_to_path(self.settings, self.settings_path)
        else:
            self.settings_path = setting_paths[0]
            print(f"-- loading settings from {self.settings_path.relative_to(self.root_dir)}")
            with open(self.settings_path, "r") as setting_file:
                self.settings = yaml.safe_load(setting_file.read())


    def yaml_write_settings_to_path(self, templates, path):
        with open(path, "w+") as out_file:
            out_str = []
            for template in templates:
                out_str.append(yaml.dump([template],
                        sort_keys=False, 
                        allow_unicode=True,
                        line_break=False,
                        default_flow_style=False,
                        width=float("inf")))
            out_file.write("\n".join(out_str))

    # ----------------------------------------

    def load_font_collection(self):
        for s in self.settings:
            if s["template"] == FONT_COLLECTION_SECTION_IDENTIFIER:
                fonts = self.init_section_from_settings(s)
                self.templates.append(fonts)
                setattr(self, FONT_COLLECTION_SECTION_IDENTIFIER, fonts)

    def load_templates(self):
        for s in self.settings:
            if s["template"] in self.template_map and s["template"] != FONT_COLLECTION_SECTION_IDENTIFIER:
                template = self.init_section_from_settings(s)
                self.templates.append(template)
 

    def init_section_from_settings(self, template_dict):
        template_class = self.template_map.get(template_dict["template"])
        if template_class:
            settings = template_dict.get("settings", {})
            return template_class(self, settings)

    def draw(self, output_dir=None):

        # if self.single_font_mode:
        #     targets = [self.template_map["fonts"](self, {"font_paths": [path]}) for path in self.fonts.font_paths]
        # else:
        #     targets = [self.fonts]

        # original_fonts = self.fonts

        # for fonts in targets:
            # self.fonts = fonts

        now = datetime.datetime.now()
        db.newDrawing()
        self._draw()

        if output_dir == None:
            output_dir = self.root_dir

        out = output_dir / f"{now.strftime('%Y%m%d-%H%M')}-specimenMachine-{self.fonts.font_collection_filename}.pdf"
        db.saveImage(out)
        print(f"-- saved {out}")

        db.endDrawing()

        # self.fonts = original_fonts

    def _draw(self):
        draw_last = []
        for template in self.templates:
            if issubclass(type(template), SMTemplateAllPages):
                draw_last.append(template)
            elif issubclass(type(template), SMFontCollection):
                pass
            else:
                template.draw()
        for template in draw_last:
            template.draw()

    def get_settings_as_list(self):
        out = [{"template": self.reverse_template_map[template.__class__], "settings": template.settings_fill.to_dict()} for template in self.templates]
        for template in out:
            if len(template["settings"]) == 0:
                del template["settings"]
        return out 

    def write_settings_file(self):
        print("-- saving setting file")
        out = self.get_settings_as_list()
        self.yaml_write_settings_to_path(out, self.settings_path)


    @property
    def reverse_template_map(self):
        return {v:k for k, v in self.template_map.items()}

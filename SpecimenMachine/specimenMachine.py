# import drawbotgrid.grid as dbgrid
from .fontHelpers import load_font_dir, load_font_list

import drawBot as db
from fontTools.ttLib import TTFont

from collections import OrderedDict
import yaml
import pathlib
import datetime

SETTINGS_FILE_NAME = "settings.yaml"

class SMBase():
    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class SMSettings(SMBase):
    attributes = {}
    POPULATE_TRIGGER  = "<?>"

    def __init__(self, director, settings):
        self.settings = settings
        self.director = director
        self.load_settings(self.attributes)
        self.load_settings(self.settings)

    def populate_default_value(self):
        return NotImplemented

    def all_setting_as_dict(self):
        return {arg: getattr(self, arg) for arg in self.args}

    def load_settings(self, settings):
        if settings != self.POPULATE_TRIGGER:
            for at, value in settings.items():
                if value == self.POPULATE_TRIGGER:
                    value = self.attributes.get(at)
                setattr(self, at, value)
        # self._private_populate_attributes()
        # self.populate_attributes()

    def public_populate_attributes(self):
        """
        override this to set up you own populating methods
        """
        pass

    def _private_populate_attributes(self):
        """
        this is used by the library to load things 
        that subclasses should not have to worry about
        """
        pass

    def populate_attributes(self):
        self._private_populate_attributes()
        self.public_populate_attributes()

    # def get_autocompleted_settings(self):
    #     """
    #     this will add the self.attribute value 
    #     to each key attribute a value of <?> in self.settings 
    #     """
    #     updated_settings = {}
    #     for k, v in self.settings.items():
    #         if v == self.POPULATE_TRIGGER:
    #             updated_settings[k] = getattr(self, k)
    #         else:
    #             updated_settings[k] = v
    #     return updated_settings

    def is_attribute_real(self, attribute):
        value = getattr(self, attribute)
        return self._is_value_real(value)

    def _is_value_real(self, value):
        return value != None and value != self.POPULATE_TRIGGER

    def draw(self):
        pass

    @property
    def user_populated_settings(self):
        if self.settings == self.POPULATE_TRIGGER:
            out = self._get_populated_dict(self.attributes)
        else:
            out = self._get_populated_dict(self.settings, skip_none_values=True)
        return out

    def _get_populated_dict(self, dict, skip_none_values=False):
        out = {}
        for k, v in dict.items():
            if v == self.POPULATE_TRIGGER:
                v = getattr(self, k)
            if not skip_none_values or v:
                out[k] = v
        return out


        # return {attr: getattr(self, attr) for attr in self.attributes}


class SMFontCollection(SMSettings):
    attributes = {
        "font_directory":None, 
        "font_paths": None,
        }
        
    def load_fonts(self):

        if self.is_attribute_real("font_paths"):
            font_paths = [self.director.root_dir / p for p in self.font_paths]
            self.fonts = load_font_list(font_paths)
        elif self.font_directory != None:
            self.fonts = load_font_dir(self.director.root_dir / self.font_directory)
        else:
            self.fonts = load_font_dir(self.director.input_path)
        self.font_paths = [str(f.path.relative_to(self.director.root_dir)) for f in self.fonts]

    def _private_populate_attributes(self):
        self.load_fonts()

    @property
    def common_family_name(self):
        return self.get_common_fonts_attribute("prefered_family_name")

    def get_common_fonts_attribute(self, attribute):
        attrs = [getattr(f, attribute) for f in self.fonts]
        return self._remove_duplicate_in_list(attrs)

    def _remove_duplicate_in_list(self, list_):
        # python > 3.5 preserve order of keys in a dict. Yay.
        return list(dict.fromkeys(list_))


    def get_font_names_as_formatted_string(self, sep="\n", **kwargs):
        if not sep:
            sep = ""
        fs = db.FormattedString(**kwargs)
        for i, font in enumerate(self.fonts):
            fs.append(f"{font.prefered_family_name} {font.prefered_style_name}",
                      font=font.path)
            if i+1 < len(font):
                fs.append(sep)
        return fs


    def get_font_sample_as_formatted_string(self, sample_str, sep="\n", **kwargs):
        if not sep:
            sep = ""
        fs = db.FormattedString(**kwargs)
        for i, font in enumerate(self.fonts):
            fs.append(sample_str,
                      font=font.path)
            if i+1 < len(font):
                fs.append(sep)
        return fs

    def get_font_by_family_style_name(self, name):
        for font in self.fonts:
            if f"{font.prefered_family_name} {font.prefered_style_name}" == name:
                return font
        return self.fonts[0]

    def get_fonts_by_style_name(self, style):
        return [f for f in self.fonts if f.prefered_style_name == style]

    def get_copyright(self):
        return list(set([f.copyright for f in self.fonts]))

    def get_language_support(self):
        # for efficiency reasons, only the first font languge support is processed here
        # i am not sure what should happen if language support are inconsistents accross the font collection
        return self.fonts[0].language_support


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


class SMSection(SMSettings):

    def __init__(self, director, settings):
        super().__init__(director, settings)

    def draw(self):
        print(f"-- drawing {self}")
        self._draw()

    def _draw():
        print(f"must overide {self}._draw()")


class SMSectionAllPages(SMSection):

    def draw(self):
        print(f"-- drawing {self}")
        for page in db.pages():
            with page:
                self._draw()


class SMDirector(SMBase):
    section_map = {
        "fonts" : SMFontCollection

    }

    required_attributes = ["fonts"]

    default_settings = {}


    def __init__(self, input_path, single_font_mode=False, columns=None, baselines=None):

        self.input_path = pathlib.Path(input_path)
        if self.input_path.is_dir():
            self.root_dir = self.input_path
        else:
            self.root_dir = self.input_path.parent

        self.settings_path =  self.root_dir/SETTINGS_FILE_NAME
        self.section_settings = self.look_for_settings()
                
        self.columns = columns
        self.baselines = baselines
        self.sections = []
        self.load_sections()
        self.assign_required_section_to_attributes()
        self.populate_required_sections()
        self.populate_other_sections()

        # should this be dealt with at a higher level?
        self.single_font_mode = single_font_mode


    def look_for_settings(self):
        setting_paths = list(self.root_dir.glob("*" + SETTINGS_FILE_NAME))
        if len(setting_paths) == 0:
            print(f"-- No setting file found, creating {self.settings_path.relative_to(self.root_dir)}")
            section_settings = self.default_settings
            self.yaml_dump_sections_to_path(section_settings, self.settings_path)
        else:
            self.settings_path = setting_paths[0]
            print(f"-- loading settings from {self.settings_path.relative_to(self.root_dir)}")
            with open(self.settings_path, "r") as setting_file:
                section_settings = yaml.safe_load(setting_file.read())
        return section_settings

    def yaml_dump_sections_to_path(self, sections, path):
        with open(path, "w+") as out_file:
            out_str = []
            for s in sections:
                out_str.append(yaml.dump([s],
                        sort_keys=False, 
                        allow_unicode=True,
                        line_break=False,
                        default_flow_style=False,
                        width=float("inf")))
            out_file.write("\n".join(out_str))



    def load_sections(self):
        self.sections = [self.init_section_from_settings(s) for s in self.section_settings]


    def assign_required_section_to_attributes(self):
        for attr in self.required_attributes:
            target_class = self.section_map.get(attr)
            if target_class:
                for section in self.sections:
                    if type(section) == target_class:
                        setattr(self, attr, section)

    def populate_required_sections(self):
        for attr in self.required_attributes:
            section = getattr(self, attr)
            section.populate_attributes()

    def populate_other_sections(self):
        for section in self.sections:
            # section = getattr(self, attr)
            section.populate_attributes()


    def init_section_from_settings(self, section_dict):
        section_class = self.section_map.get(section_dict["type"])
        if section_class:
            section_settings = section_dict.get("settings", {})
            return section_class(self, section_settings)

    # def get_autocompleted_settings(self):
    #     return [s.get_autocompleted_settings() for s in self.sections]


    def draw(self, output_dir=None):
        family_names = self.fonts.common_family_name
        now = datetime.datetime.now()
        db.newDrawing()
        self._draw()

        if output_dir == None:
            output_dir = self.root_dir

        out = output_dir / f"{''.join(family_names)}-specimenMachine-{now.strftime('%Y%m%d-%H%M')}.pdf"
        db.saveImage(out)
        print(f"-- saved {out}")

        db.endDrawing()

    def _draw(self):
        draw_last = []
        for section in self.sections:
            if issubclass(type(section), SMSectionAllPages):
                draw_last.append(section)
            else:
                section.draw()
        for section in draw_last:
            section.draw()

    def populate_settings_file(self):
        print("-- updating setting file (if required)")
        out = [{"type": self.reverse_section_map[section.__class__], "settings": section.user_populated_settings} for section in self.sections]
        for section in out:
            if len(section["settings"]) == 0:
                del section["settings"]
        self.yaml_dump_sections_to_path(out, self.settings_path)

    @property
    def reverse_section_map(self):
        return {v:k for k, v in self.section_map.items()}

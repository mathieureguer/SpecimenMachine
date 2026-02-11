import copy
from addict import Dict

AUTO_TOKEN  = "<auto>"
FILL_TOKEN  = "<fill>"

class SMSettings():

    defaults = {
        "subtitle": "cool",
        "info": {
            "name": "<fill>",
            "age": "37",
            },
        "class_test": "<auto>",
        }
    
    # ----------------------------------------

    def autofill_class_test(self):
        return "auto class"

    def autofill_info_name(self):
        return "auto name"
    # ----------------------------------------
    
    def __init__(self, director, user_settings):
        self.settings = {}

        self.director = director
        self.user_settings = user_settings

        self.settings_raw = self._load_settings_raw()
        self.settings_fill = self._load_recursive_autofill_dict(self.settings_raw, FILL_TOKEN)
        self.settings = Dict(self._load_recursive_autofill_dict(self.settings_fill, AUTO_TOKEN))

    # ----------------------------------------
    
    def _load_settings_raw(self):
        raw = {}
        raw.update(self.defaults)
        raw.update(self.user_settings)
        return raw
    
    def _load_recursive_autofill_dict(self, dic, token):
        out = copy.deepcopy(dic)
        for k, v in self._nested_items(out):
            if v == token:
                self._auto_fill_key(out, k)
        return out

    # ----------------------------------------

    def _auto_fill_key(self, dic, chained_keys):
        if isinstance(chained_keys, str):
            chained_keys = [chained_keys]
        value = self._get_autofill_value(chained_keys)
        self.nested_set(dic, chained_keys, value)

    def _get_autofill_value(self, chained_keys):
        autofill_key = self._get_autofill_funct_name(chained_keys)
        if hasattr(self, autofill_key):
            autofill_func = getattr(self, autofill_key)
            return autofill_func()
        else:
            try:
                return self._nested_get(self.defaults, chained_keys)
            except:
                raise KeyError

    def _get_autofill_funct_name(self, chained_keys):
        return f"autofill_{'_'.join(chained_keys)}"
    
    # ----------------------------------------
    
    def _nested_get(self, dic, keys):    
        for key in keys:
            dic = dic[key]
        return dic

    def nested_set(self, dic, keys, value):
        for key in keys[:-1]:
            dic = dic.setdefault(key, {})
        dic[keys[-1]] = value

    def _nested_keys(self, dic):
        return [k for k, v in self._nested_items(dic)]
       
    def _nested_items(self, dic, parent_keys=[]):
        items = []
        for k, v in dic.items():
            if isinstance(v, dict):
                new_parent_keys = parent_keys[:]
                new_parent_keys.append(k)
                items += self._nested_items(v, new_parent_keys)
            else:
                items.append((parent_keys+[k], v))
        return items



        
            
 

if __name__ == "__main__":
    import pprint
    settings = SMSettings(None, {"subtitle": "<auto>"})
    pprint.pprint(settings.settings_raw)
    pprint.pprint(settings.settings_fill)
    pprint.pprint(settings.settings)
    print("info", settings.settings.info)
    print("test", settings.settings.test.con)
    print("info.name", settings.settings.info.name)
    pprint.pprint(settings.settings)

    

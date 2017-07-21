import re
from copy import deepcopy
from functools import partial

import yaml


def search_attr(pattern, input_str, none_value):
    search = re.search(pattern, input_str)
    if search:
        result = search.group(search.lastindex) and str(search.group(search.lastindex)).strip()
        if result != none_value:
            return result.strip()
    return None


class ParsedValue(object):
    @classmethod
    def boolean(cls, name, pattern, non_value=None):
        return cls(name, pattern, non_value, cls.set_parsed_boolean)

    @classmethod
    def list(cls, name, pattern, non_value=None):
        return cls(name, pattern, non_value, cls.set_parsed_list)

    def __init__(self, name, pattern, non_value=None, transform=None):
        self.name = name
        self.pattern = pattern
        self.non_value = non_value
        self.set_parsed = transform and partial(transform, self) or self.set_parsed

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def set_parsed(self, instance, input_str):
        instance.__dict__[self.name] = search_attr(self.pattern, input_str, self.non_value) or instance.__dict__[self.name]

    def set_parsed_boolean(self, instance, input_str):
        instance.__dict__[self.name] = search_attr(self.pattern, input_str, self.non_value) is not None

    def set_parsed_list(self, instance, input_str):
        instance.__dict__[self.name] = re.findall(self.pattern, input_str)


class ParsedObject(yaml.YAMLObject):
    template = None
    yaml_tag = u'!Data'
    yaml_flow_style = '|'
    hidden_fields = []

    @classmethod
    def to_yaml(cls, dumper, data):
        new_data = deepcopy(data)
        for item in cls.hidden_fields:
            del new_data.__dict__[item]
        return dumper.represent_yaml_object(cls.yaml_tag, new_data, cls,
                                            flow_style=cls.yaml_flow_style)

    @classmethod
    def from_str(cls, input_str):
        return cls().update(input_str)

    def __str__(self):
        return self.template.format(self)

    def update(self, input_str):
        for attr in self.__dict__:
            getattr(self.__class__, attr).set_parsed(self, input_str)
        return self

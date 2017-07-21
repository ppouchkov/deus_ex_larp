import re

from parsed_object import ParsedObject, ParsedValue


class Program(ParsedObject):
    yaml_tag = u'!Program'
    template = """
--------------------
#{0.code} programm info:
Effect: {0.effect_name}
Inevitable effect: {0.inevitable_effect_name}
Allowed node types:
{0.allowed_node_types_str}
Duration: {0.duration}
END ----------------
"""
    code = ParsedValue('code', re.compile("""#(\d+?) programm info:"""))
    effect_name = ParsedValue('effect_name', re.compile("""Effect: (.*?)\n"""))
    inevitable_effect_name = ParsedValue('inevitable_effect_name', re.compile("""Inevitable effect: (.*?)\n"""))
    allowed_node_types = ParsedValue.list('allowed_node_types', re.compile(""" -([^-].*?)\n"""))
    duration = ParsedValue('duration', re.compile("""Duration: (\d+?)sec"""))

    def __init__(self, code=None, effect_name=None, inevitable_effect_name=None, allowed_node_types=None,
                 duration=None):
        self.code = code
        self.effect_name = effect_name
        self.inevitable_effect_name = inevitable_effect_name
        self.allowed_node_types = allowed_node_types or []
        self.duration = duration

    @property
    def allowed_node_types_str(self):
        return '\n'.join(' -{}'.format(node_type) for node_type in self.allowed_node_types)

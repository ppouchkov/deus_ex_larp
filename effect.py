import re

from parsed_object import ParsedObject, ParsedValue


class Effect(ParsedObject):
    yaml_tag = u'!Effect'
    template = """
--------------------
Info about '{0.name}' effect:
{0.info}
Effect class: '{0.effect_class}'.
END ----------------
"""
    name = ParsedValue('name', re.compile("""Info about '(.*?)' effect:"""))
    info = ParsedValue('info', re.compile("""effect:\n(.*?)Effect class:""", re.MULTILINE | re.DOTALL))
    effect_class = ParsedValue('effect_class', re.compile("""Effect class: (.*?)[.|\n]"""))

    def __init__(self, name=None, info=None, effect_class=None):
        self.name = name
        self.info = info
        self.effect_class = effect_class

import re

from parsed_object import ParsedObject, ParsedValue


class Hacker(ParsedObject):
    yaml_tag = u'!Hacker'
    template = """
--------------------
{0.login} status:
Current target: {0.target}
Current administrating system: {0.adm_system}
Proxy level: {0.proxy_level}
Current proxy address: {0.proxy_address}
END ----------------
"""
    login = ParsedValue('login', re.compile("([\w|\d]+) status:"))
    target_name = ParsedValue('target_name', re.compile("Current target: (.*?)\n"), 'not set')
    adm_system_name = ParsedValue('adm_system_name', re.compile("Current administrating system: (.*?)\n"), 'none')
    no_proxy = ParsedValue.boolean('no_proxy', re.compile("Warning: proxy not available"))
    proxy_level = ParsedValue('proxy_level', re.compile("Proxy level: (\d*?)\n"))
    proxy_address = ParsedValue('proxy_address', re.compile("Current proxy address: (.*?)\n"))

    def __init__(self, login=None, target=None, adm_system=None, no_proxy=None, proxy_level=None, proxy_address=None):
        super(Hacker, self).__init__()
        self.login = login
        self.target = target
        self.adm_system = adm_system
        self.no_proxy = no_proxy
        self.proxy_level = proxy_level
        self.proxy_address = proxy_address

    def update(self, input_str):
        super(Hacker, self).update(input_str)
        if self.no_proxy:
            self.proxy_level = 0
            self.proxy_address = None
        else:
            self.proxy_level = int(self.proxy_level)
        return self

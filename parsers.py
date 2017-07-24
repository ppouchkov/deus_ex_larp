import re

import test_strings
from entities import Status


def search_string(pattern, input_str, none_value=None):
    search = re.search(pattern, input_str)
    if search and search.group(search.lastindex) is not None:
        result = str(search.group(search.lastindex)).strip()
        if result != none_value:
            return result
    return None


def parse_status(input_string):
    target = search_string("Current target: (.*?)\n", input_string, none_value='not set')
    adm_system = search_string("Current administrating system: (.*?)\n", input_string, none_value='none')
    if search_string("(Warning: proxy not available)", input_string):
        proxy_level = 0
        proxy_address = None
    else:
        proxy_level = int(search_string("Proxy level: (\d*?)\n", input_string) or 0)
        proxy_address = search_string("Current proxy address: (.*?)\n", input_string)
    return Status(target, adm_system, proxy_level, proxy_address)



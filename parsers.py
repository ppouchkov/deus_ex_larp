import re

import yaml

import test_strings
from entities import Status, Program, Effect, SystemNode


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


def parse_program(input_string):
    code = int(search_string("#(\d+?) program+ info:", input_string) or 0)
    effect_name = search_string("Effect: (.*?)\n", input_string)
    node_types = [str(elem).strip() for elem in re.findall("- *([^-|\n].*?)\n", input_string)]
    duration = search_string("Duration: (.*?)\n", input_string)
    inevitable_effect_name = search_string("Inevitable effect: (.*?)\n", input_string)
    return Program(code, effect_name, node_types, duration, inevitable_effect_name)


def parse_effect(input_string):
    name = search_string("Info about '(.*?)' effect:", input_string)
    info = search_string(re.compile("""effect:\n(.*?)Effect class:""", re.MULTILINE | re.DOTALL),
                         input_string)
    effect_class = search_string("Effect class: (.*?)[\n|.]", input_string)
    return Effect(name, effect_class, info)


def parse_node_from_short_string(input_string, system):
    name = search_string("(\w+) \(.*?\)", input_string)
    node_type = search_string("\w+ \((.*?)\)", input_string)
    encrypted = search_string("(\*encrypted\*)", input_string) is not None
    program_code = int(search_string("#(\d+)", input_string) or 0)
    disabled = search_string("DISABLED", input_string) is not None
    child_nodes_names = []
    child_nodes_names_str = search_string('"Child nodes: *\[(.*?)\]', input_string)
    if child_nodes_names_str:
        child_nodes_names = [elem.strip() for elem in child_nodes_names_str.split(',')]

    return (
        SystemNode(system, name, encrypted, program_code, node_type, None, disabled, None, True),
        [(name, child_name) for child_name in child_nodes_names]
    )


def parse_node(input_string):
    if search_string("(not available)", input_string):
        system = search_string("(.*?)/.*? not available", input_string)
        name = search_string(".*?/(.*?) not available", input_string)
        return SystemNode(system, name, None, None, None, None, None, None, False)
    available = True
    system = search_string("""Node "(.+?)/.+?" properties:""", input_string)
    name = search_string("""Node ".+?/(.+?)" properties:""", input_string)
    encrypted = search_string("""(Installed program: *encrypted*)""", input_string) is not None
    program_code = int(search_string("""Installed program: #(\d+)""", input_string) or 0)
    node_type = search_string("""Type: (.+?)\n""", input_string)
    node_effect_name = search_string("""Node effect: (.+?)\n""", input_string)
    child_nodes_names = [str(elem).strip() for elem in re.findall("\d+: (.+?)\(", input_string)]
    # child_nodes_short_strings = [str(elem).strip() for elem in re.findall("\d+: (.+?)\n", input_string)]

    return (
        SystemNode(system, name, encrypted, program_code, node_type, node_effect_name, disabled, child_nodes_names, available),
        [(name, child_name) for child_name in child_nodes_names]
    )

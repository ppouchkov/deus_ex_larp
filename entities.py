import os
from copy import deepcopy

import yaml
from graphviz import Digraph


class YAMLObject(yaml.YAMLObject):
    hidden_fields = []

    @classmethod
    def to_yaml(cls, dumper, data):
        new_data = deepcopy(data)
        for item in cls.hidden_fields:
            del new_data.__dict__[item]
        return dumper.represent_yaml_object(cls.yaml_tag, new_data, cls, flow_style=cls.yaml_flow_style)


class Status(YAMLObject):
    yaml_tag = u'!Status'
    __shared_state = {}

    def __init__(self, target, adm_system, proxy_level, proxy_address):
        self.__dict__ = self.__shared_state

        self.target = target
        self.adm_system = adm_system
        self.proxy_level = proxy_level
        self.proxy_address = proxy_address

    def __str__(self):
        return """
--------------------
Current target: {0.target}
Current administrating system: {0.adm_system}
Proxy level: {0.proxy_level}
Current proxy address: {0.proxy_address}
END ----------------
        """.strip().format(self)


class Effect(YAMLObject):
    yaml_tag = u'!Effect'

    def __init__(self, name, effect_class, info=None):
        self.name = name
        self.effect_class = effect_class
        self.info = info

    def __str__(self):
        return """
--------------------
Info about '{0.name}' effect:
{0.info}
Effect class: {0.effect_class}.
END ----------------
        """.strip().format(self)


class Program(YAMLObject):
    yaml_tag = '!Program'

    def __init__(self, code, effect_name, node_types, duration, inevitable_effect_name):
        self.code = code
        self.effect_name = effect_name
        self.node_types = node_types
        self.duration = duration
        self.inevitable_effect_name = inevitable_effect_name

    def __str__(self):
        return """
--------------------
#{0.code} programm info:
Effect: {0.effect_name}
Inevitable effect: {0.inevitable_effect_name}
Allowed node types:
{allowed_node_types_str}
Duration: {0.duration}
END ----------------
        """.strip().format(
            self,
            allowed_node_types_str='\n'.join(' -{}'.format(node_type) for node_type in self.node_types))


class ProgramSet(YAMLObject):
    yaml_tag = '!ProgramSet'

    def __init__(self):
        self.programs = {}

    def find_breakthrough(self, defence):
        pass


class SystemNode(YAMLObject):
    yaml_tag = '!SystemNode'

    def __init__(self, system, name, encrypted, program_code, node_type, node_effect_name, disabled, child_nodes_names,
                 available):
        self.system = system
        self.name = name
        self.encrypted = encrypted
        self.program_code = program_code
        self.node_type = node_type
        self.node_effect_name = node_effect_name
        self.disabled = disabled
        self.child_nodes_names = child_nodes_names or []
        self.available = available

    @property
    def graphviz_style_dict(self):
        return {}


class System(YAMLObject):
    yaml_tag = '!System'

    def __init__(self, name):
        self.name = name
        self.node_graph = {}

    def update_from_folder(self, folder_name, redraw=True):
        for elem in os.listdir(folder_name):
            if not os.path.isfile(os.path.join(folder_name, elem)):
                continue
            if elem.startswith(self.name):
                continue
            with open(os.path.join(folder_name, elem)) as f:
                print os.path.join(folder_name, elem)
                self.add_node(yaml.load(f))
        if redraw:
            self.draw(folder_name)

    def add_node(self, new_node):
        current_node = self.node_graph.setdefault(new_node.name, new_node)
        assert isinstance(current_node, SystemNode)
        current_node.encrypted = new_node.encrypted
        current_node.program_code = new_node.program_code or current_node.program_code
        current_node.node_effect_name = new_node.node_effect_name or current_node.node_effect_name
        current_node.disabled = new_node.disabled
        current_node.child_nodes_names = new_node.child_nodes_names or current_node.child_nodes_names
        current_node.available = new_node.available

    def draw(self, folder_name, view=False):
        dot = Digraph(name=self.name, format='svg')
        dot.attr(size='8')

        node_buffer = [self.node_graph.get('firewall', SystemNode(self.name, 'firewall', *([None]*6 + [True])))]
        edge_buffer = []
        elem_visited = set()
        while node_buffer:
            current_node = node_buffer.pop(0)
            assert isinstance(current_node, SystemNode)
            if current_node.name in elem_visited:
                continue
            elem_visited.add(current_node.name)
            dot.node(current_node.name, **current_node.graphviz_style_dict)
            for child_name in current_node.child_nodes_names:
                node_buffer.append(self.node_graph[child_name])
                edge_buffer.append((current_node.name, child_name))
        for elem in edge_buffer:
            dot.edge(*elem)
        dot.render(self.name, folder_name, view)

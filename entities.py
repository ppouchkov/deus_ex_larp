from copy import deepcopy

import yaml


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


class Program(YAMLObject):
    yaml_tag = '!Program'

    def __init__(self, code, effect_name, node_types):
        self.code = code
        self.effect_name = effect_name
        self.node_types = node_types


class SystemNode(YAMLObject):
    yaml_tag = '!SystemNode'

    def __init__(self, system, name, encrypted, program_code, node_type, node_effect_name, disabled, child_nodes_names):
        self.system = system
        self.name = name
        self.encrypted = encrypted
        self.program_code = program_code
        self.node_type = node_type
        self.node_effect_name = node_effect_name
        self.disabled = disabled
        self.child_nodes_names = child_nodes_names

    @property
    def graphviz_style_dict(self):
        return {}


class System(YAMLObject):
    yaml_tag = '!System'

    @classmethod
    def to_yaml(cls, dumper, data):
        # TODO split graph nodes to files
        return dumper.represent_yaml_object(cls.yaml_tag, data, cls,
                                            flow_style=cls.yaml_flow_style)

    @classmethod
    def from_yaml(cls, loader, node):
        # TODO gather graph node from files
        return loader.construct_yaml_object(node, cls)

    def __init__(self, name):
        self.name = name
        self.node_graph = {}

    def add_node(self):
        pass

    def draw(self, view=False):
        pass

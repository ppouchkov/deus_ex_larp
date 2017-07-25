import ConfigParser
import os
from collections import namedtuple

CONFIG_PATH = 'config'
os.environ["PATH"] += os.pathsep + 'C:/Program Files (x86)/Graphviz2.38/bin/'

config_parser = ConfigParser.RawConfigParser()
config_parser.read(CONFIG_PATH)

JabberUser = namedtuple('JabberUser', ['jid', 'pwd'])

attacker = JabberUser(
    config_parser.get('attacker', 'jid'),
    config_parser.get('attacker', 'pwd'),
)

node_holder = JabberUser(
    config_parser.get('node_holder', 'jid'),
    config_parser.get('node_holder', 'pwd'),
)

data = config_parser.get('global', 'data_folder')

loot_node_types = set(node_type.strip() for node_type
                      in str(config_parser.get('global', 'loot_node_types')).splitlines()
                      if node_type)
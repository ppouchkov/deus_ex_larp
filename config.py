import ConfigParser
from collections import namedtuple

CONFIG_PATH = 'config'

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

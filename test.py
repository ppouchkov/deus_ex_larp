import logging
import os
import shutil
from Queue import Queue
from functools import partial
from threading import Thread
from time import sleep

import test_strings
from client import ResendingClient
from config import data
from entities import TestSystemNode
from parsers import parse_node_from_short_string, dump_program_code, parse_effect, parse_program


class Mocker(object):
    def send_message_to_printer(self, mto, mbody, msubject=None, mtype=None,
                         mhtml=None, mfrom=None, mnick=None, queue=None):
        queue.put(mbody)


test_nodes = {
    'Firewall': TestSystemNode('TestSystem', 'firewall', program_code=dump_program_code(60), node_type='Firewall', node_effect_name='trace'),
    'Antivirus': TestSystemNode('TestSystem', 'green_antivirus', program_code=dump_program_code(60), node_type='Antivirus'),
    'VPN': TestSystemNode('TestSystem', 'black_vpn', program_code=dump_program_code(60), node_type='VPN'),
    'Cryptographic system': TestSystemNode('TestSystem', 'crypto_lock', program_code='*encrypted*', node_type='Cryptographic system'),
    'Bank account': TestSystemNode('TestSystem', 'poor_wallet', program_code=dump_program_code(60), node_type='Bank account'),
    'Data': TestSystemNode('TestSystem', 'data', program_code=dump_program_code(60), node_type='Data'),
}


def print_and_put(instance, message):
    print message
    instance.input_queue.put(message)


def send_reply(instance, message):
    instance.output_buffer.appendleft(message)
    instance.output_queue.put(message)
    while instance.wait_for_reply:
        sleep(0.1)


def test_status():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    sleep(3)
    print_and_put(client, '/status')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.hacker_proxy_not_set)
    print_and_put(client, '/exit')
    print client.current
# test_status()


def test_store():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    print_and_put(client, '/store stored_data test')
    # print '>>> {}'.format(test_queue.get())

    client.message({'body': 'test buffer'})
    print_and_put(client, '/store')
    # print '>>> {}'.format(test_queue.get())
    print_and_put(client, '/exit')
# test_store()


def test_target():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    print_and_put(client, '/target test_system')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    client.input_queue.put('/exit')
    print client.target.name
# test_target()


def test_effect():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    print_and_put(client, '/effect analyze')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_analyze)
    client.input_queue.put('/exit')
# test_effect()


def test_effect_list():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    if os.path.exists('data/effects/analyze'):
        os.remove('data/effects/analyze')
    print_and_put(client, '/effect_list analyze trace')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_analyze)
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_trace)
    client.input_queue.put('/exit')
    assert os.path.exists('data/effects/trace')
    assert os.path.exists('data/effects/analyze')
# test_effect_list()


def test_effect_cache():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    print_and_put(client, '/effect_list trace trace')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_trace)
    client.input_queue.put('/exit')
# test_effect_cache()


def test_info():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    print_and_put(client, '/info #25725')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.command_defence_25725)
    print_and_put(client, '/info #25725')
    client.input_queue.put('/exit')
# test_info()


def test_info_total():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)

    test_progam = test_strings.command_defence_inevitable_template.format(
        code=25725, effect='trace', inevitable_effect='analyze')
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    if os.path.exists('data/effects/analyze'):
        os.remove('data/effects/analyze')

    print_and_put(client, '/info_total #25725')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_progam)
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_trace)
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_analyze)

    client.input_queue.put('/exit')
# test_info_total()


def test_look():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/look firewall')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_nodes['Firewall'].str_enabled())
    print client.target.node_graph['firewall']
    client.input_queue.put('/exit')
# test_look()


def test_look_encrypted():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    test_node = test_nodes['Cryptographic system']
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/look {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    print_and_put(client, '/look {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    test_nodes['Cryptographic system'].program_code = dump_program_code(60)
    send_reply(client, test_node.str_disabled([]))
    print_and_put(client, '/look {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    test_nodes['Cryptographic system'].program_code = '*encrypted*'
    send_reply(client, test_node.str_enabled())

    print client.target.node_graph['crypto_lock'].program_code
    client.input_queue.put('/exit')
# test_look_encrypted()


def test_explore_enabled():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Firewall']
    test_node.program_code = '#25725'
    # print test_node.str_enabled()
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/draw')
    print_and_put(client, '/explore firewall')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.command_defence_25725)
    client.input_queue.put('/exit')
# test_explore_enabled()


def test_explore_disabled():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Firewall']
    test_node.program_code = '#25725'
    # print test_node.str_enabled()
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/draw')
    print_and_put(client, '/explore firewall')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_nodes['Firewall'].str_disabled(
        """0: antivirus1 (Antivirus): #210700 DISABLED\n"""
        """1: antivirus2 (Antivirus): #54480699"""
    ))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.command_defence_25725)
    client.input_queue.put('/exit')
# test_explore_disabled()


def test_explore_encrypted():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Cryptographic system']
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/explore {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    client.input_queue.put('/exit')
# test_explore_encrypted()


def test_check_attack():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    print_and_put(client, '/check_attack 25 25725')
    print_and_put(client, '/check_attack 2 25725')
    print_and_put(client, '/check_attack 25 30')
    client.input_queue.put('/exit')
# test_check_attack()


def test_forward_attack():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    test_node = test_nodes['Firewall']
    test_node.program_code = '#25725'
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/draw')
    print_and_put(client, '/explore {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    print_and_put(client, '/forward_attack #25 firewall')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.attack_reply_success_template.format(
        target=client.target.name, code=3675, defence_code=client.target.node_graph['firewall'].program_code)
    )
    client.input_queue.put('/exit')
# test_forward_attack()


def test_encrypted():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Cryptographic system']
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/explore {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    print_and_put(client, '/forward_attack #{} {}'.format(10, test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.attack_reply_failure_template.format(target='TestSystem', code=10, defence_code=25725))
    print_and_put(client, '/explore {}'.format(test_node.name))
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_node.str_enabled())
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.command_defence_25725)
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_trace)
    client.input_queue.put('/exit')
# test_encrypted()


def test_explore_choice():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Firewall']
    test_node.program_code = '#25725'
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/draw')
    print_and_put(client, '/explore_choice {}'.format(test_node.name))
    sleep(3)
    print_and_put(client, '/0')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_nodes['Firewall'].str_enabled())
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.command_defence_25725)
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.effect_trace)
    client.input_queue.put('/exit')
# test_explore_choice()


def test_explore_choice_flush():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    if os.path.exists('data/programs/#25725'):
        os.remove('data/programs/#25725')
    if os.path.exists('data/effects/trace'):
        os.remove('data/effects/trace')
    if os.path.exists('data/TestSystem'):
        shutil.rmtree('data/TestSystem')
    test_node = test_nodes['Firewall']
    test_node.program_code = '#25725'
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    print_and_put(client, '/draw')
    print_and_put(client, '/explore_choice {}'.format(test_node.name))
    sleep(3)
    print_and_put(client, '/1')
    sleep(5)
    print len(client.choice_buffer)
    print_and_put(client, '/status')
    print '>>> {}'.format(test_queue.get())
    client.output_queue.put(test_strings.hacker_first)
    client.input_queue.put('/exit')
# test_explore_choice_flush()


def test_attack_choice():
    test_queue = Queue()
    client = ResendingClient(start=False)
    client.send_message = partial(Mocker().send_message_to_printer, queue=test_queue)
    current_folder = os.path.join(data, 'effects')
    dump_handler = partial(client.dump_reply_handler,
                                   folder=current_folder,
                                   file_name_getter=lambda x: '{0.name}'.format(x),
                                   parser=parse_effect)
    dump_handler(test_strings.effect_analyze)
    dump_handler(test_strings.effect_trace)
    dump_handler(test_strings.effect_disable)
    dump_handler(test_strings.effect_get_data)
    dump_handler(test_strings.effect_logname)
    dump_handler(test_strings.effect_minor_fraud)
    dump_handler(test_strings.effect_read_data)

    current_folder = os.path.join(data, 'programs')
    dump_handler = partial(client.dump_reply_handler,
                           folder=current_folder,
                           file_name_getter=lambda x: dump_program_code(x.code),
                           parser=parse_program)

    dump_handler(test_strings.command_attack_disable_template.format(code=2))
    dump_handler(test_strings.command_attack_disable_template.format(code=3))
    dump_handler(test_strings.command_attack_disable_template.format(code=10))
    dump_handler(test_strings.command_attack_disable_template.format(code=15))
    dump_handler(test_strings.command_attack_disable_template.format(code=25))
    dump_handler(test_strings.command_attack_disable_template.format(code=30))
    dump_handler(test_strings.command_attack_get_data_template.format(code=4))
    dump_handler(test_strings.command_attack_get_data_template.format(code=9))
    dump_handler(test_strings.command_attack_read_data_template.format(code=16))
    dump_handler(test_strings.command_attack_minor_fraud_template.format(code=27))
    dump_handler(test_strings.command_attack_minor_fraud_template.format(code=32))

    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    test_node = test_nodes['Firewall']
    test_node.program_code = 27 * 117 * 2 * 3 * 10 * 15 * 25 * 30 * 16
    client.target.add_node(test_node)
    client.cmd_attack_choice(test_node.name)
    sleep(3)
    print_and_put(client, '/3')
    sleep(3)
    print_and_put(client, '/6')
    sleep(3)
    #
    #
    print_and_put(client, '/target TestSystem')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, 'ok')
    test_node = test_nodes['Data']
    test_node.program_code = 27 * 117 * 2 * 3 * 10 * 15 * 25 * 30 * 16
    client.target.add_node(test_node)
    client.cmd_attack_choice(test_node.name)
    sleep(3)
    print_and_put(client, '/0')
    print '>>> {}'.format(test_queue.get())
    send_reply(client, test_strings.attack_reply_read_data_success.format(code=16, defence_code=test_node.program_code, target='TestSystem'))
    sleep(3)
    print_and_put(client, '/store')
    sleep(5)
    client.input_queue.put('/exit')
test_attack_choice()

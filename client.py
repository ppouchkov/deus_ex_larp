#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import os
import threading
from Queue import Queue
from collections import deque
from functools import partial
from time import sleep

import sleekxmpp
import yaml

from check_rule import check_rule
from config import attacker, node_holder, data
from entities import System, Program, AttackReply, SystemNode
from parsers import parse_status, parse_program, parse_effect, parse_node, parse_attack_reply, parse_diagnostics, \
    parse_program_code, dump_program_code, parse_node_from_short_string
from utils import stable_write, cache_check


logging.basicConfig(level=20, filename='data/logs',
                    format='[%(asctime)s][%(levelname)s][%(threadName)s][%(funcName)s]%(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S", filemode='w')


def make_command(is_blocking, handler):
    def wrapped(command_method):
        def wrapper(instance, *args, **kwargs):
            try:
                logging.info('> start {}({}{}{})'.format(
                    command_method.__name__,
                    ', '.join(str(arg) for arg in args),
                    ', ' if kwargs else '',
                    ', '.join('{}={}'.format(k, kwargs[k]) for k in kwargs)))
                assert isinstance(instance, ResendingClient)
                if is_blocking and not instance.disable_locks:
                    instance.wait_for_reply = True
                if handler:
                    instance.reply_handler = getattr(instance, handler)
                else:
                    instance.reply_handler = getattr(instance, 'default_reply_handler')
                message = command_method(instance, *args, **kwargs)
                if message:
                    delta = (instance.last_command_sent + instance.sending_delay - datetime.datetime.now()
                             ).total_seconds()
                    if delta > 0:
                        sleep(delta)
                    logging.info('>>> {}'.format(message))
                    instance.send_message(instance.recipient, message, mtype='chat')
                    instance.last_command_sent = datetime.datetime.now()
                wait_start = datetime.datetime.now()
                while instance.wait_for_reply:
                    if datetime.datetime.now() > wait_start + datetime.timedelta(seconds=ResendingClient.wait_for_reply_max):
                        th_name = threading.current_thread().name
                        raise ValueError('Waited too long in {}'.format(th_name))
                    sleep(ResendingClient.wait_rate)
            except Exception as e:
                print 'CMD ERROR: {}'.format(str(e))
                logging.exception('CMD {} ERROR: {}'.format(command_method.__name__, str(e)))
            finally:
                logging.info('> finish {}({}{}{})'.format(
                    command_method.__name__,
                    ', '.join(str(arg) for arg in args),
                    ', ' if kwargs else '',
                    ', '.join('{}={}'.format(k, kwargs[k]) for k in kwargs)))
        return wrapper
    return wrapped


def make_reply_handler():
    def wrapped(handler_method):
        def wrapper(instance, message, **kwargs):
            result = None
            try:
                logging.info('< {}'.format(threading.current_thread().name))
                logging.info('< start {}({})'.format(
                    handler_method.__name__,
                    ', '.join('{}={}'.format(k, kwargs[k]) for k in kwargs)))
                logging.info('<<< {}'.format(message))
                assert isinstance(instance, ResendingClient)
                result = handler_method(instance, message, **kwargs)
            except Exception as e:
                print 'HANDLER ERROR: {}'.format(str(e))
                logging.exception('HANDER {} ERROR: {}'.format(handler_method.__name__, str(e)))
            finally:
                instance.wait_for_reply = False
                instance.reply_handler = getattr(instance, 'default_reply_handler')
                logging.info('< finish {}({})'.format(
                    handler_method.__name__,
                    ', '.join('{}={}'.format(k, kwargs[k]) for k in kwargs)))
            return result
        return wrapper
    return wrapped


class ResendingClient(sleekxmpp.ClientXMPP):
    greeting_message = 'The very first test {}'.format(datetime.datetime.now())
    sending_delay = datetime.timedelta(seconds=1)

    disable_locks = False

    wait_for_reply = False
    wait_for_reply_max = 60 * 5
    wait_rate = 0.5

    @classmethod
    def _is_internal_command(cls, input_str):
        return str(input_str).startswith('/')

    def message_read_from_stdin(self):
        threading.current_thread().name = 'Reader'
        logging.info('{} started'.format(threading.current_thread().name))
        while True:
            message = raw_input()
            self.input_queue.put(message)
            if message == '/exit':
                break
        logging.info('{} exited'.format(threading.current_thread().name))

    def message_process(self):
        logging.info('{} started'.format(threading.current_thread().name))
        threading.current_thread().name = 'Processor'
        while True:
            message = self.input_queue.get()
            if message == '/exit':
                logging.info('forward /exit')
                self.output_queue.put(message)
                break
            if not self._is_internal_command(message):
                delta = (self.last_command_sent + self.sending_delay - datetime.datetime.now()).total_seconds()
                if delta > 0:
                    sleep(delta)
                logging.info('>>> {}'.format(message))
                self.send_message(self.recipient, message, mtype='chat')
                self.last_command_sent = datetime.datetime.now()
                continue
            message_split = message.split()
            command, args = message_split[0].strip('/'), message_split[1:]
            if command == 'flush_choice':
                self.cmd_flush_choice()
                continue
            if self.choice_buffer and str(command).isdigit():
                try:
                    next_command = self.choice_buffer[int(command)]
                    self.cmd_flush_choice()
                    self.input_queue.put(next_command)
                    continue
                except Exception as e:
                    print 'ERROR parsing choice {}: {}'.format(message, str(e))
                    print 'Flush choice buffer'
                    logging.exception('ERROR parsing choice {}: {}'.format(message, str(e)))
                    self.cmd_flush_choice()
            if hasattr(self, 'cmd_{}'.format(command)):
                getattr(self, 'cmd_{}'.format(command))(*args)
            else:
                print 'No such command {}'.format(command)
        logging.info('{} exited'.format(threading.current_thread().name))

    def message_reply_parser(self):
        try:
            logging.info('{} started'.format(threading.current_thread().name))
            threading.current_thread().name = 'ReplyParser'
            while True:
                message = self.output_queue.get()
                logging.info('got "{}{}"'.format(message.replace('\n', '\\n ')[:20], len(message) > 20 and '...' or ''))
                if message == '/exit':
                    break
                print self.reply_handler(message)
                self.wait_for_reply = False
            self.close()
            logging.info('{} exited'.format(threading.current_thread().name))
        except:
            logging.exception('on message reply parsing')
            raise

    def __init__(self, start=True):
        sleekxmpp.ClientXMPP.__init__(self, attacker.jid, attacker.pwd)
        if not os.path.exists(os.path.join(data, 'effects')):
            print 'create folder {}'.format(os.path.join(data, 'effects'))
            os.mkdir(os.path.join(data, 'effects'))
        if not os.path.exists(os.path.join(data, 'programs')):
            print 'create folder {}'.format(os.path.join(data, 'programs'))
            os.mkdir(os.path.join(data, 'programs'))

        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199')  # XMPP Ping

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.last_command_sent = datetime.datetime.now()
        self.recipient = node_holder.jid
        self.input_queue = Queue()
        self.output_queue = Queue()
        self.choice_buffer = []
        self.output_buffer = deque([], maxlen=5)

        self.reply_handler = self.default_reply_handler

        self.current = None
        self.target = None

        if start:
            self.start()
        else:
            self._start_thread("Processor", self.message_process)
            self._start_thread("ReplyParser", self.message_reply_parser)

    def start(self):
        if self.connect():
            self.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")

    def session_start(self, event):
        self.send_presence()
        self.get_roster()
        self._start_thread("Reader", self.message_read_from_stdin)
        self._start_thread("Processor", self.message_process)
        self._start_thread("ReplyParser", self.message_reply_parser)
        sleep(3)
        self.input_queue.put(self.greeting_message)

    def message(self, msg):
        # TODO check from
        try:
            self.output_buffer.appendleft(msg['body'])
            self.output_queue.put(msg['body'])
        except:
            logging.exception('on message recived: {}'.format(msg['body']))

    def add_choice(self, command):
        current_choice = len(self.choice_buffer)
        self.choice_buffer.append(command)
        print '    [{}] {}'.format(current_choice, command)

    @make_reply_handler()
    def default_reply_handler(self, message):
        return message

    def close(self):
        print 'disconnect'
        self.disconnect(wait=True)

    @make_command(is_blocking=False, handler=None)
    def cmd_store(self, file_name='stored_data', content=None):
        current_content = content or self.output_buffer[0]
        current_folder = self.target and os.path.join(data, self.target.name) or data
        stable_write(current_folder, file_name, '\n' + '='*20 + '\n', mode='a')
        stable_write(current_folder, file_name, current_content, mode='a')

    @make_command(is_blocking=True, handler=None)
    def cmd_target(self, system):
        assert system, 'Specify system name'
        self.reply_handler = partial(self.target_reply_handler, target_name=system)
        return 'target {}'.format(system)

    @make_reply_handler()
    def target_reply_handler(self, message, target_name):
        target_folder = os.path.join(data, target_name)
        if message.strip() != 'ok':
            return 'target failed with message:\n{}'.format(message)
        if not os.path.exists(target_folder):
            os.mkdir(target_folder)
        self.target = System(target_name)
        self.target.node_graph['firewall'] = SystemNode(target_name, 'firewall', *[None]*6+[True, ])
        self.target.update_from_folder(target_folder, redraw=True)
        return 'new target: {}'.format(target_name)

    @make_command(is_blocking=False, handler=None)
    def cmd_draw(self, system_name=None):
        target = system_name and System(system_name) or self.target
        if target:
            target.update_from_folder('{}/{}'.format(data, target.name), redraw=True)
            target.draw('{}/{}'.format(data, target.name), view=True)
            print 'Draw: ok'
        else:
            logging.error('Specify target')
            print 'Specify target'

    @make_command(is_blocking=True, handler='status_reply_handler')
    def cmd_status(self):
        return 'status'

    @make_reply_handler()
    def status_reply_handler(self, message):
        self.current = parse_status(message)
        return str(self.current)

    @make_command(is_blocking=True, handler=None)
    def cmd_effect(self, effect_name, verbose=True):
        current_folder = os.path.join(data, 'effects')
        effect = cache_check(current_folder, effect_name)
        if effect:
            print 'cache hit: {}'.format(effect_name)
            logging.info('cache hit: {}'.format(effect_name))
            self.wait_for_reply = False
            if verbose:
                print effect
        elif effect is None:
            print 'cache miss: {}'.format(effect_name)
            logging.info('cache miss: {}'.format(effect_name))
            self.reply_handler = partial(self.dump_reply_handler,
                                         folder=current_folder,
                                         file_name_getter=lambda x: '{0.name}'.format(x),
                                         parser=parse_effect)
            return 'effect {}'.format(effect_name)

    @make_command(is_blocking=False, handler=None)
    def cmd_effect_list(self, *effect_names):
        for effect_name in effect_names:
            self.cmd_effect(effect_name.strip(','))

    @make_command(is_blocking=True, handler=None)
    def cmd_info(self, program_code, verbose=True):
        current_code = parse_program_code(program_code)
        if current_code is None:
            print 'wrong code: {}'.format(program_code)
            return
        current_folder = os.path.join(data, 'programs')

        program = cache_check(current_folder, dump_program_code(current_code))
        if program:
            print 'cache hit: {}'.format(current_code)
            logging.info('cache hit: {}'.format(current_code))
            self.wait_for_reply = False
            if verbose:
                print program
        else:
            print 'cache miss: {}'.format(current_code)
            logging.info('cache miss: {}'.format(current_code))
            self.reply_handler = partial(self.dump_reply_handler,
                                         folder=current_folder,
                                         file_name_getter=lambda x: dump_program_code(x.code),
                                         parser=parse_program)
            return 'info {}'.format(dump_program_code(current_code))

    @make_command(is_blocking=False, handler=None)
    def cmd_info_total(self, program_code, verbose=False):
        current_folder = os.path.join(data, 'programs')
        self.cmd_info(program_code, verbose)
        program = cache_check(current_folder, dump_program_code(program_code))
        if program.effect_name:
            self.cmd_effect(program.effect_name, verbose=False)
        if program.inevitable_effect_name:
            self.cmd_effect(program.inevitable_effect_name, verbose=False)

    @make_command(is_blocking=False, handler=None)
    def cmd_info_list(self, *program_codes, **kwargs):
        program_codes = [code.strip(' ,\n') for code in program_codes]
        for program_code in program_codes:
            self.cmd_info_total(program_code, kwargs.get('verbose', True))
            sleep(1)
        print 'finish batch_info {}'.format(len(program_codes))

    @make_command(is_blocking=False, handler=None)
    def cmd_info_file(self, file_name, verbose=False):
        with open(os.path.join(data, file_name)) as f:
            self.cmd_info_list(*f.readlines(), verbose=verbose)

    @make_reply_handler()
    def dump_reply_handler(self, message, folder, file_name_getter, parser):
        try:
            obj = parser(message)
            stable_write(folder, file_name_getter(obj), yaml.dump(obj, default_style='|'), 'w')
        except Exception as e:
            logging.exception('DUMP ERROR: {}'.format(str(e)))
            return 'DUMP ERROR: {}'.format(str(e))
        if self.target:
            target_folder = os.path.join(data, self.target.name)
            self.target.update_from_folder(target_folder, redraw=True)
        return message

    @make_command(is_blocking=True, handler='look_reply_handler')
    def cmd_look(self, system_node_name):
        if self.target is None:
            print 'Specify target'
            return None
        return 'look {}'.format(system_node_name)

    @make_reply_handler()
    def look_reply_handler(self, message):
        system_node, system_node_child_strings = parse_node(message)
        if self.target.name != system_node.system:
            return 'target mismatch: target ({}) node ({})'.format(self.target.name, system_node.system)
        current_folder = '{}/{}'.format(data, self.target.name)
        self.target.update_from_folder(current_folder, redraw=False)
        self.target.add_node(system_node)
        names_to_dump = [system_node.name, ]
        for child_node_string in system_node_child_strings:
            child_node = parse_node_from_short_string(child_node_string, system_node.system)[0]
            self.target.add_node(child_node)
            names_to_dump.append(child_node.name)
        for name in names_to_dump:
            stable_write(current_folder, name, yaml.dump(self.target.node_graph[name], default_style='|'), 'w')
        self.target.update_from_folder(current_folder, redraw=True)
        return message

    @make_command(is_blocking=False, handler=None)
    def cmd_explore(self, system_node_name='firewall'):
        self.cmd_look(system_node_name)
        print 'verified code: {}'.format(self.target.node_graph[system_node_name].program_code or '*encrypted*')
        if self.target.node_graph[system_node_name].program_code:
            self.cmd_info_total(self.target.node_graph[system_node_name].program_code, verbose=False)
        if self.target.node_graph[system_node_name].node_effect_name:
            self.cmd_effect(self.target.node_graph[system_node_name].node_effect_name, verbose=False)

    @make_command(is_blocking=False, handler=None)
    def cmd_explore_recursive(self, system_node_name='firewall'):
        assert self.target, 'Specify target'
        node_buffer = [self.target.node_graph[system_node_name]]
        elem_visited = set()
        while node_buffer:
            current_node = node_buffer.pop(0)
            if current_node.name in elem_visited:
                continue
            self.cmd_explore(current_node.name)
            elem_visited.add(current_node.name)
            for child_name in current_node.child_nodes_names:
                if self.target.node_graph[current_node.name].disabled and \
                        self.target.node_graph[current_node.name].available:
                    node_buffer.append(self.target.node_graph[child_name])

    @make_command(is_blocking=False, handler=None)
    def cmd_check_attack(self, attack_code, defence_code):
        current_folder = os.path.join(data, 'programs')
        current_attack_code = dump_program_code(attack_code)
        current_defence_code = dump_program_code(defence_code)
        with open(os.path.join(current_folder, current_attack_code)) as fa:
            attack = yaml.load(fa)
        with open(os.path.join(current_folder, current_defence_code)) as fd:
            defence = yaml.load(fd)
        if check_rule(attack.code, defence.code):
            print 'Attack {} is valid against {}'.format(attack.code, defence.code)
        else:
            print 'WARNING: Attack {} is NOT valid against {}'.format(attack.code, defence.code)

    @make_command(is_blocking=True, handler=None)
    def cmd_forward_attack(self, attack_code, system_node):
        self.reply_handler = partial(self.forward_attack_reply_handler, system_node=system_node)
        return '{} {}'.format(dump_program_code(attack_code), system_node)

    @make_reply_handler()
    def forward_attack_reply_handler(self, message, system_node):
        attack_reply = parse_attack_reply(message)
        assert isinstance(attack_reply, AttackReply)
        current_node = self.target.node_graph[system_node]
        assert isinstance(current_node, SystemNode)
        current_node.available = attack_reply.new_available
        current_node.disabled = attack_reply.new_disabled
        if attack_reply.new_defence:
            current_node.program_code = attack_reply.new_defence
        return message

    @make_command(is_blocking=False, handler=None)
    def cmd_explore_choice(self, system_node='firewall', command='explore'):
        current_node = self.target.node_graph[system_node]
        self.add_choice('/{} {}'.format(command, system_node))
        for child_name in current_node.child_nodes_names:
            self.add_choice('/{} {}'.format(command, child_name))
        self.add_choice('/flush_choice')

    @make_command(is_blocking=False, handler=None)
    def cmd_attack_choice(self, system_node, effect_filter='all', limit_for_effect=3, choice_template=None):
        default_choice_template = '/forward_attack {code} {node_name}'
        extend_choice_template = '/attack_choice {system_node} {effect_filter} {limit_for_effect}{choice_template}'
        current_choice_template = choice_template or default_choice_template
        current_folder = os.path.join(data, 'programs')
        current_node = self.target.node_graph[system_node]
        print 'Current node: {} {} {}'.format(current_node.name, current_node.node_type,
                                              current_node.program_code or 'Unknown')
        if not current_node.program_code:
            print 'Best Guess:'
            result_code = self.attack_best_guess()
            self.add_choice(default_choice_template.format(code=result_code, node_name=system_node))
        else:
            result = {}
            for program_file in os.listdir(current_folder):
                if not program_file.startswith('#'):
                    continue
                with open(os.path.join(current_folder, program_file)) as f:
                    current_program = yaml.load(f)
                    assert isinstance(current_program, Program)
                    if current_node.node_type not in set(current_program.node_types):
                        continue
                    if not check_rule(current_program.code, current_node.program_code):
                        continue
                    result.setdefault(current_program.effect_name, []).append(current_program)
            for effect_name in [effect_name for effect_name in result
                                if effect_filter == 'all' or effect_filter == effect_name]:
                print 'Effect: {}'.format(effect_name)
                for i in range(min(limit_for_effect, len(result[effect_name]))):
                    self.add_choice(current_choice_template.format(code=result[effect_name][i].code, node_name=system_node))
                if limit_for_effect < len(result[effect_name]):
                    self.add_choice(extend_choice_template.format(
                        system_node=system_node,
                        effect_filter=effect_filter,
                        limit_for_effect=len(result[effect_name]),
                        choice_template=choice_template and ' {}'.format(extend_choice_template) or ''
                    ))
        print 'Default:'
        self.add_choice('/flush_choice')

    @make_command(is_blocking=False, handler=None)
    def cmd_flush_choice(self):
        self.choice_buffer = []
        self.wait_for_reply = False

    @make_command(is_blocking=False, handler=None)
    def cmd_atk(self, system_node='firewall'):
        self.cmd_explore(system_node)
        current_node = self.target.node_graph[system_node]
        if not current_node.available:
            print 'node {} unavailable'.format(system_node)
            return
        if current_node.disabled:
            self.cmd_explore_choice(system_node, 'atk')
        else:
            self.cmd_attack_choice(system_node)

    def attack_best_guess(self, effect_filter='all'):
        return 0

    @make_command(is_blocking=False, handler=None)
    def cmd_trace_route(self, target_sytem_node_name):
        start_system_node_name = 'firewall'
        pass

    @make_command(is_blocking=False, handler=None)
    def cmd_parse_diagnostics(self, file_name, skip_codes=False):
        current_path = os.path.join(data, file_name)
        with open(current_path) as f:
            lines = '\n'.join(f.readlines())
        system = parse_diagnostics(lines)
        print 'parsed {} nodes'.format(len(system.node_graph))
        if not skip_codes:
            for code in [node.program_code for node in system.node_graph.itervalues() if node.program_code]:
                self.cmd_info_total(code, verbose=False)
        system.dump_to_folder(os.path.join(data, system.name))
        system.draw(os.path.join(data, system.name), view=True)

if __name__ == '__main__':
    rc = ResendingClient()

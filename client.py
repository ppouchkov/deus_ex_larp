#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import logging
import os
from collections import deque
from functools import partial, wraps
from time import sleep

import sleekxmpp
import yaml

from check_rule import check_rule
from config import attacker, node_holder, data
from entities import System, Program, AttackReply, SystemNode
from parsers import parse_status, parse_program, parse_effect, parse_node, parse_attack_reply


def make_command(is_blocking, handler):
    def wrapped(command_method):
        def wrapper(instance, *args, **kwargs):
            try:
                logging.info('> {}({}{}{})'.format(
                    command_method.__name__,
                    ', '.join(args),
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
                    logging.info('>>> {}'.format(message))
                    instance.forward_message(message)
                wait_start = datetime.datetime.now()
                while instance.wait_for_reply:
                    if datetime.datetime.now() > wait_start + datetime.timedelta(seconds=ResendingClient.wait_for_reply_max):
                        raise ValueError('Waited too long')
                    sleep(ResendingClient.wait_rate)
            except Exception as e:
                print 'CMD ERROR: {}'.format(str(e))
                logging.exception('CMD {} ERROR: {}'.format(command_method.__name__, str(e)))
        return wrapper
    return wrapped


def make_reply_handler():
    def wrapped(handler_method):
        def wrapper(instance, message, **kwargs):
            try:
                logging.info('> {}({})'.format(
                    handler_method.__name__,
                    ', '.join('{}={}'.format(k, kwargs[k]) for k in kwargs)))
                logging.info('<<< {}'.format(message))
                assert isinstance(instance, ResendingClient)
                result = handler_method(instance, message, **kwargs)
                instance.wait_for_reply = False
                return result
            except Exception as e:
                print 'HANDLER ERROR: {}'.format(str(e))
                logging.exception('HANDER {} ERROR: {}'.format(handler_method.__name__, str(e)))
        return wrapper
    return wrapped


class ResendingClient(sleekxmpp.ClientXMPP):
    greeting_message = 'The very first test {}'.format(datetime.datetime.now())
    sending_delay = datetime.timedelta(seconds=1)

    disable_locks = False

    wait_for_reply = False
    wait_for_reply_max = 60
    wait_rate = 0.5

    @classmethod
    def _is_internal_command(cls, input_str):
        return str(input_str).startswith('/')

    def read_stdin(self):
        while True:
            message = raw_input()
            self.forward_message(message)
            if message == '/exit':
                break
        print 'Reader exited'

    def __init__(self, start=True):
        sleekxmpp.ClientXMPP.__init__(self, attacker.jid, attacker.pwd)
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199')  # XMPP Ping

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.last_command_sent = datetime.datetime.now()
        self.recipient = node_holder.jid
        self.input_buffer = deque([], 5)
        self.output_buffer = deque([], 5)
        self.choice_buffer = []

        self.reply_handler = self.default_reply_handler

        self.current = None
        self.target = None

        if start:
            self.start()

    def start(self):
        if self.connect():
            self.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")

    def session_start(self, event):
        self.send_presence()
        self.get_roster()

        self._start_thread("input", self.read_stdin)

        self.forward_message(self.greeting_message)

    def forward_message(self, message):
        if message == '/exit':
            self.close()
            return
        self.input_buffer.appendleft(message)
        delta = (self.last_command_sent + self.sending_delay - datetime.datetime.now()).total_seconds()
        if delta > 0:
            sleep(delta)
        if not self._is_internal_command(message):
            self.send_message(self.recipient, message, mtype='chat')
            self.last_command_sent = datetime.datetime.now()
            return

        message_split = message.split()
        command, args = message_split[0].strip('/'), message_split[1:]
        if self.choice_buffer and not command == 'flush_choice':
            try:
                next_command = self.choice_buffer[int(command)]
                self.choice_buffer = []
                self.forward_message(next_command)
            except Exception as e:
                print 'ERROR parsing choice {}: {}'.format(message, str(e))
                print 'Flush choice buffer'
                self.choice_buffer = []
            return
        elif command == 'flush_choice':
            self.cmd_flush_choice()
        if hasattr(self, 'cmd_{}'.format(command)):
            getattr(self, 'cmd_{}'.format(command))(*args)
        else:
            print 'No such command {}'.format(command)
        self.last_command_sent = datetime.datetime.now()

    def message(self, msg):
        self.output_buffer.appendleft(self.reply_handler(msg['body']))
        print self.output_buffer[0]

    @make_reply_handler()
    def default_reply_handler(self, message):
        return message

    def close(self):
        print 'disconnect'
        self.disconnect(wait=True)

    @make_command(is_blocking=True, handler=None)
    def cmd_target(self, system):
        assert system, 'Specify system name'
        self.reply_handler = partial(self.target_reply_handler, target_name=system)
        return 'target {}'.format(system)

    @make_reply_handler()
    def target_reply_handler(self, message, target_name):
        target_folder = os.path.join(data, target_name)
        if message.strip() != 'ok':
            return ' target failed with message:\n{}'.format(message)
        if not os.path.exists(target_folder):
            os.mkdir(target_folder)
        self.target = System(target_name)
        self.target.node_graph['firewall'] = SystemNode(target_name, 'firewall', *[None]*6+[True, ])
        self.target.update_from_folder(target_folder, redraw=True)
        return 'new target: {}'.format(target_name)

    @make_command(is_blocking=False, handler=None)
    def cmd_draw(self, system=None, view=True):
        if system:
            target = System(system)
            target.update_from_folder('{}/{}'.format(data, system), redraw=True)
        else:
            target = self.target
        if target:
            target_folder = '{}/{}'.format(data, target.name)
            target.draw(target_folder, view)
            print 'Draw: ok'
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
        if not os.path.exists(current_folder):
            print 'create folder {}'.format(current_folder)
            os.mkdir(current_folder)
        if not os.path.exists(os.path.join(current_folder, effect_name)):
            print 'Cache miss'
            self.reply_handler = partial(self.dump_reply_handler,
                                         folder=current_folder,
                                         file_name_getter=lambda x: '{0.name}'.format(x),
                                         parser=parse_effect)
            return 'effect {}'.format(effect_name)
        elif verbose:
            with open(os.path.join(current_folder, effect_name)) as f:
                print 'Cache hit'
                print yaml.load(f)

    @make_command(is_blocking=True, handler=None)
    def cmd_info(self, program_code, verbose=True):
        current_code = None
        current_folder = os.path.join(data, 'programs')
        if isinstance(program_code, basestring) and str(program_code).startswith('#'):
            program_code = program_code.strip('#')
        if isinstance(program_code, basestring) and str(program_code).isdigit():
            current_code = int(program_code)
        elif isinstance(program_code, int):
            current_code = program_code
        if current_code is None:
            print 'wrong code: {}'.format(program_code)
            return

        if not os.path.exists(current_folder):
            print 'create folder {}'.format(current_folder)
            os.mkdir(current_folder)

        if not os.path.exists(os.path.join(current_folder, '#{}'.format(current_code))):
            self.reply_handler = partial(self.dump_reply_handler,
                                         folder=current_folder,
                                         file_name_getter=lambda x: '#{0.code}'.format(x),
                                         parser=parse_program)
            return 'info #{}'.format(current_code)
        elif verbose:
            logging.info('<<< cached #{} '.format(program_code))
            with open(os.path.join(current_folder, '#{}'.format(current_code))) as f:
                print yaml.load(f)
        return None

    @make_command(is_blocking=False, handler=None)
    def cmd_info_total(self, program_code, verbose=True):
        self.cmd_info(program_code, verbose)
        with open(os.path.join(data, 'programs', '#{}'.format(program_code))) as f:
            current_program = yaml.load(f)
        if current_program.effect_name:
            self.cmd_effect(current_program.effect_name, verbose=False)
        if current_program.inevitable_effect_name:
            self.cmd_effect(current_program.inevitable_effect_name, verbose=False)

    @make_command(is_blocking=False, handler=None)
    def cmd_batch_info(self, *program_codes, **kwargs):
        program_codes = [code.strip(' ,\n') for code in program_codes]
        for program_code in program_codes:
            self.cmd_info_total(program_code, kwargs.get('verbose', True))
            sleep(1)
        print 'finish batch_info {}'.format(len(program_codes))

    def cmd_file_info(self, file_name, verbose=False):
        with open(os.path.join(data, file_name)) as f:
            self.cmd_batch_info(*f.readlines(), verbose=verbose)

    @make_reply_handler()
    def dump_reply_handler(self, message, folder, file_name_getter, parser):
        try:
            obj = parser(message)
            with open(os.path.join(folder, file_name_getter(obj)), 'w') as f:
                yaml.dump(obj, f, default_style='|')
        except Exception as e:
            return 'ERROR: {}'.format(str(e))
        if self.target:
            target_folder = os.path.join(data, self.target.name)
            self.target.update_from_folder(target_folder, redraw=True)
        return message

    @make_command(is_blocking=False, handler=None)
    def cmd_store(self, file_name='stored_data'):
        if self.target is None:
            current_folder = data
        else:
            current_folder = os.path.join(data, self.target.name)
        try:
            f = open(os.path.join(current_folder, file_name), "a", 0)
            f.write(self.output_buffer[0])
            f.close()
        except IOError as (errno, strerror):
            print "I/O error({0}): {1}".format(errno, strerror)

    @make_command(is_blocking=True, handler='look_reply_handler')
    def cmd_look(self, system_node_name):
        if self.target is None:
            print 'Specify target'
            return None
        return 'look {}'.format(system_node_name)

    @make_reply_handler()
    def look_reply_handler(self, message):
        system_node, _ = parse_node(message)
        if self.target.name != system_node.system:
            return 'target mismatch: target ({}) node ({})'.format(self.target.name, system_node.system)
        result = self.dump_reply_handler(
            message,
            folder='{}/{}'.format(data, self.target.name),
            file_name_getter=lambda obj: obj.name,
            parser=lambda m: parse_node(m)[0]
        )
        return result

    @make_command(is_blocking=False, handler=None)
    def cmd_explore(self, system_node_name='firewall', attack=False):
        self.cmd_look(system_node_name)
        if self.target.node_graph[system_node_name].program_code:
            self.cmd_info_total(self.target.node_graph[system_node_name].program_code, verbose=False)
        if self.target.node_graph[system_node_name].node_effect_name:
            self.cmd_effect(self.target.node_graph[system_node_name].node_effect_name, verbose=False)
        if attack:
            self.cmd_attack_choice(system_node_name)

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
        current_attack_code = str(attack_code).isdigit() and '#{}'.format(attack_code) or attack_code
        current_defence_code = str(defence_code).isdigit() and '#{}'.format(defence_code) or defence_code
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
        self.reply_handler = partial(self.attack_reply_handler, system_node=system_node)
        return '#{} {}'.format(attack_code, system_node)

    @make_reply_handler()
    def attack_reply_handler(self, message, system_node):
        attack_reply = parse_attack_reply(message)
        assert isinstance(attack_reply, AttackReply)
        current_node = self.target.node_graph[system_node]
        assert isinstance(current_node, SystemNode)
        current_node.available = attack_reply.new_available
        current_node.disabled = attack_reply.new_disabled
        if attack_reply.new_defence:
            current_node.program_code = attack_reply.new_defence
        if attack_reply.success:
            self.cmd_explore_choice(system_node)
        return '{}\n{}'.format(message, '\n    - '.join(attack_reply.warning))

    @make_command(is_blocking=False, handler=None)
    def cmd_explore_choice(self, system_node='firewall'):
        current_node = self.target.node_graph[system_node]
        self.choice_buffer.append('/explore {} attack'.format(system_node))
        for child_name in current_node.child_nodes_names:
            self.choice_buffer.append('/explore {} attack}'.format(child_name))
        self.choice_buffer.append('/flush_choice')
        for current_choice, command in enumerate(self.choice_buffer):
            print '    [{}] {}'.format(current_choice, command)

    @make_command(is_blocking=False, handler=None)
    def cmd_attack_choice(self, system_node, effect_filter='all', limit_for_effect=3):
        current_folder = os.path.join(data, 'programs')
        current_node = self.target.node_graph[system_node]
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
        current_choice = 0
        for effect_name in [effect_name for effect_name in result
                            if effect_filter == 'all' or effect_filter == effect_name]:
            print 'Effect: {}'.format(effect_name)
            for i in range(min(limit_for_effect, len(result[effect_name]))):
                next_command = '/forward_attack {} {}'.format(result[effect_name][i].program_code, system_node)
                self.choice_buffer.append(next_command)
                print '    [{}] {}'.format(current_choice, next_command)
                current_choice += 1
            if limit_for_effect < len(result[effect_name]):
                next_command = '/find_attack {} {}'.format(system_node, effect_name, len(result[effect_name]))
                self.choice_buffer.append(next_command)
                print '    [{}] {}'.format(current_choice, next_command)
                current_choice += 1
        next_command = '/flush_choice'
        self.choice_buffer.append(next_command)
        print '    [{}] {}'.format(current_choice, next_command)
        current_choice += 1

    @make_command(is_blocking=False, handler=None)
    def cmd_flush_choice(self):
        self.choice_buffer = []
        self.wait_for_reply = False

    @make_command(is_blocking=False, handler=None)
    def cmd_atk(self, system_node='firewall'):
        self.cmd_attack_choice(system_node)

    def cmd_parse_diagnostics(self, file_name):
        pass

if __name__ == '__main__':
    rc = ResendingClient()

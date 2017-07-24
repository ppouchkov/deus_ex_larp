#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
from collections import deque
from functools import partial
from time import sleep

import re
import sleekxmpp
import yaml

from config import attacker, node_holder, data
from entities import System
from parsers import parse_status, parse_program, parse_effect


class ResendingClient(sleekxmpp.ClientXMPP):
    greeting_message = 'The very first test {}'.format(datetime.datetime.now())
    sending_delay = datetime.timedelta(seconds=1)

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

    def __init__(self):
        sleekxmpp.ClientXMPP.__init__(self, attacker.jid, attacker.pwd)
        self.register_plugin('xep_0030')  # Service Discovery
        self.register_plugin('xep_0199')  # XMPP Ping

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.last_command_sent = datetime.datetime.now()
        self.recipient = node_holder.jid
        self.input_buffer = deque([], 5)
        self.output_buffer = deque([], 5)

        self.reply_handler = self.default_reply_handler
        self.wait_for_reply = False

        self.current = None
        self.target = None

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
            return
        message_split = message.split()
        command, args = message_split[0].strip('/'), message_split[1:]
        if hasattr(self, 'cmd_{}'.format(command)):
            getattr(self, 'cmd_{}'.format(command))(*args)
        else:
            print 'No such command {}'.format(command)
        self.last_command_sent = datetime.datetime.now()

    def message(self, msg):
        self.output_buffer.appendleft(self.reply_handler(msg['body']))
        print self.output_buffer[0]

    @classmethod
    def default_reply_handler(cls, message):
        return message

    def match_pattern_reply_handler(self, message, pattern):
        print 'reply handler'
        try:
            assert re.match(pattern, message), \
                'reply pattern mismatch, expected: {}'.format(pattern.pattern)
        except Exception as e:
            print str(e)
        finally:
            self.reply_handler = self.default_reply_handler
            self.wait_for_reply = False
        return message

    def close(self):
        print 'disconnect'
        self.disconnect(wait=True)

    def cmd_repeat(self, i=None):
        try:
            message = self.input_buffer[i and int(i) or 1]
            print '/repeat: {}'.format(message)
            self.forward_message(message)
        except IndexError:
            print '/repeat: ERROR empty buffer'
        except ValueError:
            print '/repeat: ERROR index should be integer'

    def cmd_target(self, system):
        try:
            assert system, 'Specify system name'

            target_folder = '{}/{}'.format(data, system)
            if not os.path.exists(target_folder):
                os.mkdir(target_folder)
                self.target = System(system)

            self.reply_handler = partial(self.match_pattern_reply_handler, pattern="ok")
            self.wait_for_reply = True

            self.forward_message('target {}'.format(system))

            while self.wait_for_reply:
                sleep(0.5)

        except Exception as e:
            print str(e)

    def cmd_status(self):
        self.reply_handler = self.status_reply_handler
        self.wait_for_reply = True

        self.forward_message('status')
        while self.wait_for_reply:
            sleep(0.5)

    def status_reply_handler(self, message):
        self.current = parse_status(message)
        self.wait_for_reply = False
        return str(self.current)

    def cmd_effect(self, effect_name, verbose=True):
        current_folder = os.path.join(data, 'effects')
        if not os.path.exists(current_folder):
            print 'create folder {}'.format(current_folder)
            os.mkdir(current_folder)

        if not os.path.exists(os.path.join(current_folder, effect_name)):
            self.reply_handler = partial(self.dump_reply_handler,
                                         folder=current_folder,
                                         file_name_getter=lambda x: '{0.name}'.format(x),
                                         parser=parse_effect)
            self.wait_for_reply = True
            self.forward_message('info #{}'.format(effect_name))
            while self.wait_for_reply:
                sleep(0.5)
        elif verbose:
            with open(os.path.exists(os.path.join(current_folder, effect_name))) as f:
                print yaml.load(f)

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
            self.wait_for_reply = True
            self.forward_message('info #{}'.format(current_code))
            while self.wait_for_reply:
                sleep(0.5)
        elif verbose:
            with open(os.path.join(current_folder, '#{}'.format(current_code))) as f:
                print yaml.load(f)
        with open(os.path.join(current_folder, '#{}'.format(current_code))) as f:
            current_program = yaml.load(f)

        self.cmd_effect(current_program.effect_name, verbose=False)
        if current_program.inevitable_effect_name:
            self.cmd_effect(current_program.inevitable_effect_name, verbose=False)
        print 'finish info'

    def cmd_batch_info(self, *program_codes):
        for program_code in program_codes:
            self.cmd_info(program_code)
        print 'finish batch_info'

    def dump_reply_handler(self, message, folder, file_name_getter, parser):
        try:
            obj = parser(message)
            with open(os.path.join(folder, file_name_getter(obj)), 'w') as f:
                yaml.dump(obj, f, default_style='|')
            self.wait_for_reply = False
        except Exception as e:
            print str(e)
            return 'ERROR'
        return message


if __name__ == '__main__':
    rc = ResendingClient()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
from collections import deque
from time import sleep
import sleekxmpp

from config import attacker, node_holder


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

        self.reply_handler = self.default_message_handler

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
            self.default_message_handler(message)
        self.last_command_sent = datetime.datetime.now()

    def message(self, msg):
        self.output_buffer.appendleft(self.reply_handler(msg['body']))
        print self.output_buffer[0]

    def default_message_handler(self, message):
        return message

    def close(self):
        print 'disconnect'
        self.disconnect(wait=True)

    def cmd_repeat(self, i = None):
        try:
            message = self.input_buffer[i and int(i) or 1]
            print '/repeat: {}'.format(message)
            self.forward_message(message)
        except IndexError:
            print '/repeat: ERROR empty buffer'
        except ValueError:
            print '/repeat: ERROR index should be integer'

if __name__ == '__main__':
    rc = ResendingClient()

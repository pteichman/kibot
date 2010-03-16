#!/usr/bin/python2

import random

import kibot.BaseModule
from kibot.timeoutsocket import Timeout
from kibot.Settings import Setting, init_settings
from kibot.m_irclib import Timer, nm_to_n, StopHandlingEvent, Event

class test(kibot.BaseModule.BaseModule):
    """test module - module for testing kibot functionality"""

    _settings = [
        Setting('var1', get_cperm='owner'),
        Setting('var2', 3, 'description', conv_func=int),
        ]

    _stash_attrs = ['var1', 'var2']
    _command_groups = [
        ('normal', ('noperm', 'badtimer')),
        ('special', ('testreply', 'flood'))
        # the function timeout deliberately omitted to test the "other"
        # feature
        ]
    
    def __init__(self, bot):
        kibot.BaseModule.BaseModule.__init__(self, bot)
        self.flood_timer = None

        self.bot.set_handler('test_event_1', self._test_handler_1, 0)
        self.bot.set_handler('test_event_1', self._test_handler_1, 1)
        self.bot.set_handler('test_event_2', self._test_handler_2, 0)
        self.bot.set_handler('test_event_2', self._test_handler_2, 1)

    def _unload(self):
        self.bot.del_handler('test_event_1', self._test_handler_1, 0)
        self.bot.del_handler('test_event_1', self._test_handler_1, 1)
        self.bot.del_handler('test_event_2', self._test_handler_2, 0)
        self.bot.del_handler('test_event_2', self._test_handler_2, 1)

    _test_handlers_cperm = 1
    def test_handlers(self, cmd):
        event = Event('test_event_1', None, None, [], None)
        self.bot.handle_event(self.bot.conn, event)
        event = Event('test_event_2', None, None, [], None)
        self.bot.handle_event(self.bot.conn, event)

    def _test_handler_1(self, c, e):
        self.bot.log(0, 'handler 1')
        return 'NO MORE'

    def _test_handler_2(self, c, e):
        self.bot.log(0, 'handler 2')
        raise StopHandlingEvent

    # no cperm provided (should be "forbidden")
    def noperm(self, cmd):
        cmd.reply('noperm')

    _oper_cperm = 1
    def oper(self, cmd):
        name, password = cmd.asplit()
        self.bot.conn.oper(name, password)

    _badtimer_cperm = 1
    def badtimer(self, cmd):
        self.bot.set_timer(None)

    _testreply_cperm = 1
    def testreply(self, cmd):
        for meth in 'privmsg reply notice nnotice nreply pnotice msg'.split():
            func = getattr(cmd, meth)
            func('METHOD = %s' % meth)

    _setflood_cperm = 1
    def setflood(self, cmd):
        try:
            step, delays = cmd.asplit(1)
            step = float(step)
            delays = eval(delays)
        except Exception, e:
            cmd.reply('failed - syntax: 2 ((9, 3), (6, 2), (3, 1))')
            cmd.reply(str(e))
        else:
            self.bot.conn.fp.step = step
            self.bot.conn.fp.delays = delays
            cmd.reply('done')

    _flood_cperm = 1
    def flood(self, cmd):
        """flood the server with public messages (to test flood protection)
        flood (start|stop) [N]
        if N is provided, the posts will be of length N (default N=100)"""
        args = cmd.asplit()
        if len(args) == 0 or len(args) > 2 or \
               (args[0] not in ['start', 'stop']):
            return cmd.reply('syntax: flood (start|stop) [N]')
        if args[0] == 'start':
            if self.flood_timer: return cmd.reply('already flooding')
            try: N = int(args[1])
            except IndexError, e: N = 40
            except ValueError, e: return cmd.reply('bad length: %s' % args[1])
            target = cmd.channel or cmd.nick
            self.flood_timer = Timer(0, self._flooder, (N, target), repeat=0)
            self.bot.set_timer(self.flood_timer)
        else:
            if not self.flood_timer: return cmd.reply('not flooding')
            self.bot.del_timer(self.flood_timer)
            self.flood_timer = None

    def _flooder(self, length, target):
        char = random.choice(['X', '.', '/', '|'])
        msg = char * length
        self.bot.conn.privmsg(target, msg)
        return 1
    
    _longmessage_cperm = 1
    def longmessage(self, cmd):
        """send a long message to test message splitting
        longmessage [length]"""
        if cmd.args:
            try: length = int(cmd.args)
            except:
                return cmd.reply('syntax: longmessage [length]')
        else: length = 540
        msg = ''
        while len(msg) < length:
            a = str(len(msg))
            a = a + ' ' + '.'*(9-len(a))
            msg = msg + a
        cmd.reply(msg)
            
    _timeout_cperm = 1
    def timeout(self, cmd):
        import urllib
        import time
        # www.dulug drops ftp, so it will only return after a timeout
        s = 'TIMEOUT START: %s' % time.asctime()
        self.bot.log(4, s)
        cmd.reply(s)

        try:
            urllib.urlopen('ftp://www.dulug.duke.edu/')
        except Timeout, e:
            s = 'TIMEOUT: %s' % str(e)
            self.bot.log(4, s)
            cmd.reply(s)
            
        s = 'TIMEOUT STOP: %s' % time.asctime()
        self.bot.log(4, s)
        cmd.reply(s)
        
    

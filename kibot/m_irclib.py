import select
import time
import types
import traceback
import sys
import socket
import os
import os.path
import errno

from . import irclib
from .irclib import (_linesep_regexp, _rfc_1459_command_regexp,
                     numeric_events, is_channel, nm_to_n, _ctcp_dequote)

def _ping_ponger(conn, event): conn.pong(event.target)
irclib._ping_ponger = _ping_ponger

from . import Flood
from . import logger
log = logger.Logger(threshold=10)

class StopHandlingEvent(Exception): pass

# logging conventions
# 7 = all raw server communication
# 5 = all events
# 3 = all timers
# 0 = errors

def cprefix(thing, prefix):
    return thing and (prefix + thing)

class IRC(irclib.IRC):
    def server(self):
        # overridden so it uses MY ServerConnection object :)
        """Creates and returns a ServerConnection object."""

        c = ServerConnection(self)
        self.connections.append(c)
        return c

    def add_timer(self, timer):
        if not isinstance(timer, Timer):
            raise TypeError, 'object is not a Timer instance: %s' \
                  % repr(timer)
        self.delayed_commands.append(timer)
        if self.fn_to_add_timeout:
            self.fn_to_add_timeout(timer)

    def del_timer(self, timer):
        if not isinstance(timer, Timer):
            raise TypeError, 'object is not a Timer instance: %s' \
                  % repr(timer)
        if timer in self.delayed_commands:
            self.delayed_commands.remove(timer)

    def process_timeout(self):
        t = time.time()
        dc  = self.delayed_commands
        ndc = [] # new delayed commands
        for timer in dc:
            if t >= timer.time:
                if timer.run(): ndc.append(timer)
            else:
                ndc.append(timer)
        self.delayed_commands = ndc

    def process_once(self, timeout=0):
        sockets = map(lambda x: x._get_socket(), self.connections)
        sockets = filter(lambda x: x != None, sockets)
        if sockets:
            while 1:
                try:
                    (i, o, e) = select.select(sockets, [], [], timeout)
                    break
                except select.error, (nr, msg):
                    if nr == errno.EINTR: continue
                    else: raise
            self.process_data(i)
        else:
            time.sleep(timeout)
        self.process_timeout()

    def _handle_event(self, connection, event):
        """[Internal]"""
        h = self.handlers
        for handler in h.get("all_events", []) + h.get(event.type, []):
            try:
                ret = handler[1](connection, event)
                if ret == "NO MORE": raise StopHandlingEvent()
            except StopHandlingEvent, msg:
                return
            except SystemExit:
                raise
            except Exception, msg:
                lexc = traceback.format_exception(sys.exc_type, sys.exc_value,
                                                  sys.exc_traceback)
                exc = ' '.join(lexc)
                log(0, "Handler raised exception:\n%s" % exc)

class Timer(object):
    """Timer is the class used to create delayed and/or repeating functions.

    A Timer instance should be created and handed off to bot.set_timer().
    You should keep a reference around so you can remove it, though.

    Repeating functions should return 0 to be removed or 1 to continue.
    Returning otherwise will result in an exception and somewhat undefined
    behavior."""

    def __init__(self, seconds, func, args=(), kwargs={},
                 fromnow=1, repeat=None):
        """
        seconds   - when the function should be called (the first time)
        func      - python function to call
        args      - arguments to pass to the function
        kwargs    - keyword arguments to pass to the function
        fromnow   - if 1, seconds is interpreted as number of seconds
                    from the time if instantiation.  If zero, it's an
                    absolute unix time (number of seconds since Jan 1, 1970)
        repeat    - if None, function will only be called once, and will
                    be automatically removed.  If an integer, repeat at
                    that interval (in seconds)
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.repeat = repeat

        if fromnow: self.time = time.time() + seconds
        else: self.time = seconds

    def run(self):
        """Internal method"""
        log(5, "Executing Timer: %s, %s, %s" % \
            (self.func, self.args, self.kwargs))
        try:
            ret = apply(self.func, self.args, self.kwargs)
        except SystemExit:
            raise
        except Exception, msg:
            exc = traceback.format_exception(sys.exc_type, sys.exc_value,
                                             sys.exc_traceback)
            log(0, "Timer raised exception:\n%s" % ''.join(exc))
            return 0

        if self.repeat is None:
            return 0
        else:
            self.time = self.time + self.repeat
            if not ret in (0, 1):
                log(0, "Error: repeating Timer must return 0 or 1")
            return ret

    def __cmp__(self, other):
        return cmp(self.time, other.time)


class DirectConnectionMaster(irclib.Connection):

    """Listens for connections on a socket, and then feeds them
    directly to the bot.  You need one Master, which then creates a
    DirectConnection instance for each incoming connection.
    """

    def __init__(self, irclibob, listen):
        self.irclibob = irclibob
        self.listen = listen
        if type(listen) == type(1): # it's a port
            self.socktype = 'inet'
        else:
            self.socktype = 'unix'
        self.conn_id = 1

    def connect(self):
        if self.socktype == 'inet':
            self.master = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.master.bind(('', self.listen))
        else:
            self.master = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # if it exists, remove it.  I hope to make this unnecessary,
            # but if the bot dies in the early stages of startup, a socket
            # can be left behind.  I don't really need it for locking
            # reasons, since the pid file should do that for us.
            if os.path.exists(self.listen): os.unlink(self.listen)
            self.master.bind(self.listen)
        self.master.listen(1)
        self.irclibob.connections.append(self)

    def close(self):
        self.master.close()
        if self in self.irclibob.connections:
            self.irclibob.connections.remove(self)
        if self.socktype == 'unix' and os.path.exists(self.listen):
            os.unlink(self.listen)

    def process_data(self):
        """called when the master socket is readable, which means that
        someone is connecting to it"""
        sock, addr = self.master.accept()
        if type(addr) == type(''): addr_s = addr
        else: addr_s = '%s:%s' % (addr)
        log(1, 'ACCEPTING: DC(%s) from %s' % (self.conn_id, addr_s))
        dc = DirectConnection(self.irclibob, sock, self.conn_id)
        self.conn_id += 1
        self.irclibob.connections.append(dc)
        dc.connect()

    def _get_socket(self):
        return self.master

    def __del__(self):
        self.close()

class DirectConnection(irclib.Connection):
    def __init__(self, irclibob, sock, conn_id):
        self.irclibob = irclibob
        self.socket = sock
        self.conn_id = conn_id
        self.previous_buffer = ''

    def connect(self):
        pass

    def close(self):
        self.irclibob.connections.remove(self)
        self.socket.close()

    def write(self, data):
        self.socket.sendall(data)

    def process_data(self):
        try:
            new_data = self.socket.recv(2**14)
        except socket.error, x:
            # The server hung up.
            self.close()
            return
        if not new_data:
            # Read nothing: connection must be down.
            self.close()
            return

        lines = _linesep_regexp.split(self.previous_buffer + new_data)

        # Save the last, unfinished line.
        self.previous_buffer = lines[-1]
        lines = lines[:-1]

        for line in lines:
            if not line: continue # ignore blank lines
            log(7, "DC(%s): %s" % (self.conn_id, line))
            nm = '!DC(%s)' % self.conn_id
            if line[0] in '#&+!':
                lsplit = line.split(None, 1)
                if len(lsplit) == 2: chan, cmd = lsplit
                else: chan, cmd = lsplit[0], ''
                e = Event('pubmsg', nm, chan, [cmd], line)
            else:
                e = Event('privmsg', nm, '', [line], line)
            self.irclibob._handle_event(self, e)

    def _get_socket(self):
        return self.socket

class ServerConnection(irclib.ServerConnection):
    def __init__(self, irclibobj):
        irclib.ServerConnection.__init__(self, irclibobj)
        self.fp = Flood.FloodProtector()
        self._set_handlers()
        self.channel_keys = {}

    def connect(self, server, port, nickname, password=None, username=None,
                ircname=None, log_in=1):
        """Connect/reconnect to a server.

        Arguments:
            server   -- Server name.
            port     -- Port number.
            nickname -- The nickname.
            password -- Password (if any).
            username -- The username.
            ircname  -- The IRC name.

        This function can be called to reconnect a closed connection.

        Returns the ServerConnection object.
        """
        if self.connected:
            self.quit("Changing server")

        self.socket = None
        self.previous_buffer = ""
        self.handlers = {}
        self.real_server_name = ""
        self.real_nickname = nickname
        self.server = server
        self.port = port
        self.nickname = nickname
        self.username = username or nickname
        self.ircname = ircname or nickname
        self.password = password
        self.localhost = socket.gethostname()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect((self.server, self.port))
        except socket.error, x:
            raise irclib.ServerConnectionError, "Couldn't connect to socket: %s" % x
        self.connected = 1
        if self.irclibobj.fn_to_add_socket:
            self.irclibobj.fn_to_add_socket(self.socket)

        if log_in: self.log_in()
        return self

    def log_in(self):
        # Log on...
        if self.password:
            self.pass_(self.password)
        self.nick(self.nickname)
        self.user(self.username, self.localhost, self.server, self.ircname)
        return self

    def process_data(self):
        """[Internal]"""

        try:
            new_data = self.socket.recv(2**14)
        except socket.error, x:
            # The server hung up.
            self.disconnect("Connection reset by peer")
            return
        if not new_data:
            # Read nothing: connection must be down.
            self.disconnect("Connection reset by peer")
            return

        lines = _linesep_regexp.split(self.previous_buffer + new_data)

        # Save the last, unfinished line.
        self.previous_buffer = lines[-1]
        lines = lines[:-1]

        for line in lines:
            log(7, "FROM SERVER: "+line)

            prefix = None
            command = None
            arguments = None

            m = _rfc_1459_command_regexp.match(line)
            if m.group("prefix"):
                prefix = m.group("prefix")
                if not self.real_server_name:
                    self.real_server_name = prefix

            if m.group("command"):
                command = m.group("command").lower()

            if m.group("argument"):
                a = m.group("argument").split(" :", 1)
                arguments = a[0].split()
                if len(a) == 2:
                    arguments.append(a[1])

            if command == "nick":
                if nm_to_n(prefix) == self.real_nickname:
                    self.real_nickname = arguments[0]

            if command in ["privmsg", "notice"]:
                target, message = arguments[0], arguments[1]
                messages = _ctcp_dequote(message)

                if command == "privmsg":
                    if is_channel(target):
                        command = "pubmsg"
                else:
                    if is_channel(target):
                        command = "pubnotice"
                    else:
                        command = "privnotice"

                for m in messages:
                    if type(m) is types.TupleType:
                        if command in ["privmsg", "pubmsg"]:
                            command = "ctcp"
                        else:
                            command = "ctcpreply"

                        m = list(m)

                        # do the "specific" ctcp event, ie ctcp_action
                        ctcp_command = "%s_%s" % (command, m[0].lower())
                        ctcp_m = m[1:]
                        e = Event(ctcp_command, prefix, target, ctcp_m, line)
                        log(5, 'EVENT: ' + str(e))
                        self._handle_event(e)
                    else:
                        m = [m]
                    e = Event(command, prefix, target, m, line)
                    log(5, 'EVENT: ' + str(e))
                    self._handle_event(e)
            else:
                target = None

                if command == "quit":
                    arguments = [arguments[0]]
                elif command == "ping":
                    target = arguments[0]
                else:
                    target = arguments[0]
                    arguments = arguments[1:]

                if command == "mode":
                    if not is_channel(target):
                        command = "umode"

                # Translate numerics into more readable strings.
                if numeric_events.has_key(command):
                    command = numeric_events[command]

                e = Event(command, prefix, target, arguments, line)
                log(5, 'EVENT: ' + str(e))
                self._handle_event(e)

    def _handle_event(self, event):
        """[Internal]"""
        self.irclibobj._handle_event(self, event)
        if self.handlers.has_key(event.type):
            for fn in self.handlers[event.type]:
                fn(self, event)

    def _get_handlers(self):
        prefix = '_on_'
        handlers = []
        L = len(prefix)
        for f in dir(self):
            a = getattr(self, f)
            if callable(a) and f.startswith(prefix):
                handlers.append(f[L:])
        return handlers

    def _set_handlers(self):
        prefix = '_on_'
        priority = 120
        handlers = self._get_handlers()
        for name in handlers:
            handler = getattr(self, prefix + name)
            self.irclibobj.add_global_handler(name, handler, priority)

    def disconnect(self, message=""):
        """Hang up the connection.

        Arguments:

            message -- Quit message.
        """
        if self.connected == 0:
            return

        self.connected = 0
        try:
            self.socket.close()
        except socket.error, x:
            pass
        self.socket = None
        e = Event("disconnect", self.server, "", [message], "")
        self._handle_event(e)

    # needed to fix "the tim problem" :)
    _msg_limit = 510
    def _split_msg(self, message, limit=None):
        newmsg = []
        lim = limit or self._msg_limit
        while len(message) > lim:
            i = message.rfind(' ', 0, lim+1)
            # if we don't find a space or if there isn't a space in the
            # last 20% of the message, then do a hard chop at the limit
            if i == -1 or i < 0.8*lim:
                newmsg.append(message[:lim])
                message = message[lim:]
            else:
                newmsg.append(message[:i])
                message = message[i+1:] # discard the space
        newmsg.append(message)
        return newmsg

    #################################################################
    def _on_send_raw(self, c, e):
        """Send raw string to the server.
        The string will be padded with appropriate CR LF.
        """
        if not e.conn is self: return
        string = e.raw
        delay, msg = self.fp.check(string) # flood protection
        if delay: log(6, "FLOOD PROTECT: %s" % msg)
        try:
            log(7, "TO SERVER: " + string)
            self.socket.send(string + "\r\n")
        except socket.error, x:
            # Aouch!
            self.disconnect("Connection reset by peer.")

    def send_raw(self, string):
        """Send raw string to the server.
        This is a convenience function for sending a send_raw event
        """
        self._handle_event(Event('send_raw', '', '', [], string, conn=self))

    ###################################################################
    def action(self, target, action):
        self._handle_event(Event('send_ctcp_action', '', '', [target, action],
                                 conn=self))
    def _on_send_ctcp_action(self, c, e):
        if not e.conn is self: return
        self.ctcp("ACTION", *e.args)

    def ctcp(self, ctcptype, target, parameter=""):
        ## it is possible thet ctcp and ctcp_reply run into the message
        ## limits
        ctcptype = ctcptype.upper()
        parameter = parameter and (" " + parameter) or ""
        self._handle_event(Event('send_ctcp', '', '',
                                 [ctcptype, target, parameter], conn=self))
    def _on_send_ctcp(self, c, e):
        if not e.conn is self: return
        self.privmsg(e.args[1], "\001%s%s\001" % (e.args[0], e.args[2]))

    def ctcp_reply(self, target, parameter):
        ## it is possible thet ctcp and ctcp_reply run into the message
        ## limits
        self._handle_event(Event('send_ctcp_reply', '', '',
                                 [target, parameter], conn=self))
    def _on_send_ctcp_reply(self, c, e):
        if not e.conn is self: return
        self.notice(e.args[0], "\001%s\001" % e.args[1])

    def admin(self, server=""):
        self._handle_event(Event('send_admin', '', '', [server.strip()],
                                 conn=self))
    def _on_send_admin(self, c, e):
        if not e.conn is self: return
        self.send_raw("ADMIN " + e.args[0])

    def globops(self, text):
        self._handle_event(Event('send_globops', '', '', [text], conn=self))
    def _on_send_globops(self, c, e):
        if not e.conn is self: return
        self.send_raw("GLOBOPS :" + e.args[0])

    def info(self, server=""):
        self._handle_event(Event('send_info', '', '', [server.strip()],
                                 conn=self))
    def _on_send_info(self, c, e):
        if not e.conn is self: return
        self.send_raw('INFO ' + e.args[0])

    def invite(self, nick, channel):
        self._handle_event(Event('send_invite', '', '', [nick, channel],
                                 conn=self))
    def _on_send_invite(self, c, e):
        if not e.conn is self: return
        self.send_raw("INVITE %s %s" % tuple(e.args))

    def ison(self, nicks):
        """Send an ISON command.
            nicks is a list of nicks
        """
        self._handle_event(Event('send_ison', '', '', nicks, conn=self))
    def _on_send_ison(self, c, e):
        if not e.conn is self: return
        self.send_raw("ISON " + ' '.join(e.args))

    def join(self, channel, key=""):
        if key != "":
            self.channel_keys[channel] = key
        self._handle_event(Event('send_join', '', '', [channel, key],
                                 conn=self))
    def _on_send_join(self, c, e):
        if not e.conn is self: return
        channel = e.args[0]
        key = e.args[1] and (' ' + e.args[1])
        self.send_raw("JOIN %s%s" % (channel, key))

    def kick(self, channel, nick, comment=""):
        self._handle_event(Event('send_kick', '', '',
                                  [channel, nick, comment], conn=self))
    def _on_send_kick(self, c, e):
        if not e.conn is self: return
        comment = e.args[2] and (" :" + e.args[2])
        self.send_raw("KICK %s %s%s" % (e.args[0], e.args[1], comment))

    def links(self, remote_server="", server_mask=""):
        self._handle_event(Event('send_links', '', '',
                                 [remote_server, server_mask], conn=self))
    def _on_send_links(self, c, e):
        if not e.conn is self: return
        command = "LINKS"
        for i in e.args:
            if i: command = command + ' ' + i
        self.send_raw(command)

    def list(self, channels=None, server=""):
        self._handle_event(Event('send_list', '', '', [channels, server],
                                 conn=self))
    def _on_send_list(self, c, e):
        if not e.conn is self: return
        command = "LIST"
        if e.args[0]:
            command = command + " " + ','.join(e.args[0])
        if e.args[1]:
            command = command + " " + e.args[1]
        self.send_raw(command)

    def lusers(self, server=""):
        self._handle_event(Event('send_lusers', '', '', [server], conn=self))
    def _on_send_lusers(self, c, e):
        if not e.conn is self: return
        server = e.args[0] and (' ' + e.args[0])
        self.send_raw("LUSERS" + server)

    def mode(self, target, command):
        self._handle_event(Event('send_mode', '', '',
                                 [target, command], conn=self))
    def _on_send_mode(self, c, e):
        if not e.conn is self: return
        self.send_raw("MODE %s %s" % tuple(e.args))

    def motd(self, server=""):
        self._handle_event(Event('send_motd', '', '', [server], conn=self))
    def _on_send_motd(self, c, e):
        if not e.conn is self: return
        server = e.args[0] and (' ' + e.args[0])
        self.send_raw('MOTD' + server)

    def names(self, channels=None):
        self._handle_event(Event('send_names', '', '', [channels], conn=self))
    def _on_send_names(self, c, e):
        if not e.conn is self: return
        c = e.args and (' ' + ','.join(channels)) or ''
        self.send_raw("NAMES" + c)

    def nick(self, newnick):
        self._handle_event(Event('send_nick', '', '', [newnick], conn=self))
    def _on_send_nick(self, c, e):
        if not e.conn is self: return
        self.send_raw("NICK %s" % tuple(e.args))

    def notice(self, target, text):
        lim = self._msg_limit - 100
        if len(text) > self._msg_limit: messages = self._split_msg(text, lim)
        else: messages = [text]
        for text in messages:
            self._handle_event(Event('send_notice', '', '', [target, text],
                                     conn=self))
    def _on_send_notice(self, c, e):
        if not e.conn is self: return
        self.send_raw("NOTICE %s :%s" % tuple(e.args))

    def oper(self, nick, password):
        self._handle_event(Event('send_oper', '', '', [nick, password],
                                 conn=self))
    def _on_send_oper(self, c, e):
        if not e.conn is self: return
        self.send_raw("OPER %s %s" % tuple(e.args))

    def part(self, channels):
        if type(channels) == types.StringType: c = [channels]
        else: c = channels
        self._handle_event(Event('send_part', '', '', c, conn=self))
    def _on_send_part(self, c, e):
        self.send_raw('PART ' + ','.join(e.args))
        if not e.conn is self: return

    def pass_(self, password):
        self._handle_event(Event('send_pass', '', '', [password], conn=self))
    def _on_send_pass(self, c, e):
        if not e.conn is self: return
        self.send_raw("PASS %s" + e.args)

    def ping(self, target, target2=""):
        self._handle_event(Event('send_ping', '', '', [target, target2],
                                 conn=self))
    def _on_send_ping(self, c, e):
        if not e.conn is self: return
        t1 = e.args[0]
        t2 = e.args[1] and (' ' + e.args[1])
        self.send_raw("PING %s%s" % (t1, t2))

    def pong(self, target, target2=""):
        self._handle_event(Event('send_pong', '', '', [target, target2],
                                 conn=self))
    def _on_send_pong(self, c, e):
        if not e.conn is self: return
        t1 = e.args[0]
        t2 = e.args[1] and (' ' + e.args[1])
        self.send_raw("PONG %s%s" % (t1, t2))

    def privmsg(self, target, text):
        lim = self._msg_limit - 100
        if len(text) > self._msg_limit: messages = self._split_msg(text, lim)
        else: messages = [text]
        for text in messages:
            self._handle_event(Event('send_privmsg', '', '', [target, text],
                                     conn=self))
    def _on_send_privmsg(self, c, e):
        if not e.conn is self: return
        self.send_raw("PRIVMSG %s :%s" % tuple(e.args))

    def privmsg_many(self, targets, text):
        lim = self._msg_limit - 100
        if len(text) > self._msg_limit: messages = self._split_msg(text, lim)
        else: messages = [text]
        for text in messages:
            self._handle_event(Event('send_privmsg_many', '', '',
                                     [targets, text], conn=self))
    def _on_send_privmsg_many(self, c, e):
        if not e.conn is self: return
        self.send_raw("PRIVMSG %s :%s" % (','.join(e.args[0]), e.args[1]))

    def quit(self, message=""):
        self._handle_event(Event('send_quit', '', '',
                                 [message], conn=self))
    def _on_send_quit(self, c, e):
        if not e.conn is self: return
        message = e.args[0] and (' :' + e.args[0])
        self.send_raw("QUIT" + message)

    def sconnect(self, target, port="", server=""):
        self._handle_event(Event('send_sconnect', '', '',
                                 [target, port, servers], conn=self))
    def _on_send_sconnect(self, c, e):
        if not e.conn is self: return
        port = e.args[1] and (' ' + e.args[1])
        server = e.args[2] and (' ' + e.args[2])
        self.send_raw("CONNECT %s%s%s" % (e.args[0], port, server))

    def squit(self, server, comment=""):
        self._handle_event(Event('send_squit', '', '',
                                 [server, comment], conn=self))
    def _on_send_squit(self, c, e):
        if not e.conn is self: return
        comment = cprefix(e.args[1], ' :')
        self.send_raw("SQUIT %s%s" % (e.args[0], comment))

    def stats(self, statstype, server=""):
        self._handle_event(Event('send_stats', '', '',
                                 [statstype, server], conn=self))
    def _on_send_stats(self, c, e):
        if not e.conn is self: return
        server = cprefix(e.args[1], ' ')
        self.send_raw("STATS %s%s" % (e.args[0], server))

    def time(self, server=""):
        self._handle_event(Event('send_time', '', '', [server], conn=self))
    def _on_send_time(self, c, e):
        if not e.conn is self: return
        server = cprefix(e.args[0], ' ')
        self.send_raw("TIME" + server)

    def topic(self, channel, new_topic=''):
        self._handle_event(Event('send_topic', '', '', [channel, new_topic],
                                 conn=self))
    def _on_send_topic(self, c, e):
        if not e.conn is self: return
        new_topic = cprefix(e.args[1], ' :')
        self.send_raw("TOPIC %s%s" % (e.args[0], new_topic))

    def trace(self, target=""):
        self._handle_event(Event('send_target', '', '', [target], conn=self))
    def _on_send_trace(self, c, e):
        if not e.conn is self: return
        target = cprefix(e.args[0], ' ')
        self.send_raw("TRACE" + target)

    def user(self, username, localhost, server, ircname):
        self._handle_event(Event('send_user', '', '',
                                 [username, localhost, server, ircname],
                                 conn=self))
    def _on_send_user(self, c, e):
        if not e.conn is self: return
        self.send_raw("USER %s %s %s :%s" % tuple(e.args))

    def userhost(self, nicks):
        self._handle_event(Event('send_userhost', '', '', list(nicks),
                                 conn=self))
    def _on_send_userhost(self, c, e):
        if not e.conn is self: return
        self.send_raw("USERHOST " + ','.join(e.args))

    def users(self, server=""):
        self._handle_event(Event('send_users', '', '', [server], conn=self))
    def _on_send_users(self, c, e):
        if not e.conn is self: return
        server = cprefix(e.args[0], ' ')
        self.send_raw("USERS" + server)

    def version(self, server=""):
        self._handle_event(Event('send_version', '', '', [server], conn=self))
    def _on_send_version(self, c, e):
        if not e.conn is self: return
        server = cprefix(e.args[0], ' ')
        self.send_raw("VERSION" + server)

    def wallops(self, text):
        self._handle_event(Event('send_wallops', '', '', [text], conn=self))
    def _on_send_wallops(self, c, e):
        if not e.conn is self: return
        self.send_raw("WALLOPS :" + e.args[0])

    def who(self, target="", op=""):
        self._handle_event(Event('send_who', '', '', [target, op], conn=self))
    def _on_send_who(self, c, e):
        if not e.conn is self: return
        target = cprefix(e.args[0], ' ')
        op = e.args[1] and ' o' ##### SHOULD THIS BE "or"?
        self.send_raw("WHO%s%s" % (target, op))

    def whois(self, targets):
        self._handle_event(Event('send_whois', '', '', targets, conn=self))
    def _on_send_whois(self, c, e):
        if not e.conn is self: return
        self.send_raw("WHOIS " + ','.join(e.args))

    def whowas(self, nick, max="", server=""):
        self._handle_event(Event('send_whowas', '', '', [nick, max, server],
                                 conn=self))
    def _on_send_whowas(self, c, e):
        if not e.conn is self: return
        max = cprefix(e.args[1], ' ')
        server = cprefix(e.args[2], ' ')
        self.send_raw("WHOWAS %s%s%s" % (e.args[0], max, server))

class Event(object):
    """Event instances are used to represent irc events, and are what
    handlers receive.  Event objects are read-only, and have a number
    of standard attributes:
      type    - event type, this is first arg to bot.set_handler(...)
      source  - event source, usually a nickmask or server name
      target  - event target, usually a channel or nick
      args    - list containing arguments
      raw     - the raw event, usually the full irc string
      flags   - a dict that can be used by event generators for
                arbitrary information (this is optional)

    Here's an example.  If the bot is on channel #mtest, and someone
    (lets say michael) types "hello" into the channel, the corresponding
    Event instance will have the following attributes:

      type:   'pubmsg'
      source: 'michael!~mstenner@alai.adsl.duke.edu'
      target: '#mtest'
      args:   ['hello']
      raw:    ':michael!~mstenner@alai.adsl.duke.edu PRIVMSG #mtest :hello'

    Note that the exact handling of each type of event depends on the irc
    protocol and also on the event type.  Kibot generates some
    "secondary" events internally.  For example, the 'command' Event
    instance looks like this:

      type:   'command'
      source: 'michael'   <- nick who executed the command
      target: 'path'      <- command as typed
      args:   ['']        <- args to the command (as a single string)
      raw     < the kibot.CommandHandler.Command instance >

    If you're having trouble figuring out how handle and deal with an event
    be sure to turn up logging (to at least level 5) and look at the events
    as they ocme in.
    """
    def __init__(self, type, source, target, args,
                 raw='', conn=None, flags=None):
        self._type = type
        self._source = source
        self._target = target
        if args: self._args = args
        else: self._args = []
        self._raw = raw
        self._conn = conn
        self._flags = flags or {}

    def _get_type(self): return self._type
    type = property(_get_type)
    def _get_source(self): return self._source
    source = property(_get_source)
    def _get_target(self): return self._target
    target = property(_get_target)
    def _get_args(self): return self._args
    args = property(_get_args)
    def _get_raw(self): return self._raw
    raw = property(_get_raw)
    def _get_conn(self): return self._conn
    conn = property(_get_conn)
    def _get_flags(self): return self._flags
    flags = property(_get_flags)

    def __str__(self):
        format = "type: %s, source: %s, target: %s, args: %s%s"
        if self._flags: f = ", flags: %s" % self._flags
        else: f = ""
        return format % (self._type, self._source, self._target, self._args, f)


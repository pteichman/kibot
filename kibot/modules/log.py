"""
This module maintains logs of irc communication that the bot sees.  This
includes channel conversation, private messages, and server notices.  All
logging is facilitated via 'logging objects'.  Each object has a 'type',
which determines the format of its output (xml, text, etc), a filename,
list of channels to log, list of nicks whose private communication (with the
bot) to log, and list of servers whose notices to log.

Here are some notes on these:

  type
    there are currently two builtin types, 'xml' and 'text'.  This is
    currently no facility for using 'plugin' types, although it's easy
    enough to add on to the 'official' module and then put it in a
    local modules directory.  If there's demand, a plugin machanism
    can be added.

  filename
    this is a string which can contain strftime formats.  This value
    will be joined with the 'logdir' setting to get the filename to
    which logs should be written.  Therefore, if the filename begins
    with a '/', it will be interpreted as an absolute filename.  This
    way, you can specify a logdir where most logs go, but still
    specify an absolute path for others.  Logging objects
    automatically log to the right place when logdir or filenames are
    changed, although old logs are never moved.

  channels
    this is a (comma-separated) list of channels to log.  The list can
    contain glob characters, so you could do '#dhg,#kibot*'

  nicks
    this is a (comma-separated) list of nicks whose private
    communication with the bot should be logged.  This includes only
    private communication going in either direction between the given
    nick(s) and the bot.  It DOES NOT (in fact, CAN not) log private
    communication between two users.

  servers
    this is a (comma-separated) list of servers whose notices should
    be logged.  Because kibot currently only supports single-server
    connections, you should really either set this to '*' if want
    notices, or '' if you don't.
"""


import time
import string
import os.path
import fnmatch

from kibot.BaseModule import BaseModule
from kibot.m_irclib import is_channel
from kibot.irclib import parse_channel_modes
from kibot.Settings import Setting

from kibot.m_irclib import nm_to_n

class log(BaseModule):
    """logging of irc communication
    The default logfile directory is stored in the setting 'logdir'.  It
    can be viewed with 'get log.logdir' and set with 'set log.logdir NEWDIR'
    """

    def _update_logdir(self, name):
        for logobj in self.loggers.values(): logobj.set_basedir(self.logdir)
            
    _settings = [
        Setting('logdir', None, 'default directory for logs',
                update_func=_update_logdir)
        ]

    _stash_attrs = ['logdata']
    def __init__(self, bot):
        self.formats = {'xml': XMLLogger, 'text': TextLogger}
        self.logdir = bot.op.files.data_dir
        self.loggers = {}
        self.logdata = {}
        BaseModule.__init__(self, bot)

        self._recreate_loggers()
        
    def _unload(self):
        for k, v in self.loggers.items():
            v.unload()
        self.loggers = {}

    def _sync(self, logger_id=None):
        if logger_id: ids = [logger_id]
        else: ids = self.loggers.keys()
        for k in ids:
            try:
                self.logdata[k] = self.loggers[k].get_data()
            except KeyError, e:
                try: del self.logdata[k]
                except KeyError, e: pass
        self._stash()

    def _recreate_loggers(self):
        for k, (t, d) in self.logdata.items():
            klass = self.formats[t]
            inst = apply(klass, (self.bot, self.logdir), d)
            self.loggers[k] = inst

    _newlog_cperm = 'manager'
    def newlog(self, cmd):
        """create a new irc logging object
        newlog <label> <filename> <type> [<channels> [<nicks> [<servers>]]]
        <filename> will be treated as an strftime format
        <type> should be one of: xml text
        <channels>, <nicks> and <servers> are comma-separated lists which can contain globs.  Empty quotes can be used to indicate an empty list.
        ex: newlogger private private-%Y%m%d.xml xml '' * *
        This will log all private communication and server notices.
        """
        args = cmd.shsplit()
        try:
            label = args.pop(0)
            filename = args.pop(0)
            string_logtype = args.pop(0)
        except IndexError, e:
            cmd.reply('syntax error: newlogger <label> <filename> <type> [<channels> [<nicks> [<servers>]]]')
            return
            
        ltype = self.formats.get(string_logtype)
        if not ltype: return cmd.reply('bad log type: %s' % string_logtype)

        while len(args) < 3: args.append('')
        channels, nicks, servers = tuple( map(self._splitlist, args) )

        logger = ltype(self.bot, self.logdir, filename,
                       channels, nicks, servers)
        self.loggers[label] = logger
        self._sync(label)
        cmd.reply('done')

    def _splitlist(self, st):
        if not st: return []
        else: return st.split(',')

    _setlog_cperm = 'manager'
    def setlog(self, cmd):
        """set a log object's properties
        setlog <label> <property name> <new value>
        legal property names: filename channels nicks servers
        type cannot be set dynamically - you must destroy and recreate the object
        """
        legal_names = ['filename', 'channels', 'nicks', 'servers']
        try:
            label, name, value = cmd.shsplit(2)
        except IndexError, e:
            cmd.reply('syntax error: setlog <label> <property name> <new value>')
            return

        try: logobj = self.loggers[label]
        except KeyError, e: return cmd.reply('no such logger: %s' % label)

        if not name in ['filename', 'channels', 'nicks', 'servers']:
            return cmd.reply('<property name> must be one of %s' %
                             ' '.join(legal_names))

        if name in legal_names[1:]:
            setattr(logobj, name, self._splitlist(value))
        elif name == 'filename':
            self.loggers.set_filename(value)
        self._sync(label)
        cmd.reply('done')
        
    _getlog_cperm = 'manager'
    def getlog(self, cmd):
        """get a log object's properties
        getlog [label(s)]"""
        if not cmd.args:
            return cmd.reply('labels: %s' % ', '.join(self.loggers.keys()))
        else:
            labels = cmd.shsplit()

        for label in labels:
            if not self.loggers.has_key(label):
                return cmd.reply('no such log object: %s' % label)
        for label in labels:
            logobj = self.loggers.get(label)
            filename = logobj.filename
            ltype    = logobj.logtype
            channels = repr( ','.join(logobj.channels) )
            nicks    = repr( ','.join(logobj.nicks) )
            servers  = repr( ','.join(logobj.servers) )
            cmd.reply("%s: %s %s %s %s %s" % (label, filename, ltype,
                                              channels, nicks, servers))
        
    _dellog_cperm = 'manager'
    def dellog(self, cmd):
        """delete a log object
        dellog [label(s)]"""
        if not cmd.args:
            return cmd.reply('syntax: dellog [label(s)]')
        else:
            labels = cmd.shsplit()

        for label in labels:
            if not self.loggers.has_key(label):
                return cmd.reply('no such log object: %s' % label)
        for label in labels:
            logobj = self.loggers.get(label)
            logobj.unload()
            del self.loggers[label]
        self._sync()
        cmd.reply('done')
            
class BaseLogger(BaseModule):
    time_format = "%a, %d %b %Y %H:%M:%S"
    trans_table = string.maketrans('', '')
    del_chars = []
    for i in range(0, 256):
        if i < 32 or i > 127: del_chars.append(chr(i))
    del_chars = ''.join(del_chars)
    
    def __init__(self, bot, basedir, filename,
                 channels=None, nicks=None, servers=None):
        self.bot = bot
        self.fo = None
        self.basedir  = basedir
        self.filename = filename
        self._real_filename = None
        self._open_file()

        self.channels = channels or []
        self.nicks = nicks or []
        self.servers = servers or []

        self._set_all_handlers()

    def get_data(self):
        d = {'filename': self.filename,
             'channels': self.channels,
             'nicks':    self.nicks,
             'servers':  self.servers}
        return(self.logtype, d)

    def unload(self):
        self._del_all_handlers()
        self._close_file()

    def __repr__(self):
        st = '%s(bot, %s, %s, %s, %s, %s)' % \
             (self.__class__.__name__, repr(self.basedir), repr(self.filename),
              repr(self.channels), repr(self.nicks), repr(self.servers))
        return st
    
    def set_filename(self, filename):
        if not self.filename == filename:
            self._close_file()
            self.filename = filename
            self._open_file()

    def set_basedir(self, basedir):
        if not self.basedir == basedir:
            self._close_file()
            self.basedir = basedir
            self._open_file()

    def _open_file(self):
        if self.fo: self._close_file()
        nfname = time.strftime(self.filename, time.localtime(time.time()))
        nfname = os.path.join(self.basedir, nfname)
        self._real_filename = nfname
        self.fo = file(nfname, 'a')
        self._write_header()

    def _close_file(self):
        if not self.fo: return
        self._write_footer()
        self.fo.close()
        self.fo = None

    def write(self, st):
        # check what the filename should be now and open a new
        # file if necessary
        nfname = time.strftime(self.filename, time.localtime(time.time()))
        nfname = os.path.join(self.basedir, nfname)
        if not nfname == self._real_filename:
            self._close_file()
            self._open_file()
        #self.bot.log(10, 'writing %s to %s' % (repr(st), nfname))
        self.fo.write(st)
        self.fo.flush() # <-- should I remove this?
        
    def _write_header(self):
        """This is called EVERY time a file is opened, not just the first
        time"""
        pass

    def _write_footer(self):
        """This is called EVERY time a file is closed, not just the first
        time"""
        pass        

    def _set_all_handlers(self):
        self._set_handlers(prefix='_onlow_',  priority=-10)
        self._set_handlers(prefix='_on_',     priority=-1)
        self._set_handlers(prefix='_onhigh_', priority=101)

    def _del_all_handlers(self):
        self._del_handlers(prefix='_onlow_',  priority=-10)
        self._del_handlers(prefix='_on_',     priority=-1)
        self._del_handlers(prefix='_onhigh_', priority=101)

    def _add_times(self, m):
        T = time.time()
        TT = time.localtime(T)
        m['utime'] = str(int(T))
        m['htime'] = time.strftime(self.time_format, TT)

    def _match_list(self, s, globlist):
        for g in globlist:
            if fnmatch.fnmatch(s, g): return 1
        return 0
    
    def _strip_func(self, prestripped_text):
        return prestripped_text.translate(self.trans_table, self.del_chars)

    def _strip(self, *args):
        """You can pass this a string, tuple, list, or dict.
        If a list or tuple, child strings will be stripped.  If it's a
        dict, the keys will be stripped.  You can also pass several strings.
        """
        t = type(args[0])
        if t == type( () ) or t == type( [] ):
            return map(self._strip_func, args[0])
        elif t == type( {} ):
            m = {}
            for k, v in args[0].items():
                m[k] = self._strip_func(v)
            return m
        else:
            return map(self._strip_func, args)

    ########################################################################
    def _on_pubmsg(self, c, e):
        if not self._match_list(e.target, self.channels): return
        m = {'target': e.target,
             'source': nm_to_n(e.source),
             'message': e.args[0],
             'type': 'public'}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._pubmsg_f % m)

    def _on_privmsg(self, c, e):
        snick = nm_to_n(e.source)
        if not self._match_list(snick, self.nicks): return
        m = {'target': self.bot.nick,
             'source': snick,
             'message': e.args[0],
             'type': 'private'}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._privmsg_f % m)

    def _on_send_privmsg(self, c, e):
        target, text = e.args
        m = {'target': target,
             'source': self.bot.nick,
             'message': text}
        if is_channel(target):
            if not self._match_list(target, self.channels): return
            m['type'] = 'public'
            form = self._send_pubmsg_f
        else:
            if not self._match_list(target, self.nicks): return
            m['type'] = 'private'
            form = self._send_privmsg_f
        self._add_times(m)
        m = self._strip(m)
        self.write(form % m)
            
    def _on_pubnotice(self, c, e):
        if not self._match_list(e.target, self.channels): return
        m = {'target': e.target,
             'source': nm_to_n(e.source),
             'message': e.args[0],
             'type': 'public'}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._pubnotice_f % m)
    
    def _on_privnotice(self, c, e):
        if e.source is None:
            source = getattr(c, 'real_server_name', c.server)
            if not self._match_list(source, self.servers): return
            format = self._servernotice_f
        else:
            source = nm_to_n(e.source)
            if not self._match_list(source, self.nicks): return
            format = self._privnotice_f

        m = {'target': self.bot.nick,
             'source': source,
             'message': e.args[0],
             'type': 'private'}
        self._add_times(m)
        m = self._strip(m)
        self.write(format % m)

    def _on_send_notice(self, c, e):
        target, text = e.args
        m = {'target': target,
             'source': self.bot.nick,
             'message': text}
        if is_channel(target):
            if not self._match_list(target, self.channels):return
            m['type'] = 'public'
            form = self._send_pubnotice_f
        else:
            if not self._match_list(target, self.nicks):return
            m['type'] = 'private'
            form = self._send_privnotice_f
        self._add_times(m)
        m = self._strip(m)
        self.write(form % m)

    def _on_ctcp_action(self, c, e):
        m = {'target': e.target,
             'source': nm_to_n(e.source),
             'message': e.args[0]}
        if is_channel(e.target):
            if not self._match_list(e.target, self.channels): return
            m['type'] = 'public'
            form = self._pubaction_f
        else:
            if not self._match_list(e.target, self.nicks): return
            m['type'] = 'private'
            form = self._privaction_f
        self._add_times(m)
        m = self._strip(m)
        self.write(form % m)
    
    def _on_send_ctcp_action(self, c, e):
        target, text = e.args
        m = {'target': target,
             'source': self.bot.nick,
             'message': text}
        if is_channel(target):
            if not self._match_list(target, self.channels): return
            m['type'] = 'public'
            form = self._send_pubaction_f
        else:
            if not self._match_list(target, self.nicks): return
            m['type'] = 'private'
            form = self._send_privaction_f
        self._add_times(m)
        m = self._strip(m)
        self.write(form % m)

    def _on_join(self, c, e):
        if not self._match_list(e.target, self.channels): return
        m = {'channel': e.target,
             'nick': nm_to_n(e.source),
             'nickmask': e.source}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._join_f % m)
    
    def _on_nick(self, c, e):
        for chan_name, chan_obj in self.bot.ircdb.channels.items():
            if chan_obj.has_user(e.target) and \
                   self._match_list(chan_name, self.channels):
                break # skips else
        else:
            return

        m = {'old': nm_to_n(e.source),
             'new': e.target}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._nick_f % m)
        
    def _on_part(self, c, e):
        if not self._match_list(e.target, self.channels): return
        m = {'channel': e.target,
             'nick': nm_to_n(e.source)}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._part_f % m)
        
    def _on_kick(self, c, e):
        if not self._match_list(e.target, self.channels): return
        m = {'channel': e.target,
             'source': nm_to_n(e.source),
             'target': e.args[0],
             'message': e.args[1]}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._kick_f % m)
        
    def _onlow_quit(self, c, e):
        nick = nm_to_n(e.source)
        for chan_name, chan_obj in self.bot.ircdb.channels.items():
            self.bot.log(0, 'checking %s' % chan_name)
            if chan_obj.has_user(nick) and \
                   self._match_list(chan_name, self.channels):
                self.bot.log(0, 'success')
                break # skips else
            else:
                self.bot.log(0, "%s %s" % (chan_obj.has_user(nick),
                                           self._match_list(chan_name, self.channels)))
                self.bot.log(0, 'failure')
        else:
            return

        m = {'nick': nick,
             'message': e.args[0]}
        self._add_times(m)
        m = self._strip(m)
        self.write(self._quit_f % m)

    def _on_topic(self, c, e):
        if is_channel(e.target) and self._match_list(e.target, self.channels):
            m = {'nick': nm_to_n(e.source),
                 'channel': e.target,
                 'topic': e.args[0]}
            self._add_times(m)
            m = self._strip(m)
            self.write(self._topic_f % m)

    def _on_mode(self, c, e):
        """handler for mode changes
        This method is more complex than the others.  First, it ONLY handles
        channel mode changes.  This includes bans, ops, voice, topic lock,
        etc.  Non-channel modes are ignored.

        For each mode individually, the following things happen:
        1) if the instance has a method called _handle_mode_X (where
           X is the specific mode) it will be called with the following
           args: connection_object, event_object, source_nick,
                 target_channel, sign, mode, arg

           For example, if seth gives michael ops on #dhg, you would
           see this: (<conn>, <event>, 'seth', '#dhg', '+', 'o', 'michael')

           if the function returns None (this is what happens when
           there is no explicit "return") then processing goes on to
           the next "chunk".  Otherwise, processing continues to (2)

        2) The standard "m" dict is formed.

        3) if the instance has an attribute called _mode_X_f then it
           will be used as the format string for writing the mode.
           Otherwise, the attribute _mode_f will be used.  Therefore,
           you should define _mode_f as a "generic mode" format, which
           you can override with _mode_X_f attributes or _handle_mode_X
           methods.

        Note that this happens for each perm "chunk".  A single mode
        command can contain may chunks.  For example:
          /mode #dhg +ov michael michael
        This will first be processed with
          (sign, mode, arg) = ('+', 'o', 'michael')
        and then
          (sign, mode, arg) = ('+', 'v', 'michael')

        m contains the following keys:
          utime, htime, source, channel, sign, mode, arg, raw
        where raw is (for example) '+v michael'
        """
        if not (is_channel(e.target) and
                self._match_list(e.target, self.channels)): return
        t = e.target
        s = nm_to_n(e.source)
        string_modes = ' '.join(e.args)
        modes = parse_channel_modes(string_modes)
        m = {'source': s, 'channel': t}
        self._add_times(m)
        for sign, mode, arg in modes:
            meth = getattr(self, '_handle_mode_' + mode, None)
            if meth is not None:
                if not meth(c, e, s, t, sign, mode, arg): continue

            raw = '%s%s %s' % (sign, mode, arg)
            new = {'sign': sign, 'mode': mode, 'arg': arg, 'raw': raw}
            m.update(self._strip(new))
            format = getattr(self, '_mode_%s_f' % mode, self._mode_f)
            self.write(format % m)
                
class XMLLogger(BaseLogger):
    logtype = 'xml'
    def _strip_func(self, t):
        t = t.translate(self.trans_table, self.del_chars)
        t = t.replace("&", "&amp;")
        t = t.replace("<", "&lt;")
        t = t.replace(">", "&gt;")
        return t

    _pubmsg_f = '<msg type="%(type)s" time="%(htime)s" utime="%(utime)s" ' \
                'target="%(target)s" source="%(source)s">%(message)s</msg>\n'
    _send_privmsg_f = _send_pubmsg_f = _privmsg_f = _pubmsg_f

    _pubnotice_f = '<notice type="%(type)s" time="%(htime)s" utime="%(utime)s" ' \
                   'target="%(target)s" source="%(source)s">%(message)s</notice>\n'
    _send_privnotice_f = _send_pubnotice_f = _pubnotice_f
    _servernotice_f = _privnotice_f = _pubnotice_f

    _pubaction_f = '<action type="%(type)s" time="%(htime)s" utime="%(utime)s" ' \
                'target="%(target)s" nick="%(source)s">%(message)s</action>\n'
    _send_privaction_f = _send_pubaction_f = _privaction_ = _pubaction_f

    _join_f = '<join time="%(htime)s" utime="%(utime)s" ' \
              'channel="%(channel)s" nick="%(nick)s">%(nickmask)s</join>\n'
    _nick_f = '<nick time="%(htime)s" utime="%(utime)s" ' \
              'old="%(old)s" new="%(new)s" />\n'''
    _part_f = '<part time="%(htime)s" utime="%(utime)s" ' \
              'channel="%(channel)s" nick="%(nick)s" />\n'
    _kick_f = '<kick time="%(htime)s" utime="%(utime)s" ' \
              'channel="%(channel)s" source="%(source)s" target="%(target)s">' \
              '%(message)s</kick>\n'
    _quit_f = '<quit time="%(htime)s" utime="%(utime)s" ' \
              'nick="%(nick)s">%(message)s</quit>\n'
    _topic_f = '<topic time="%(htime)s" utime="%(utime)s" ' \
               'channel="%(channel)s" nick="%(nick)s">%(topic)s</topic>\n'
    _mode_f  = '<mode time="%(htime)s" utime="%(utime)s" ' \
               'channel="%(channel)s" source="%(source)s" sign="%(sign)s" ' \
               'mode="%(mode)s" arg="%(arg)s">%(raw)s</mode>\n'

class TextLogger(BaseLogger):
    logtype = 'text'
    time_format = "%x %X"

    _pubmsg_f           = '%(htime)s <%(source)s> %(message)s\n'
    _send_pubmsg_f      =  _pubmsg_f
    _privmsg_f          = '%(htime)s <%(source)s> %(message)s\n'
    _send_privmsg_f     = '%(htime)s >%(target)s< %(message)s\n'

    _pubnotice_f        = '%(htime)s -%(source)s- %(message)s\n'
    _send_pubnotice_f   = _pubnotice_f
    _servernotice_f     = _pubnotice_f
    _privnotice_f       = '%(htime)s -%(source)s- %(message)s\n'
    _send_privnotice_f  = '%(htime)s +%(source)s+ %(message)s\n'

    _pubaction_f        = '%(htime)s * %(source)s %(message)s\n'
    _send_pubaction_f   = _pubaction_f
    _privaction_f       = '%(htime)s (%(target)s) * %(source)s %(message)s\n'
    _send_privaction_f  = _privaction_f
    
    _join_f  = '%(htime)s --> %(nick)s (%(nickmask)s) has joined %(channel)s\n'
    _nick_f  = '%(htime)s --- %(old)s is now known as %(new)s\n'
    _part_f  = '%(htime)s <-- %(nick)s has left %(channel)s\n'
    _kick_f  = '%(htime)s <-- %(source)s has kicked %(target)s from ' \
               '%(channel)s (%(message)s)\n'
    _quit_f  = '%(htime)s <-- %(nick)s has quit (%(message)s)\n'
    _topic_f = '%(htime)s --- %(nick)s has changed the %(channel)s ' \
               'topic to: %(topic)s\n'
    _mode_f  = '%(htime)s --- mode: %(raw)s on %(channel)s by %(source)s\n'

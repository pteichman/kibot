import string
import re
import time

import BaseModule
from irclib import irc_lower, nm_to_n, is_channel
from m_irclib import DirectConnection, Event

from PermObjects import cpString, PermError

class CommandHandler(BaseModule.BaseModule):
    """This class is for handling bot commands.  An instance will
    be stored as bot.command_handler, but has no public methods
    and should not be accessed directly."""

    def __init__(self, bot):
        self.bot = bot
        self._set_handlers(20)
        
    def _unload(self):
        self._del_handlers()

    ############################################################
    # Handlers

    def _on_privmsg(self, c, e):
        """handler for all private messages to the bot"""
        nm = e.source
        channel = None
        command = e.args[0]
        self._do_command(nm, channel, command, c, e)

    def _on_pubmsg(self, c, e):
        """handler for all public (channel) messages"""
        command_regex = r'\s*%s\s*[,:]\s*(.*?)\s*$' % self.bot.nick
        m = re.match(command_regex, e.args[0], re.IGNORECASE)
        if m:
            nm = e.source
            channel = e.target
            command = m.group(1)
            self._do_command(nm, channel, command, c, e)
        return

    def _on_command_not_found(self, c, e):
        """default handler for command_not_found events"""
        e.raw.reply("command not found: %s" % e.target)

    def _on_permission_denied(self, c, e):
        """default handler for permission_denied events"""
        cmd = e.raw
        args = e.args
        if e.args:
            cmd.nreply("permission denied: %s" % args[0])
            for r in args[1:]: cmd.nreply(str(r))
        else:
            e.raw.reply("permission denied")

    def _on_command(self, c, e):
        """default handler for command events"""
        cmd, obj = e.raw
        self.bot.log(9, 'RUNNING: (%s) %s' \
                     % (time.strftime('%H:%M:%S'), obj))
        obj(cmd)
        self.bot.log(9, 'RETURNED: (%s)' % time.strftime('%H:%M:%S'))

    ############################################################

    def _do_command(self, nm, channel, command, connection, event):
        """called by the pubmsg and privmsg handlers
        creates the reply object and command object, and passes
        it on to _run()"""
        
        self.bot.log(3, 'COMMAND: %s, %s, %s' % (nm, channel, command))
        if isinstance(connection, DirectConnection):
            #nick = '!'+nm # the '!' marks it as direct - it's hard to
            #              # get one in a REAL irc nick :)
            nick = nm # nickmask now starts with '!'
            reply = DirectConnectionReply(nick=nick, channel=channel,
                                             connection=connection)
        else:
            nick = nm_to_n(nm)
            reply = IRCReply(nick=nick, channel=channel,
                             connection=connection)

        com, args = self._cmd_split(command)
        cmd = Command(bot=self.bot, nick=nick, nickmask=nm, channel=channel,
                      connection=connection, cmd=com, args=args,
                      _reply_object=reply, event=event)
        self._run(cmd)

    ##############################################################
    def _run(self, cmd):
        """check permissions, look up function, and throw either a
        command_not_found, permission_denied, or command event"""
        
        
        if self._check_ignore(cmd): return
        
        command_name = self.bot.permdb.expand_alias(cmd.cmd)
        obj, cperm = self.bot.mod.find_object(command_name)
        
        if obj is None or not callable(obj):
            event = Event('command_not_found', cmd.nick, cmd.cmd,
                          [cmd.args], cmd)
            self.bot.handle_event(cmd.connection, event)
            return
        
        try:
            can_execute = self.bot.permdb.can_execute(command_name, obj,
                                                      cperm, cmd)
            reason = []
        except PermError, e:
            can_execute = 0
            reason = list(e.args)
        if not can_execute:
            event = Event('permission_denied', cmd.nick, cmd.cmd,
                          reason, cmd)
            self.bot.handle_event(cmd.connection, event)
            return

        event = Event('command', cmd.nick, cmd.cmd, [cmd.args], [cmd, obj])
        self.bot.handle_event(cmd.connection, event)

    _ignore_perm = cpString('ignore')
    def _check_ignore(self, cmd):
        user = self.bot.ircdb.get_user(nickmask=cmd.nickmask)
        if user:
            uperms = user.get_perms()
            userid = user.userid
        else:
            uperms = self.bot.permdb.get_unknown_perms()
            userid = 'unknown'

        context = {'bot': self.bot, 'cmd': cmd}
        if self._ignore_perm.trycheck(uperms, context):
            self.bot.log(2, "IGNORING: nick=%s, userid=%s" % \
                    (cmd.nick, user.userid))
            return 1 # silently ignore
        else:
            return 0


    #############################################################
    # helper functions (uninteresting)
    
    def _cmd_split(self, command):
        """split a command line into command and args
        args is a single string"""

        cmd_list = string.split(command, ' ', 1)
        cmd = cmd_list.pop(0)
        if cmd_list: args = string.strip(cmd_list[0])
        else: args = ''
        return cmd, args
        


class ReplyObject:
    """Base class for the different reply types.  Mostly, this just
    provides the _get_target_and_message method

    Reply objects are created automatically in CommandHandler._run
    """

    def __init__(self, **kwargs):
        """Args: nick, channel (or None), Connection object"""
        self.__dict__.update(kwargs)

    def _get_target_and_message(self, arg_list):
        """arg_list should contain either 1 or >1 elements
        If >1, the first should be the "target", either a nick or channel.
           the other arguments will be joined to form the message
        If 1, it is interpreted as the message, and the target will be
           chosen based on the nature of the incoming command.  If it
           was private, the reply will be private if it was public, the
           reply will be public.
           """
        if len(arg_list) == 0: return(None, None)
        elif len(arg_list) == 1:
            if self.channel: target = self.channel
            else: target = self.nick
            message = str(arg_list[0])
        else:
            target = arg_list[0]
            message = string.join(map(str, arg_list[1:]), ' ')
        return(target, message)
        
class IRCReply(ReplyObject):
    """This is the class for IRC replies to commands.  Every Command
    object has a reply object.  The public methods of this class will
    be available as methods of Command instances directly."""

    def privmsg(self, *args):
        """default reply mechanism, if multiple args, first is interpreted
        as the target (either nick or channel).  Otherwise, reply will
        be the same as the command.  That is, a publicly-asked command
        will get a public response.

        the methods reply and privmsg are identical"""
        target, message = self._get_target_and_message(args)
        self.connection.privmsg(target, message)
    reply = privmsg

    def notice(self, *args):
        """same as reply/privmsg, but sends an irc notice instead.
        Some clients handle notices differently from privmsgs, which
        may be good or bad :)"""
        target, message = self._get_target_and_message(args)
        self.connection.notice(target, message)

    def nreply(self, *args):
        """same as reply, but if it's a public response, the user's nick
        (the one who typed the command) is prepended"""
        target, message = self._get_target_and_message(args)
        if is_channel(target): message = '%s: %s' % (self.nick, message)
        self.connection.privmsg(target, message)
        
    def nnotice(self, *args):
        """same as nreply, but with notice instead of privmsg"""
        target, message = self._get_target_and_message(args)
        if is_channel(target): message = '%s: %s' % (self.nick, message)
        self.connection.notice(target, message)
        
    def msg(self, *args):
        """will _always_ respond privately, even if the command was in
        a channel"""
        self.connection.privmsg(self.nick, ' '.join(args))

    def pnotice(self, *args):
        """like msg, but with a notice"""
        self.connection.notice(self.nick, ' '.join(args))

class NoReply(ReplyObject):
    """This class is for those times when you want to suppress any return
    communication from the bot. It behaves just like IRCReply, but doesn't
    do anything, except log what an IRCReply would have done.
    
    Needs to be inited with nick, channel and connection as normal.
    You also need bot=bot object if you want to log the actions.
    """

    def privmsg(self, *args):
        """default reply mechanism, if multiple args, first is interpreted
        as the target (either nick or channel).  Otherwise, reply will
        be the same as the command.  That is, a publicly-asked command
        will get a public response.

        the methods reply and privmsg are identical"""
        target, message = self._get_target_and_message(args)
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.privmsg: %s: %s" % (target, message))
    reply = privmsg

    def notice(self, *args):
        """same as reply/privmsg, but sends an irc notice instead.
        Some clients handle notices differently from privmsgs, which
        may be good or bad :)"""
        target, message = self._get_target_and_message(args)
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.notice: %s: %s" % (target, message))

    def nreply(self, *args):
        """same as reply, but if it's a public response, the user's nick
        (the one who typed the command) is prepended"""
        target, message = self._get_target_and_message(args)
        if is_channel(target):
            message = '%s: %s' % (self.nick, message)
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.nreply: %s: %s" % (target, message))
        
    def nnotice(self, *args):
        """same as nreply, but with notice instead of privmsg"""
        target, message = self._get_target_and_message(args)
        if is_channel(target):
            message = '%s: %s' % (self.nick, message)
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.nnotice: %s: %s" % (target, message))
        
    def msg(self, *args):
        """will _always_ respond privately, even if the command was in
        a channel"""
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.msg: %s: %s" % (target, message))

    def pnotice(self, *args):
        """like msg, but with a notice"""
        if hasattr(self, "bot"):
            self.bot.log(7, "NoReply.pnotice: %s: %s" % (target, message))

class DirectConnectionReply(ReplyObject):
    """This is the class for DirectConnection replies.  These basically
    all do the same thing (write to the direct connection), but with
    different prefixes so you can see which method as called."""
    
    def privmsg(self, *args):
        target, message = self._get_target_and_message(args)
        self.connection.write('PRIVMSG(%s): %s\n' % (target, message))
    reply = privmsg
    def notice(self, *args):
        target, message = self._get_target_and_message(args)
        self.connection.write('NOTICE(%s): %s\n' % (target, message))
    def nreply(self, *args):
        target, message = self._get_target_and_message(args)
        self.connection.write('NREPLY(%s): %s\n' % (target, message))
    def nnotice(self, *args):
        target, message = self._get_target_and_message(args)
        self.connection.write('NNOTICE(%s): %s\n' % (target, message))
    def msg(self, *args):
        self.connection.write('MSG: %s\n' % str(args))
    def pnotice(self, *args):
        self.connection.write('PNOTICE: %s\n' % str(args))
        
class Command:
    """An instance of this class will be created for each command, and
    will be passed to every command function.  Creation is automatic
    (in CommandHandler._do_command).

    The public attributes are:
      cmd.bot      - the bot object
      cmd.nick     - nick of the user who executed the command
      cmd.nickmask - nickmask of the user who executed the command
      cmd.channel  - channel on which it was executed (or None if private)
      cmd.cmd      - the string command as it was typed
      cmd.args     - single string containing the args (stuff after cmd.cmd)
      cmd.event    - the raw event (instance of kibot.m_irclib.Event) that
                     led to the command (probably a pubmsg or privmsg event)

    There are also a number of convenience methods (documented below):
      cmd.asplit(maxsplit=-1)
      cmd.shsplit(maxsplit=-1)

    In addition to the above methods, each of the IRCReply methods are
    copied in and are available directly as Command methods.
    """

    def __init__(self, **kwargs):
        """bot=self.bot, nick=nick, nickmask=nickmask, channel=channel,
        cmd=cmd, args=args, _reply_object=reply, event=event"""
        self.__dict__.update(kwargs)
        ## this is temporary - the reply_object should be supplied by
        ## the bot!
        if not hasattr(self, '_reply_object'):
            self._reply_object = FileObjectReply(nick=self.nick,
                                                 channel=self.channel,
                                                 connection=sys.stdout)

        for meth in 'privmsg reply notice nnotice nreply msg pnotice'.split():
            setattr(self, meth, getattr(self._reply_object, meth))
            
    def __str__(self):
        return "%s, %s, %s %s" % (self.nick, self.channel, self.cmd, self.args)
    
    def asplit(self, maxsplit=-1):
        """split the arguments string on whitespace"""
        return string.split(self.args, None, maxsplit)

    def shsplit(self, maxsplit=-1):
        """split the arguments string shell-style (quotes and backslashes)"""
        st = self.args
        if maxsplit == 0: return [st]
        arglist = []
        state = []
        carg = ''
        (BACKSLASH, SINGLE, DOUBLE) = (0, 1, 2)
        index = -1
        for char in st:
            index += 1
            if char == '"': # double quote
                if BACKSLASH in state:
                    carg = carg + char
                    state.remove(BACKSLASH)
                elif SINGLE in state:
                    carg = carg + char
                elif DOUBLE in state:
                    state.remove(DOUBLE)
                else:
                    state.append(DOUBLE)
            elif char == "'": # single quote
                if BACKSLASH in state:
                    carg = carg + char
                    state.remove(BACKSLASH)
                elif SINGLE in state:
                    state.remove(SINGLE)
                elif DOUBLE in state:
                    carg = carg + char
                else:
                    state.append(SINGLE)
            elif char == '\\': # backslash
                if BACKSLASH in state:
                    carg = carg + char
                    state.remove(BACKSLASH)
                else:
                    state.append(BACKSLASH)
            elif char in ' \t': # whitespace
                if BACKSLASH in state:
                    carg = carg + char
                    state.remove(BACKSLASH)
                elif SINGLE in state:
                    carg = carg + char
                elif DOUBLE in state:
                    carg = carg + char
                elif carg:
                    arglist.append(carg)
                    carg = ''
                    if maxsplit and maxsplit == len(arglist):
                        arglist.append(st[index:].strip())
                        break
            else: # not quote, backslash, or whitespace
                carg = carg + char
        if carg: arglist.append(carg)
        return arglist

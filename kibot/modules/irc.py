import kibot.BaseModule
from kibot.PermObjects import cpString, cpTargetChannel

from kibot.irclib import nm_to_n, parse_channel_modes, is_channel
from kibot.m_irclib import Timer

class irc(kibot.BaseModule.BaseModule):
    """basic irc operations and channel management"""

    _command_groups = (
        ('user',  ('op', 'kick', 'invite')),
        ('bot',   ('channels', 'join', 'nick', 'part')),
        ('admin', ('oper', 'mode', 'raw')),
        )

    def __init__(self, bot):
        kibot.BaseModule.BaseModule.__init__(self, bot)

        self._set_handlers()
        self._ping_timer = Timer(60, self._ping_func, repeat=60) 
        self.bot.set_timer(self._ping_timer)

    def _unload(self):
        self._del_handlers()
        self.bot.del_timer(self._ping_timer)

    def _ping_func(self):
        self.bot.conn.ping(':ALIVECHECK')
        return 1
    
    _autoop_cperm = cpTargetChannel('autoop')
    _op_cperm = cpTargetChannel('op')
    def op(self, cmd):
        """give ops to someone
        irc.op [channel] [nick(s)]
        """
        args = cmd.asplit()
        channel = cmd.channel    # default channel
        if args and is_channel(args[0]): channel = args.pop(0)
        if not channel:
            cmd.reply("What channel?")
            return
        elif not self._i_have_op(channel):
            cmd.reply("I don't have ops on %s" % channel)
            return
        
        if args: nicks = args
        else: nicks = [cmd.nick]

        chan_obj = self.bot.ircdb.channels[channel]
        chnicks = chan_obj.users()
        chopers = chan_obj.opers()
        for nick in nicks:
            if nick not in chnicks:
                cmd.reply("There is no %s on %s" % (nick, channel))
            elif nick in chopers:
                cmd.reply("%s already has ops on %s" % (nick, channel))
            else:
                self.bot.conn.mode(channel, '+o '+nick)
        
    _invite_cperm = cpTargetChannel('invite')
    def invite(self, cmd):
        """invite a user to an invite-only channel
        irc.invite [channel] [nick(s)]
        """
        args = cmd.asplit()
        channel = cmd.channel    # default channel
        if args and is_channel(args[0]): channel = args.pop(0)
        if not channel:
            cmd.reply("What channel?")
            return
        
        if args: nicks = args
        else: nicks = [cmd.nick]

        chan_obj = self.bot.ircdb.channels[channel]
        chnicks = chan_obj.users()
        for nick in nicks:
            if nick in chnicks:
                cmd.reply("%s is already on %s" % (nick, channel))
            else:
                self.bot.conn.invite(nick, channel)
        
    _kick_cperm = 'kick'
    def kick(self, cmd):
        """kick a user from a channel
        irc.kick [channel] nick(s) [comment]
        """
        args = cmd.shsplit()
        channel = cmd.channel    # default channel
        comment = "have a nice day!"
        ircdb = self.bot.ircdb
        nicks = []

        if args and is_channel(args[0]): channel = args.pop(0)
        while args:
            if ircdb.users.has_key(args[0]): nicks.append(args.pop(0))
            else: break
        if args: comment = ' '.join(args)
        if comment.startswith('comment='): comment = comment[8:]
        if not channel:
            cmd.reply("What channel?")
            return
        elif not self._i_have_op(channel):
            cmd.reply("I don't have ops on %s" % channel)
            return

        chan_obj = self.bot.ircdb.channels[channel]
        chnicks = chan_obj.users()
        chopers = chan_obj.opers()
        for nick in nicks:
            if nick not in chnicks:
                cmd.reply("There is no %s on %s" % (nick, channel))
            else:
                self.bot.conn.kick(channel, nick, comment)
        
    _part_cperm = 'manager'
    def part(self, cmd):
        """tell the bot to leave a channel
        irc.part [channel]"""
        if cmd.args:
            channel = cmd.args
        else:
            if cmd.channel is None:
                return cmd.reply("What channel?")
            else:
                channel = cmd.channel

        if not self.bot.ircdb.channels.has_key(channel):
            return cmd.reply("I'm not on that channel")
        else:
            self.bot.conn.part(channel)

    _join_cperm = cpString('manager')
    def join(self, cmd):
        """tell the bot to join a channel
        irc.join <channel>
        """
        if self.bot.ircdb.channels.has_key(cmd.args):
            cmd.reply("I'm already on that channel")
        elif not is_channel(cmd.args):
            cmd.reply("that's not a legal channel")
        else:
            args = cmd.asplit()
            channel = args[0]
            key = None
            
            if len(args) > 2:
                cmd.reply("too many arguments")
            elif len(args) == 2:
                key = args[1]

            if key is not None:
                self.bot.conn.join(channel, key)
            else:
                self.bot.conn.join(channel)

    _nick_cperm = 'manager'
    def nick(self, cmd):
        """tell the bot to change nicks
        irc.nick <newnick>
        """
        if len(cmd.asplit()) > 1:
            cmd.reply('bad nick: "%s"' % cmd.args)
        else:
            self.bot.ircdb.set_nick(cmd.args, self._nick_callback, cmd)

    def _nick_callback(self, result, data):
        if not result:
            data.reply('failed to set nick')

    _channels_cperm = 1
    def channels(self, cmd):
        """list channels
        irc.channels"""
        channels = ' '.join(self.bot.ircdb.channels.keys())
        cmd.reply(channels)

    _oper_cperm = 'manager'
    def oper(self, cmd):
        '''tell the bot to become an IRCop
        oper <operator class> <password>'''
        args = cmd.asplit()
        if not len(args) == 2:
            cmd.reply('syntax: oper <operator class> <password>')
            return
        self.bot.conn.oper(args[0], args[1])

    _mode_cperm = 'manager'
    def mode(self, cmd):
        '''execute a raw MODE command
        mode [target] <modes> [mode args]'''
        if cmd.args[0] in '+-':
            target = self.bot.nick
            command = cmd.args
        else:
            args = cmd.asplit(1)
            if len(args) < 2:
                cmd.reply('syntax: mode [target] <modes> [mode args]')
                return
            target, command = args
        self.bot.conn.mode(target, command)

    _raw_cperm = 'manager'
    def raw(self, cmd):
        """send raw text to the irc server
        raw <text>"""
        self.bot.conn.send_raw(cmd.args)
    ################################################################
    def _i_have_op(self, ch):
        mynick = self.bot.nick
        try:
            return self.bot.ircdb.channels[ch].is_oper(mynick)
        except KeyError:
            return 0
        
    def _on_invite(self, c, e):
        channel = e.args[0]
        nick = nm_to_n(e.source)
        user = self.bot.ircdb.get_user(nickmask=e.source)
        if not user: return
        uperms = user.get_perms()

        context = {'bot': self.bot, 'channel': 'NONE'}
        if self._join_cperm.trycheck(uperms, context):
            self.bot.conn.join(channel)

    def _on_mode(self, c, e):
        mynick = self.bot.nick
        modes = parse_channel_modes(' '.join(e.args))
        t = e.target
        if is_channel(t):
            if not self._i_have_op(t): return
            for sign, mode, nick in modes:
                if sign == "+" and mode == "o" and nick == mynick:
                    self._check_all(c, t)

    def _on_whoreply(self, c, e):
        """op people on a channel that the bot just joined

        when the bot joins a channel, it does a 'who' to see who's there"""
        
        ch = e.args[0]
        if not self._i_have_op(ch): return
        nick = e.args[4]
        user = self.bot.ircdb.get_user(nickmask=e.source)
        if not user: return

        context = {'bot': self.bot, 'channel': 'NONE', 'target': ch}
        if self._autoop_cperm.trycheck(uperms, context):
            self.bot.log(3, 'IRC: op-ing %s on %s' % (user.userid, ch))
            c.mode(ch, '+o '+nick)

    def _on_join(self, c, e):
        ch = e.target

        nick = nm_to_n(e.source)
        user = self.bot.ircdb.get_user(nickmask=e.source)
        if not user: return
        uperms = user.get_perms()

        ## first do any invites
        #channels = self.bot.ircdb.channels
        #for chan_name, chan_obj in channels.items():
        #    #self.bot.log(9, 'irc._on_join: checking %s' % chan_name)
        #    if not chan_obj.is_invite_only(): continue
        #    #self.bot.log(9, 'irc._on_join: %s is invite-only' % chan_name)
        #    if chan_obj.has_user(nick): continue
        #    #self.bot.log(9, 'irc._on_join: %s is not on %s' % (nick, chan_name))
        #    context = {'bot': self.bot, 'channel': 'NONE', 'target': chan_name}
        #    if self._invite_cperm.trycheck(uperms, context):
        #        self.bot.log(3, 'IRC: inviting %s to %s' \
        #                     % (user.userid, chan_name))
        #        c.invite(nick, chan_name)
        
        # give ops
        if not self._i_have_op(ch): return

        context = {'bot': self.bot, 'channel': 'NONE', 'target': ch}
        if self._autoop_cperm.trycheck(uperms, context):
            self.bot.log(3, 'IRC: op-ing %s on %s' % (user.userid, ch))
            c.mode(ch, '+o '+nick)

    def _check_invites(self, userid, nicks, channels):
        ircdb = self.bot.ircdb
        user = ircdb.get_user(userid=userid)
        if user is None:
            self.bot.log('userid "%s" returned no user in irc._check_invites' \
                         % userid)
            #print userid, nicks, channels, user
            return
        uperms = user.get_perms()
        context = {'bot': self.bot, 'channel': 'NONE', 'target': None}
        for chan_name in channels:
            chan_obj = ircdb.channels[chan_name]
            #self.bot.log(9, 'IRC: %s %s %s' % (chan_name, userid, nick))
            #self.bot.log(9, 'IRC: has_user = %s' % chan_obj.has_user(nick))
            context['target'] = chan_name
            if not chan_obj.is_invite_only(): continue
            #self.bot.log(9, 'IRC: %s is invite-only' % chan_name)

            #for nick in nicks:
            #    # if one of the nicks isn't present, then do the check
            #    if not chan_obj.has_user(nick): break
            #    #self.bot.log(9, 'IRC: nick %s is not on %s' % (nick, chan_name))
            #else: continue # otherwise, don't

            if self._invite_cperm.trycheck(uperms, context):
                self.bot.log(3, 'IRC: inviting %s to %s' % (userid, chan_name))
                for nick in nicks:
                    if not chan_obj.has_user(nick):
                        self.bot.conn.invite(nick, chan_name)
            #else:
            #    self.bot.log(9, 'IRC: %s failed invite perm check' % nick)

    def _check_ops(self, userid, nicks, channels):
        ircdb = self.bot.ircdb
        user = ircdb.get_user(userid=userid)
        uperms = user.get_perms()
        context = {'bot': self.bot, 'channel': 'NONE', 'target': None}
        for chan_name in channels:
            chan_obj = ircdb.channels[chan_name]
            #self.bot.log(9, 'IRC: %s %s %s' % (chan_name, userid, nick))
            #self.bot.log(9, 'IRC: has_user = %s' % chan_obj.has_user(nick))
            context['target'] = chan_name
            for nick in nicks:
                if not chan_obj.has_user(nick): continue
                if chan_obj.is_oper(nick): continue
                if not self._autoop_cperm.trycheck(uperms, context): continue
                self.bot.log(3, 'IRC: op-ing %s on %s' % (userid, chan_name))
                self.bot.conn.mode(chan_name, '+o '+nick)
                
    def _on_int_auth_mask(self, c, e):
        channels = self.bot.ircdb.channels.keys()
        self._check_invites(e.source, [e.target], channels)
        if not 'join' in e.args:
            self._check_ops(e.source, [e.target], channels)

    def _on_int_auth_recognize(self, c, e):
        channels = self.bot.ircdb.channels.keys()
        self._check_invites(e.source, [e.target], channels)
        self._check_ops(e.source, [e.target], channels)

    _on_int_auth_pass = _on_int_auth_recognize

    def _on_int_give_perm(self, c, e):
        userid = e.source
        nicks = self.bot.ircdb.get_nicks(userid=userid)
        channels = self.bot.ircdb.channels.keys()
        self._check_invites(e.source, nicks, channels)
        self._check_ops(e.source, nicks, channels)

    def _check_all(self, c, channel):
        """This is called when the bot gets ops.  It then scans the
        channel for others to give ops to."""
        ircdb = self.bot.ircdb
        chan_obj = ircdb.channels[channel]
        users = chan_obj.users()
        opers = chan_obj.opers()
        for oper in opers:
            if oper in users: users.remove(oper)

        permdb = self.bot.permdb
        context = {'bot': self.bot, 'channel': 'NONE', 'target': channel}
        for nick in users:
            user = self.bot.ircdb.get_user(nick)
            if user and self._autoop_cperm.trycheck(user.get_perms(), context):
                self.bot.log(3, 'IRC: op-ing %s on %s' % \
                             (user.userid, channel))
                c.mode(channel, '+o '+nick)


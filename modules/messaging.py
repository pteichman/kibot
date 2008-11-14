import re
import time
from kibot.BaseModule import BaseModule
from kibot.m_irclib import nm_to_n, Timer
from kibot.Settings import Setting

class messaging(BaseModule):
    """messages, ping notification and user tracking"""

    def _update_notify_interval(self, name):
        if getattr(self, '_message_notify_timer', None):
            self.bot.del_timer(self._message_notify_timer)
        self._message_notify_timer = Timer(0, self._message_notify_func,
                                           repeat=self.notify_interval * 3600)
        self.bot.set_timer(self._message_notify_timer)
        
    _settings = [
        Setting('seen_length', 30,
                'number of days to remember having "seen" someone',
                conv_func=float),
        Setting('notify_interval', 12,
                'number of hours to wait between message notification',
                conv_func=float, update_func=_update_notify_interval)
        ]

    _stash_attrs = ['seen_nicks', 'seen_userids', 'seen_length',
                    'last_notify', 'notify_interval',
                    'userid_messages', 'nick_messages',
                    'notify_list']

    _commands = ['seen', 'message', 'umessage', 'messages', 'ping_notify']

    def __init__(self, bot):
        self.notify_list = {}
        self.seen_nicks = {}
        self.seen_userids = {}
        self.nick_messages = {}
        self.userid_messages = {}
        self.last_notify = {}
        BaseModule.__init__(self, bot)
        self._prune_timer = Timer(60, self._prune_seen_maps, repeat=24*3600)
        self.bot.set_timer(self._prune_timer)
        self._update_notify_interval('notify_interval')
        
    def _unload(self):
        BaseModule._unload(self)
        self.bot.del_timer(self._prune_timer)
        self.bot.del_timer(self._message_notify_timer)
        
    _ping_notify_cperm = 1
    def ping_notify(self, cmd):
        """ask for notification of pings
        ping_notify [on|off]"""
        userid = self.bot.ircdb.get_userid(cmd.nick)
        if not userid: return cmd.reply("I don't know you")

        if not cmd.args:
            pass
        elif cmd.args in ['on', '1', 'yes', 'y', 'true', 't']:
            self.notify_list[userid] = 1
            self._stash()
        elif cmd.args in ['off', '0', 'no', 'n', 'false', 'f']:
            self.notify_list[userid] = 0
            self._stash()
        else:
            return cmd.reply('syntax: ping_notify [on|off]')
        
        status = self.notify_list.get(userid)
        if status: s = 'on'
        else:      s = 'off'
        cmd.reply('ping notification for %s is %s' % (userid, s))

        
    _seen_cperm = 1
    def seen(self, cmd):
        """ask if the bot has seen another user
        seen <userid/nick> [more userids/nicks]"""

        args = cmd.asplit()
        searchchannels = []

        if cmd.channel:
            # for privacy reasons, a public "seen" will be interpreted as
            # "have you seen <nick> _HERE_"
            searchchannels.append(cmd.channel)
        else:
            # you're only allowed results from channels you are currently on!
            for ch_name, ch in self.bot.ircdb.channels.items():
                if ch.has_user(cmd.nick): searchchannels.append(ch_name)

        for target in args:
            last = self._seen_target(target, searchchannels)
            if not last: msg = 'I have not seen %s' % target
            elif last['ident'] == 'userid':
                msg = "%(userid)s (as %(nick)s) was last seen on " \
                      "%(channel)s at %(htime)s" % last
            else:
                msg = "%(nick)s was last seen on " \
                      "%(channel)s at %(htime)s" % last
            cmd.reply(msg)

    def _seen_target(self, target, searchchannels):
        last = None
        last_t = 0.0
        for ch_name in searchchannels:
            try: l = self.seen_userids[ch_name][target]
            except: l = None
            if l and l['time'] > last_t: last = l

            try: l = self.seen_nicks[ch_name][target]
            except: l = None
            if l and l['time'] > last_t: last = l
        return last

    def _prune_seen_maps(self):
        cutoff = time.time() - self.seen_length * 24 * 3600
        for d in [self.seen_userids, self.seen_nicks]: # check both maps
            for ch_name, ch in d.items():       # check each channel
                for person, info in ch.items(): # check each person in the map
                    if info['time'] < cutoff: del ch[person]
                if len(ch) == 0: del d[ch_name] # remove empty channel maps
        return 1 # continue to repeat

    _message_cperm = 1
    def message(self, cmd):
        """leave a message for someone by nick
        message <nick> <message>"""
        target_nick, message = cmd.shsplit(1)
        self._store_message(target_nick, self.nick_messages,
                            [message], cmd.nick)
        if self.bot.ircdb.users.has_key(target_nick):
            userid = self.bot.ircdb.get_userid(nick=target_nick)
            self._notify(target_nick, userid)
        cmd.reply('done')
        
    _umessage_cperm = 1
    def umessage(self, cmd):
        """leave a message for someone by userid
        message <userid> <message>"""
        target_userid, message = cmd.shsplit(1)
        self._store_message(target_userid, self.userid_messages,
                            [message], cmd.nick)
        nicks = self.bot.ircdb.get_nicks(userid=target_userid)
        if nicks:
            for nick in nicks:
                self._notify(nick, target_userid)
        cmd.reply('done')

    def _store_message(self, target, message_map, message, nick):
        userid = self.bot.ircdb.get_userid(nick=nick),
        now = time.time()
        msg = {'message':     message,
               'nick':        nick,
               'userid':      userid,
               'time':        now,
               'htime':       time.ctime(now),
               'useridchunk': (userid or '') and ' (userid=%s)' % userid}
        if not message_map.has_key(target):
            message_map[target] = []
        message_map[target].append(msg)
        
    _messages_cperm = 1
    def messages(self, cmd):
        """retrieve your messages
        messages"""
        form = 'from %(nick)s%(useridchunk)s on %(htime)s:'
        keys = {'nick':   cmd.nick,
                'userid': self.bot.ircdb.get_userid(nick=cmd.nick)}
        notified = 0
        for idtype in ('userid', 'nick'):
            key = keys[idtype]
            m = getattr(self, idtype+'_messages')
            if not m.has_key(key): continue
            else: notified = 1
            message_list = m[key]
            del m[key]
            cmd.pnotice('messages for %s %s' % (idtype, key))
            for msg in message_list:
                cmd.pnotice(form % msg)
                for line in msg['message']: cmd.pnotice(line)
        if not notified:
            cmd.pnotice('no messages')

    def _message_notify_func(self):
        m = self.userid_messages
        nickmap = {}
        for userid, message_list in m.items():
            nicks = self.bot.ircdb.get_nicks(userid=userid)
            for nick in nicks:
                nickmap[nick] = {'userid': userid, 'tot':len(message_list)}
        m = self.nick_messages
        for nick, message_list in m.items():
            if not nickmap.has_key(nick):
                nickmap[nick] = {'userid': None,   'tot':0}
            nickmap[nick]['tot'] += len(message_list)

        now = time.time()
        for nick, entry in nickmap.items():
            last = self.last_notify.get(nick, 0.0)
            if now - last > self.notify_interval * 3600 * 0.5:
                self._notify(nick, entry['userid'], entry['tot'])
        for k in self.last_notify.keys():
            if not nickmap.has_key(k): del self.last_notify[k]
        return 1

    def _notify(self, nick, userid, tot=None):
        if tot is None:
            keys = {'nick':   nick,
                'userid': userid}
            tot = 0
            for idtype in ('userid', 'nick'):
                key = keys[idtype]
                m = getattr(self, idtype+'_messages')
                tot += len(m.get(key, []))

        if not tot: return
            
        self.last_notify[nick] = time.time()
        if tot == 1: plural = ''
        else: plural = 's'
        self.bot.conn.privmsg(nick, 'I have %i message%s for you.  ' \
                              'Send the command "messages" to me privately ' \
                              'to see them.' % (tot, plural))
        
    #######################################################
    # handlers

    def _on_join(self, c, e):
        nick = nm_to_n(e.source)
        userid = self.bot.ircdb.get_userid(nick=nick)
        if userid is None: self._notify(nick, None)
        
    def _on_int_auth_recognize(self, c, e):
        self._notify(e.target, e.source)
    _on_int_auth_pass = _on_int_auth_recognize
    _on_int_auth_mask = _on_int_auth_recognize

    _ping_re = re.compile(r'^(\S+)\s*[:,]\s*ping$')
    def _on_pubmsg(self, c, e):
        self._pubmsg_ping_notify_handler(c, e)
        self._pubmsg_seen_handler(c, e)

    def _pubmsg_ping_notify_handler(self, c, e):
        m = re.match(self._ping_re, e.args[0])
        if not m: return

        # it matched
        pingee = m.group(1)

        userid = self.bot.ircdb.get_userid(nick=pingee)
        if not self.notify_list.get(userid): return

        pinger = nm_to_n(e.source)
        channel = e.target
        now = time.strftime('%c', time.localtime())

        nicks = self.bot.ircdb.get_nicks(userid=userid)

        if nicks == [pingee]:
            msg = '%s pinged you on %s on %s' % \
                  (pinger, channel, now)
        else:
            msg = '%s pinged you (%s) on %s on %s' % \
                  (pinger, pingee, channel, now)

        for nick in nicks: self.bot.conn.privmsg(nick, msg)

    def _pubmsg_seen_handler(self, c, e):
        nick = nm_to_n(e.source)
        userid = self.bot.ircdb.get_userid(nickmask=e.source)
        channel = e.target
        now = time.time()
        self._update_seen_maps(nick, userid, channel, now)

    def _on_ctcp_action(self, c, e):
        nick = nm_to_n(e.source)
        userid = self.bot.ircdb.get_userid(nickmask=e.source)
        channel = e.target
        now = time.time()
        self._update_seen_maps(nick, userid, channel, now)
        
    def _update_seen_maps(self, nick, userid, channel, now):
        last = {'ident': 'nick',
                'nick': nick,
                'userid': userid,
                'channel': channel,
                'time': now,
                'htime': time.ctime(now)}

        if not self.seen_nicks.has_key(channel):
            self.seen_nicks[channel] = {}
        self.seen_nicks[channel][nick] = dict(last)

        if userid:
            last['ident'] = 'userid'
            if not self.seen_userids.has_key(channel):
                self.seen_userids[channel] = {}
            self.seen_userids[channel][userid] = last

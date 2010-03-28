import hashlib
import pickle
import re
import os
import os.path
import socket
import time
import types
import copy

from . import BaseModule
from . import Stasher
from .irclib import (nm_to_n, irc_lower, parse_channel_modes, is_channel,
                     mask_matches)
from .m_irclib import Timer, Event
from .PermObjects import UPermCache

class UserError(Exception): pass

class ircDB(BaseModule.BaseModule):
    """manages the following information 'automatically':

    list of channels
    list of users/ops/voiced/modes on each channel
    list of current users (on all channels)
    list of "known users" and User objects

    data structures:
      channel_dict = dict with channel names as keys, and channel objects
                     as values
      channel_obj  = object containing channel users/ops/voiced/modes
      current_users = dict mapping nicks to (channel list, nickmask, and
                      (if known) userid)
      known_users  = object mapping userids to user objects
    """
    _tmp_key = 'ircdb.data'
    def __init__(self, bot):
        self.bot = bot

        self.channels = IRCdict()  # channel name -> Channel instance
        self.users = IRCdict()     # nick         -> CurrentUser instance
        #                          # userid -> KnownUser instance

        ################################################################
        ## These next two lines are here for the mbot->kibot transition
        ## so that the ircdb file can be imported correctly
        ## this is happening at 0.0.7 -> 0.0.8 (roughly 17-apr-2003)
        ## They should be removed eventually
        ## This tricks pickle into thinking that it really does have
        ## mbot.ircDB, and that it's this module.  I'm sneaky :)
        import sys
        sys.modules['mbot.ircDB'] = sys.modules[self.__module__]
        ################################################################

        self.known   = Stasher.get_stasher(self.bot.op.files.ircdb_file)
        ircdata_file = os.path.join(self.bot.op.files.data_dir, 'ircdata.repr')
        self.ircdata = Stasher.get_stasher(ircdata_file)
        if not self.ircdata.has_key('channels'):
            self.ircdata['channels'] = {}

        if bot.tmp.has_key(self._tmp_key):
            self._reload()
        self._set_handlers(-5)

    def _unload(self):
        data = {'channels': self.channels,
                'users': self.users}
        self.bot.tmp[self._tmp_key] = pickle.dumps(data)
        self._del_handlers()
        self.save()

    def _reload(self):
        data = pickle.loads(self.bot.tmp[self._tmp_key])
        del self.bot.tmp[self._tmp_key]
        self.__dict__.update(data)

    def save(self):
        self.known.sync()
        self.ircdata.sync()

    ######################################################################

    # all of the functions in the next block effectively have these args:
    #   nick=None, nickmask=None, userid=None, user=None
    def get_nick(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if not nick: return None
        else: return nick

    def get_nickmask(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if not nick: None
        else: return self.users[nick].nickmask

    def get_nicks(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if userid:
            nicks = []
            for cnick, cu in self.users.items():
                if cu.userid == userid: nicks.append(cnick)
            return nicks
        elif nick:
            return [nick]
        else:
            return []

    def get_nickmasks(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if userid:
            nickmasks = []
            for cnick, cu in self.users.items():
                if cu.userid == userid: nickmasks.append(cu.nickmask)
            return nickmasks
        elif nickmask:
            return [nickmask]
        else:
            return []

    def get_userid(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if not userid: return None
        else: return userid

    def get_user(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if not userid: return None
        else: return user

    #####################################################################

    def del_user(self, *args, **kwargs):
        nick, nickmask, userid, user = self._fetch_all(*args, **kwargs)
        if not userid:
            raise UserError, "user not found"
        else:
            del self.known[userid]
            if nick: self.users[nick].userid = None

    def add_user(self, nick, userid=None, mask=None):
        """create a new new user/userid for nick"""
        _nick, _nickmask, _userid, _user = self._fetch_all(nick)
        if not _nick:
            raise UserError, "I don't see any '%s'" % (nick)
        if _userid:
            raise UserError, "%s is already known as userid '%s'" \
                  % (nick, _userid)
        if userid:
            if userid in ['default', 'unknown']:
                raise UserError, "illegal userid: '%s'" % (userid)
            if self.known.has_key(userid):
                raise UserError, "userid '%s' taken" % (userid)
        else:
            userid = nick
            if self.known.has_key(userid):
                i = 0
                while 1:
                    userid = "%s%i" % (nick, i)
                    if not self.known.has_key(userid): break
                    i = i + 1
        if mask is None:
            masks = [ self._default_mask_from_nickmask(_nickmask) ]
        elif mask == 'nomask':
            masks = []
        else:
            masks = [ mask ]

        ku = KnownUser(userid, masks=masks)
        self.known[userid] = ku
        self.users[nick].userid = userid
        return userid

    def rescan(self, nick=None, nickmask=None):
        """force rescan of nick/nickmask to see if we recognize them
        This is useful after a mask has been added to a user, for example."""
        if not nick is None:
            cu = self.users.get(nick)
            if not cu: return
            nickmask = cu.nickmask
        elif not nickmask is None:
            nick = nm_to_n(nickmask)
            cu = self.users.get(nick)
            if not cu: return
        else:
            return
        for userid, user in self.known.items():
            if user.mask_matches(nickmask):
                cu.userid = user.userid
                event = Event('int_auth_mask', userid, nick, ['scan'], None)
                self.bot.handle_event(self.bot.conn, event)
                return
        # DO NOT set cu.userid to None here.  It may have been set to
        # some userid by authpass, in which case, we should leave it
        #cu.userid = None

    def rescan_user(self, userid=None, user=None):
        if not userid is None:
            user = self.known.get(userid)
            if user is None: return
        elif not user is None:
            userid = user.userid
        else:
            return
        for nick, cu in self.users.items():
            if user.mask_matches(cu.nickmask):
                cu.userid = user.userid
                event = Event('int_auth_mask', userid, nick, ['scan'], None)
                self.bot.handle_event(self.bot.conn, event)
                return

    def set_nick(self, newnick, callback=None, cb_data=None):
        if type(newnick) == type(''):
            n = newnick
        elif type(newnick) == type(0):
            confnick = self.bot.op.irc.nick
            if type(confnick) == type(''): confnick = [confnick]

            if newnick == -1:
                try: n = self.ircdata['nick']
                except KeyError: n = None
                if n is None or n == confnick[0] or \
                   self.bot.op.admin.forget:
                    newnick = 0

            if newnick >= 0:
                n = self._get_uniq_nick(newnick, confnick)
        else:
            pass ##??

        self._set_nick_data = (newnick, n, callback, cb_data)
        self.bot.conn.nick(n)

    def _set_nick_return(self, tried_nick, result):
        nd = getattr(self, '_set_nick_data', None)
        if nd is None: return
        self._set_nick_data = None
        set_nick, text_nick, callback, cb_data = nd
        if not result:
            # failure
            if type(set_nick) == type(1):
                self.set_nick(set_nick + 1, callback)
                return
        else:
            # success
            self.bot.nick = text_nick
        if not callback is None: callback(result, cb_data)

    def _get_uniq_nick(self, ind, nicklist):
        if ind < len(nicklist): return nicklist[ind]
        diff = ind - len(nicklist)
        pad = '_^-'
        num = 1 + (diff / len(pad))
        typ = diff % len(pad)
        suf = pad[typ] * num
        return nicklist[0] + suf

    ##################################################################
    ### Support (private) functions
    def _fetch_all(self, nick=None, nickmask=None,
                   userid=None, user=None):
        #import traceback
        #traceback.print_stack()
        #print '_fetch_all', nick, nickmask, userid, user
        god = self._is_god_user(nick, nickmask, userid, user)
        if god: return god

        if not nick is None:
            cu = self.users.get(nick)
            if cu is None:
                return (None, None, None, None)
            else:
                return (nick, cu.nickmask, cu.userid,
                        self.known.get(cu.userid))

        elif not nickmask is None:
            nick = nm_to_n(nickmask)

            # first see if it's cached (if we're on a common channel)
            cu = self.users.get(nick)
            if not cu is None:
                return (nick, nickmask, cu.userid, self.known.get(cu.userid))

            for userid, user_obj in self.known.items():
                if user_obj.mask_matches(nickmask):
                    return (nick, nickmask, userid, user_obj)
            return (nick, nickmask, None, None)

        elif not userid is None:
            user = self.known.get(userid)
            if user is None: return (None, None, None, None)
            for nick, cu in self.users.items():
                if cu.userid == userid:
                    return (nick, cu.nickmask, userid, user)
            return (None, None, userid, user)

        elif not user is None:
            userid = user.userid
            for nick, cu in self.users.items():
                if cu.userid == userid:
                    return (nick, cu.nickmask, userid, user)
            return (None, None, userid, user)

        else:
            return (None, None, None, None)

    def _is_god_user(self, nick=None, nickmask=None,
                   userid=None, user=None):
        if nick and nick[0] == '!':
            user = GodUser()
            userid = user.userid
            nickmask = nick
            return (nick, nickmask, userid, user)
        elif nickmask and nickmask[0] == '!':
            user = GodUser()
            userid = user.userid
            nick = nickmask
            return (nick, nickmask, userid, user)
        else:
            return( () )

    def _rename_user(self, before, after):
        self.users[after] = self.users[before]
        if not irc_lower(before) == irc_lower(after): # tricky bastards
            del self.users[before]
        self.users[after].rename(before, after)

    def _default_mask_from_nickmask(self, nm):
        nick, userhost = nm.split('!')
        user, host = userhost.split('@')

        host_list = host.split('.')
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host): # numeric address
            # any machine in that class c subnet
            host = '.'.join(host_list[:-1]) + '.*'
        elif len(host_list) > 2: # got a name
            # any machine in that domain, unless it would be something like *.edu
            host = '*.' + '.'.join(host_list[1:])
        # any nick
        nick = '*'
        # any user "prefixes"
        while user[0] in '~': user = user[1:]
        user = '*' + user
        return '%s!%s@%s' % (nick, user, host)


    ##################################################################
    # automatic user-maintenance functions
    def _on_join(self, c, e):
        """[Internal]"""
        ch = e.target
        nm = e.source
        nick = nm_to_n(nm)
        if nick == self.bot.nick: # bot is joining
            self.ircdata['channels'][ch] = self.bot.conn.channel_keys.get(ch, 1)
            self.save()
            self.channels[ch] = Channel()
            c.who(ch)
            c.mode(ch, '') # query channel modes

        self.channels[ch].add_user(nick)

        cu = self.users.get(nick)
        if cu:
            cu.channels.append(ch)
        else:
            try: userid = self.get_userid(nickmask=nm)
            except UserError, msg: userid = None
            self.users[nick] = CurrentUser(nm, userid, [ch])
            if not userid is None:
                event = Event('int_auth_mask', nick, userid,
                              ['join'], None)
                self.bot.handle_event(self.bot.conn, event)

    def _on_channelmodeis(self, c, e):
        chan_name = e.args[0]
        raw_modes = ' '.join(e.args[1:])
        modes = parse_channel_modes(raw_modes)

        channel = self.channels[chan_name]
        for action, mode, value in modes:
            if action == "+": channel.set_mode(mode, value)
            else:             channel.clear_mode(mode, value)

    def _on_whoreply(self, c, e):
        a = e.args
        ch       = a[0]
        username = a[1]
        host     = a[2]
        nick     = a[4]
        nm = '%s!%s@%s' % (nick, username, host)

        if nick == self.bot.nick and not self.bot.hostname:
            self.bot.hostname = host
            try:
                self.bot.hostip   = socket.gethostbyname(host)
            except socket.gaierror:
                # some irc networks obscure hostnames in whois replies,
                # and dns lookups on those names will fail (synirc.net)
                pass

        self.channels[ch].add_user(nick)

        cu = self.users.get(nick)
        if cu:
            cu.add_channel(ch)
        else:
            try: userid = self.get_userid(nickmask=nm)
            except UserError, msg: userid = None
            self.users[nick] = CurrentUser(nm, userid, [ch])
            if not userid is None:
                event = Event('int_auth_mask', userid, nick,
                              ['whoreply'], None)
                self.bot.handle_event(self.bot.conn, event)

    def _on_kick(self, c, e):
        """[Internal]"""
        nick = e.args[0]
        ch = e.target

        if nick == self.bot.nick:
            del self.channels[ch]
            del self.ircdata['channels'][ch]
            self.save()
        else:
            self.channels[ch].remove_user(nick)
        self.users[nick].remove_channel(ch)

    def _on_mode(self, c, e):
        """[Internal]"""
        modes = parse_channel_modes(' '.join(e.args))
        t = e.target
        if is_channel(t):
            channel = self.channels[t]
            for mode in modes:
                if mode[0] == "+":
                    f = channel.set_mode
                else:
                    f = channel.clear_mode
                f(mode[1], mode[2])
        else:
            # Mode on self... XXX
            pass

    def _on_namreply(self, c, e):
        """[Internal]"""

        # e.args[0] == "="     (why?)
        # e.args[1] == channel
        # e.args[2] == nick list

        ch = e.args[1]
        for nick in e.args[2].split():
            if nick[0] == "@":
                nick = nick[1:]
                self.channels[ch].set_mode("o", nick)
            elif nick[0] == "+":
                nick = nick[1:]
                self.channels[ch].set_mode("v", nick)
            self.channels[ch].add_user(nick)

    def _on_nick(self, c, e):
        """[Internal]"""
        before = nm_to_n(e.source)
        after = e.target
        self._rename_user(before, after)
        for channel in self.channels.values():
            if channel.has_user(before):
                channel.change_nick(before, after)
        self.rescan(after)
        if nm_to_n(before) == self.bot.nick:
            self._set_nick_return(after, 1)
            self.bot.nick = after
            self.ircdata['nick'] = after
            self.save()

    def _on_nicknameinuse(self, c, e):
        attempted_nick = e.args[0]
        self._set_nick_return(attempted_nick, 0)

    def _on_part(self, c, e):
        """[Internal]"""
        nick = nm_to_n(e.source)
        ch = e.target

        if nick == self.bot.nick:
            del self.channels[ch]
            del self.ircdata['channels'][ch]
            self.save()
        else:
            self.channels[ch].remove_user(nick)
        self.users[nick].remove_channel(ch)
        if not self.users[nick].channels:
            del self.users[nick]

    def _on_quit(self, c, e):
        """[Internal]"""
        nick = nm_to_n(e.source)
        for channel in self.channels.values():
            channel.remove_user(nick)
        del self.users[nick]

    def _on_disconnect(self, c, e):
        """[Internal]"""
        self.channels = IRCdict()
        self.users = IRCdict()
        interval = self.bot.op.irc.reconnect_interval
        if interval:
            self._reconnect_timer = Timer(interval, self._reconnect_func, repeat=1)
            self.bot.set_timer(self._reconnect_timer)

    def _reconnect_func(self):
        if self.bot.connect():
            return 0
        else:
            return 1

    def _on_welcome(self, c, e):
        self._set_nick_return(None, 1) # we know the nick was accepted
        channels = self.ircdata['channels'].keys()
        self.bot.log(6, 'IRCDB: remembered channels: %s' % ' '.join(channels))
        if self.bot.op.admin.forget or not channels:
            channels = self.bot.op.irc.channels
            self.bot.log(6, 'IRCDB: using config channels: %s' % \
                         ' '.join(channels))
        for chan in channels:
            if type(self.ircdata['channels'][chan]) in types.StringTypes:
                key = self.ircdata['channels'][chan]
                self.bot.conn.join(chan, key)
            else:
                self.bot.conn.join(chan)

    def _on_int_new_mask(self, c, e):
        self.rescan_user(userid=e.source)

    def _on_topic(self, c, e):
        if is_channel(e.target): # someone just set the topic
            channel = self.channels[e.target]
            nick = nm_to_n(e.source)
            newtopic = e.args[0]

            channel.topic_setter(nick)
            channel.topic_time(time.time()) # this will be roughly correct
        else: # result of topic query
            channel = self.channels[e.args[0]]
            newtopic = e.args[1]

        channel.topic(newtopic)

    def _on_topicinfo(self, c, e):
        chan, nick, ttime = e.args
        channel = self.channels[chan]
        channel.topic_setter(nick)
        channel.topic_time(ttime)

class CurrentUser:
    def __init__(self, nickmask, userid=None, channels=None):
        self.nickmask = nickmask
        self.channels = channels or []
        self.userid = userid

    def add_channel(self, channel):
        if not channel in self.channels: self.channels.append(channel)
    def remove_channel(self, channel):
        if channel in self.channels: self.channels.remove(channel)
    def rename(self, before, after):
        self.nickmask = after + self.nickmask[len(before):]

class KnownUser:
    def __init__(self, userid, perms=None, masks=None, password=None):
        self.userid = userid
        self.perms = perms or []
        self.masks = masks or []
        if password:
            self.password = self.set_password(password)
        else:
            self.password = None
        self.cached_perms = None

    def __getstate__(self):
        # do this so pickle doesn't try and store the cached perms
        tmp = {}
        tmp.update(self.__dict__)
        tmp['cached_perms'] = None
        return tmp

    def __setstate__(self, dict):
        # copy the perms and masks arrays coming from pickle, to work
        # around old ircDB's that have many references to the same
        # array

        for key in ("perms", "masks"):
            if dict.has_key(key):
                dict[key] = copy.deepcopy(dict[key])

        self.__dict__ = dict

    def __repr__(self):
        r =     "KnownUser(userid=%s,\n" % repr(self.userid)
        r = r + "          perms=%s,\n" % repr(self.perms)
        r = r + "          masks=%s,\n" % repr(self.masks)
        r = r + "          password=%s)" % repr(self.password)
        return r

    #########################################################
    # mask functions
    def mask_matches(self, nickmask):
        for m in self.masks:
            if mask_matches(nickmask, m): return 1
        return 0

    def add_mask(self, mask):
        if mask not in self.masks:
            self.masks.append(mask)

    def remove_mask(self, mask):
        try:
            if type(mask) == type(1):
                del self.masks[mask]
            else:
                self.masks.remove(mask)
        except (IndexError, ValueError), msg:
            pass

    def get_masks(self):
        return list(self.masks)

    #########################################################
    # perm functions
    def add_perm(self, perm):
        if type(perm) == type(''): perm = [perm]
        for p in perm:
            if not p in self.perms: self.perms.append(p)
        self.cached_perms = None

    def remove_perm(self, perm):
        if type(perm) == type(''): perm = [perm]
        for p in perm:
            if p in self.perms: self.perms.remove(p)
        self.cached_perms = None

    def get_perms(self):
        if getattr(self, 'cached_perms', None) is None:
            self.cached_perms = UPermCache(self.perms)
        return self.cached_perms

    def get_raw_perms(self):
        return list(self.perms)

    #########################################################
    # password functions
    def set_password(self, clear, ptype='sha'):
        """set the user's password
        clear can be either the new password, None/'' to unset the password,
        or a password tuple (ptype, crypted_password)"""
        if not clear: self.password = None
        elif type(clear) == type( () ):
            self.password = clear
        else:
            f = getattr(self, '_set_password_' + ptype)
            f(clear)

    def check_password(self, clear):
        if not self.password: return -1 # <- what should this be?
        ptype = self.password[0]
        f = getattr(self, '_check_password_' + ptype)
        return f(clear)

    ########################################################
    # raw password functions.  Create a pair for each password type
    def _set_password_sha(self, clear):
        sha_obj = hashlib.sha1.new(clear)
        self.password = ('sha', sha_obj.hexdigest())

    def _check_password_sha(self, clear):
        sha_obj = hashlib.sha1.new(clear)
        return self.password[1] == sha_obj.hexdigest()

class GodUser(KnownUser):
    def __init__(self):
        self.userid = ' GOD '
        # the 'god' perm will get around most "external" perm checks, which
        # are the ones done automatically when a command is called.  This
        # happens in permDB.can_execute().  The 'owner' perms is to try
        # and catch other commands that do things internally, like
        # auth.profile
        self.perms = ['god', 'owner']
        self.masks = []
        self.password = None
        self.cached_perms = None

class IRCdict(dict):
    def __init__(self):
        dict.__init__(self)
        self.keymap = {}

    def clear(self):
        dict.clear(self)
        self.keymap.clear()

    def has_key(self, key):
        return self.keymap.has_key(irc_lower(key))

    def __getitem__(self, key):
        true_key = self.keymap[irc_lower(key)]
        return dict.__getitem__(self, true_key)

    def __delitem__(self, key):
        lower = irc_lower(key)
        dict.__delitem__(self, self.keymap[lower])
        del self.keymap[lower]

    def __setitem__(self, key, value):
        if self.has_key(key):
            del self[key]
        dict.__setitem__(self, key, value)
        self.keymap[irc_lower(key)] = key

class Channel:
    def __init__(self):
        self.userdict = IRCdict()
        self.operdict = IRCdict()
        self.voiceddict = IRCdict()
        self.modes = {}
        self.topic_info = {'topic':None, 'time':None, 'nick':None}

    def topic(self, newtopic=None):
        if not newtopic is None:
            self.topic_info['topic'] = newtopic
        return self.topic_info['topic']

    def topic_setter(self, newsetter=None):
        if not newsetter is None:
            self.topic_info['nick'] = newsetter
        return self.topic_info['nick']

    def topic_time(self, newtime=None):
        if not newtime is None:
            self.topic_info['time'] = int(newtime)
        return self.topic_info['time']

    def users(self):
        """Returns an unsorted list of the channel's users."""
        return self.userdict.keys()

    def opers(self):
        """Returns an unsorted list of the channel's operators."""
        return self.operdict.keys()

    def voiced(self):
        """Returns an unsorted list of the persons that have voice
        mode set in the channel."""
        return self.voiceddict.keys()

    def has_user(self, nick):
        """Check whether the channel has a user."""
        return self.userdict.has_key(nick)

    def is_oper(self, nick):
        """Check whether a user has operator status in the channel."""
        return self.operdict.has_key(nick)

    def is_voiced(self, nick):
        """Check whether a user has voice mode set in the channel."""
        return self.voiceddict.has_key(nick)

    def add_user(self, nick):
        self.userdict[nick] = 1

    def remove_user(self, nick):
        for d in self.userdict, self.operdict, self.voiceddict:
            if d.has_key(nick):
                del d[nick]

    def change_nick(self, before, after):
        self.userdict[after] = 1
        del self.userdict[before]
        if self.operdict.has_key(before):
            self.operdict[after] = 1
            del self.operdict[before]
        if self.voiceddict.has_key(before):
            self.voiceddict[after] = 1
            del self.voiceddict[before]

    def set_mode(self, mode, value=None):
        """Set mode on the channel.

        Arguments:

            mode -- The mode (a single-character string).

            value -- Value
        """
        if mode == "o":   self.operdict[value] = 1
        elif mode == "v": self.voiceddict[value] = 1
        else:             self.modes[mode] = value

    def clear_mode(self, mode, value=None):
        """Clear mode on the channel.

        Arguments:

            mode -- The mode (a single-character string).

            value -- Value
        """
        try:
            if mode == "o":   del self.operdict[value]
            elif mode == "v": del self.voiceddict[value]
            else:             del self.modes[mode]
        except KeyError:
            pass

    def has_mode(self, mode): return mode in self.modes
    def is_moderated(self):   return self.has_mode("m")
    def is_secret(self):      return self.has_mode("s")
    def is_protected(self):   return self.has_mode("p")
    def has_topic_lock(self): return self.has_mode("t")
    def is_invite_only(self): return self.has_mode("i")
    def has_limit(self):      return self.has_mode("l")
    def has_key(self):        return self.has_mode("k")

    def has_message_from_outside_protection(self):
        # Eh... What should it be called, really?
        return self.has_mode("n")

    def limit(self):
        if self.has_limit():
            return self.modes["l"]
        else:
            return None

    def key(self):
        if self.has_key():
            return self.modes["k"]
        else:
            return None

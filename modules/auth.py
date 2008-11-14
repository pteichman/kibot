"""The auth module contains commands for managing users, authentication,
and authorization.

USERS AND AUTHENTICATION

  Users "accounts" are created and deleted with the 'meet' and
  'forget' commands respectively.  The bot can be told to recognize a
  nick as a known user with the 'recognize' command, which can also be
  though of as something like the unix 'su' command.

  There are three ways a nick can be authenticated as a known user:
    1) by mask - if the user's profile contains a mask that matches
       the current nickmask, they will be automatically authenticated
    2) by password - passwords are managed with 'setpass' and 'authpass'
    3) via the 'recognize' command

AUTHORIZATION

  User permissions control what a user can and cannot do.  You can see
  what permissions a user has with the 'profile' command, and what
  'command permissions' (or cperm) are required by a command with the
  'perm' command.  For example:

    <michael> kibot: perm recognize
    <kibot> recognize requires: 'introduce'

  Permissions can be added and removed with the 'give' and 'take'
  commands.

PERMISSIONS TREES

  There are two "trees" of permission: the implies tree and the grants
  tree.  Each is a tree in the sense that one permission leads to
  other permissions, which may in turn lead to others.  If one
  permission is implied by another, it means the having the former
  means you automatically have the latter.

    <michael> kibot: implies
    <kibot> owner -> ['manager']
    <kibot> manager -> ['op', 'introduce', 'load', 'kick', 'invite']

  If a user has the 'manager' perm, then they automatically have the
  'op' perm.

  The grants tree controls what perms you can give to other people (or
  yourself) given the perms that you have.

    <michael> kibot: grants
    <kibot> owner -> ['manager', 'owner']
    <kibot> manager -> ['op', 'introduce', 'kick', 'ignore', 'invite']

  If a user has 'manager', they can give other people 'op', but they
  cannot give other people 'manager'.

SPECIAL USERS

  There are two special users: 'default' and 'unknown'.  The
  permissions possessed by the 'default' user will be given to newly
  created (via 'meet') users unless otherwise specified with the
  options to 'meet'.  The permissions possessed by the 'unknown' user
  are applied to anyone who is not recognized by the bot.  These users
  can be managed with the standard commands: 'profile', 'give', and
  'take'.

"""

from kibot.PermObjects import cpString
from kibot.ircDB import UserError
from kibot.m_irclib import Event

class auth:
    """user and authentication management"""

    _commands = """meet recognize unrecognize forget addmask delmask
    give take profile users whois
    grants addgrant delgrant implies addimply delimply
    authpass setpass""".split()
    
    _command_groups = (
        ('profile', ('profile', 'give', 'take',
                     'authpass', 'setpass', 'addmask', 'delmask')),
        ('users',   ('meet', 'recognize', 'unrecognize', 'forget',
                     'users', 'whois')),
        ('admin',   ('grants', 'addgrant', 'delgrant',
                     'implies', 'addimply', 'delimply'))
        )

    def __init__(self, bot):
        self.bot = bot

    _meet_cperm = 'introduce'
    def meet(self, cmd):
        """introduce a user to me
        auth.meet <nick> [<userid> [<mask>]] [with [only] <perms>]
        if <mask> is the special string "nomask", no mask will be set.
        <perms> can be automatically granted using "with".  If "with only" is
        used, the default perms with not be granted.
        """
        args = cmd.asplit()
        try:
            ind = args.index('with')
        except ValueError:
            perms = list(self.bot.permdb.default_perms)
        else:
            if args[ind+1:] and args[ind+1] == 'only':
                perms = args[ind+2:]
            else:
                perms = self.bot.permdb.default_perms + args[ind+1:]
            args = args[:ind]

        if len(args) == 1:
            nick = args[0]
            args = [nick, nick]
            if self.bot.ircdb.known.has_key(nick):
                msg = 'userid "%s" is taken.  Either provide another ' \
                      'userid with "meet %s <userid>" or (if nick "%s" ' \
                      'REALLY IS userid "%s") use "recognize %s"'
                cmd.reply(msg % (nick, nick, nick, nick, nick))
                return
        try:
            userid = self.bot.ircdb.add_user(*args)
        except UserError, msg:
            cmd.reply(str(msg))
            return
        else:
            cmd.reply('I now know %s as userid %s' % (args[0], userid))

        if perms:
            cmd.args = '%s %s' % (userid, ' '.join(perms))
            self.give(cmd)
        else: # self.give will also force save and send int_auth_recognize
            self.bot.ircdb.save()
            event = Event('int_auth_recognize', userid, args[0],
                          ['meet'], None)
            self.bot.handle_event(self.bot.conn, event)
            
    _forget_cperm = 'introduce'
    def forget(self, cmd):
        """forget a known user
        auth.forget <userid>
        """
        try:
            self.bot.ircdb.del_user(userid=cmd.args)
        except UserError, msg:
            cmd.reply("I don't know anyone by that userid")
        else:
            self.bot.ircdb.save()
            cmd.reply('Forgotten!')

    _recognize_cperm = 'introduce'
    def recognize(self, cmd):
        """recognize someone as a known user
        auth.recognize <nick> [<userid> [<mask>]]
        if <mask> is the special string "nomask", no mask will be added"""

        ircdb = self.bot.ircdb
        args = cmd.asplit()

        if args:
            nick = args.pop(0)
            current_user = ircdb.users.get(nick)
            if current_user is None:
                return cmd.reply("I don't see anyone with nick \"%s\"" \
                                 % nick)
        else:
            return cmd.reply('who shall I recognize?')

        if args:
            userid = args.pop(0)
            user = ircdb.get_user(userid=userid)
            if user is None:
                return cmd.reply('I do not know anyone with userid "%s"' \
                                 % userid)
        else:
            userid = nick
            user = ircdb.get_user(userid=userid)
            if user is None:
                cmd.reply('I do not know anyone with userid "%s"' % userid)
                cmd.reply('try "recognize <nick> <userid>"')
                return

        current_user.userid = userid
        cmd.reply('I now recognize %s as userid %s' % (nick, userid))

        if args and not args[0] == 'nomask':
            masks = args
        elif not args:
            nickmask = ircdb.get_nickmask(nick)
            masks = [ ircdb._default_mask_from_nickmask(nickmask) ]
        else:
            masks = []

        if masks:
            for mask in masks:
                user.add_mask(mask)
            self.bot.ircdb.save()
            # this is a little too annoying
            #if len(masks) < 1: format = 'added masks: %s'
            #else:              format = 'added mask: %s'
            #cmd.reply(format % (', '.join(masks)))

        event = Event('int_auth_recognize', userid, nick, ['recognize'], None)
        self.bot.handle_event(self.bot.conn, event)

    _unrecognize_cperm = 'introduce'
    def unrecognize(self, cmd):
        """UN-recognize someone
        auth.unrecognize <nick>"""

        ircdb = self.bot.ircdb

        if cmd.args:
            nick = cmd.args
            current_user = ircdb.users.get(nick)
            if current_user is None:
                return cmd.reply("I don't see anyone with nick \"%s\"" \
                                 % nick)
            else:
                current_user.userid = None
                return cmd.reply("done")
        else:
            return cmd.reply('who shall I UN-recognize?')

    _addmask_cperm = 'introduce'
    def addmask(self, cmd):
        """add a mask to a user's profile
        auth.addmask <userid> <mask>
        """
        try:
            userid, mask = cmd.asplit()
        except:
            cmd.reply('bad args')
            return
        user = self.bot.ircdb.get_user(userid=userid)
        if not user:
            cmd.reply('no such user')
            return()
        user.add_mask(mask)
        self.bot.ircdb.save()
        event = Event('int_new_mask', userid, mask, ['addmask'], None)
        self.bot.handle_event(self.bot.conn, event)


    _delmask_cperm = 'introduce'
    def delmask(self, cmd):
        """delete mask from a user's profile
        auth.delmask <userid> <mask>
        mask can either be the mask itself, or the mask index (number)
        """
        try:
            userid, mask = cmd.asplit()
        except:
            cmd.reply('bad args')
            return
        user = self.bot.ircdb.get_user(userid=userid)
        if not user:
            cmd.reply('no such user')
            return()
        try: m = int(mask)
        except ValueError: m = mask
        user.remove_mask(m)
        self.bot.ircdb.save()

    _give_cperm = 1   # handled internally
    def give(self, cmd):
        """grant a user permissions
        auth.give <userid> <perm> [<more perms>]
        """
        args = cmd.asplit()
        target_userid = args.pop(0)
        target_user = self.bot.ircdb.get_user(userid=target_userid)

        calling_user = self.bot.ircdb.get_user(cmd.nick)
        if calling_user:
            com_perms = calling_user.get_perms()
        else:
            cmd.reply("I don't know you")
            return

        if not target_user:
            if target_userid in ['default', 'unknown']:
                target_user = 'SPECIAL'
            else:
                cmd.reply("I don't know anyone with userid %s" % target_userid)
                return
        
        for perm in args:
            if not self.bot.permdb.can_grant_perm(perm, com_perms):
                cmd.reply("you cannot give '%s'" % perm)
                return

        if target_user == 'SPECIAL':
            newperms = self._give_special(target_userid, args)
        else:
            for perm in args:
                target_user.add_perm(perm)
            self.bot.ircdb.save()
            newperms = target_user.get_raw_perms()
        cmd.reply('%s now has: %s' % (target_userid, ' '.join(newperms)))

        event = Event('int_give_perm', target_userid, None, args, None)
        self.bot.handle_event(self.bot.conn, event)

    def _give_special(self, special_user, perms):
        if special_user == 'unknown':
            old = self.bot.permdb.unknown_perms
            new = old + perms
            self.bot.permdb.set_unknown_perms(new)
        elif special_user == 'default':
            self.bot.permdb.default_perms.extend(perms)
            self.bot.permdb._stash() # a little hackish
            new = self.bot.permdb.default_perms
        return new
    
    _take_cperm = 1 # handled internally
    def take(self, cmd):
        """revoke a user's permissions
        auth.take <userid> <perm> [<more perms>]
        """
        args = cmd.asplit()
        target_userid = args.pop(0)
        target_user = self.bot.ircdb.get_user(userid=target_userid)

        calling_user = self.bot.ircdb.get_user(cmd.nick)
        if calling_user:
            com_perms = calling_user.get_perms()
        else:
            cmd.reply("I don't know you")
            return

        if not target_user:
            if target_userid in ['default', 'unknown']:
                target_user = 'SPECIAL'
            else:
                cmd.reply("I don't know anyone with userid %s" % target_userid)
                return
        
        for perm in args:
            if not self.bot.permdb.can_grant_perm(perm, com_perms):
                cmd.reply("you cannot take '%s'" % perm)
                return

        if target_user == 'SPECIAL':
            newperms = self._take_special(target_userid, args)
        else:
            for perm in args:
                target_user.remove_perm(perm)
                self.bot.ircdb.save()
                newperms = target_user.get_raw_perms()
        if not newperms: newperms = ['(none)']
        cmd.reply('%s now has: %s' % (target_userid, ' '.join(newperms)))
        event = Event('int_give_perm', target_userid, None, args, None)
        self.bot.handle_event(self.bot.conn, event)
        
    def _take_special(self, special_user, perms):
        if special_user == 'unknown':
            old = self.bot.permdb.unknown_perms
            for perm in perms:
                if perm in old: old.remove(perm)
            self.bot.permdb.set_unknown_perms(old)
            new = old
        elif special_user == 'default':
            new = default_perms = self.bot.permdb.default_perms
            for perm in perms:
                if perm in default_perms: default_perms.remove(perm)
            self.bot.permdb._stash() # a little hackish
        return new
        
    _grants_cperm = 1
    def grants(self, cmd):
        """list perms that a user with <perm> can grant
        grants [<perm(s)>]"""
        args = cmd.asplit()
        gr = self.bot.permdb.grant
        if not args: args = gr.keys()
        for perm in args:
            grantable = gr.get(perm)
            cmd.reply("%s -> %s" % (perm, repr(grantable)))

    _implies_cperm = 1
    def implies(self, cmd):
        """list perms that are implied by <perm>
        implies [<perm(s)>]"""
        args = cmd.asplit()
        im = self.bot.permdb.imply
        if not args: args = im.keys()
        for perm in args:
            implied = im.get(perm)
            cmd.reply("%s -> %s" % (perm, repr(implied)))

    _addgrant_cperm = 'owner'
    def addgrant(self, cmd):
        """add <perms> that can be granted by a user with <PERM>
        addgrant <PERM> <perms>"""
        args = cmd.asplit()
        perm = args.pop(0)
        gr = self.bot.permdb.grant
        plist = gr.get(perm, [])
        for p in args:
            if not p in plist: plist.append(p)
        gr[perm] = plist
        self.bot.permdb._expand()
        self.bot.permdb._stash()

    _delgrant_cperm = 'owner'
    def delgrant(self, cmd):
        """remove <perms> that can be granted by a user with <PERM>
        delgrant <PERM> <perms>"""
        args = cmd.asplit()
        perm = args.pop(0)
        gr = self.bot.permdb.grant
        plist = gr.get(perm, [])
        for p in args:
            if p in plist: plist.remove(p)
        gr[perm] = plist
        self.bot.permdb._expand()
        self.bot.permdb._stash()

    _addimply_cperm = 'owner'
    def addimply(self, cmd):
        """add <perms> that are implied by <PERM>
        addimply <PERM> <perms>"""
        args = cmd.asplit()
        perm = args.pop(0)
        im = self.bot.permdb.imply
        plist = im.get(perm, [])
        for p in args:
            if not p in plist: plist.append(p)
        im[perm] = plist
        self.bot.permdb._expand()
        self.bot.permdb._stash()

    _delimply_cperm = 'owner'
    def delimply(self, cmd):
        """remove <perms> that are implied by <PERM>
        delimply <PERM> <perms>"""
        args = cmd.asplit()
        perm = args.pop(0)
        im = self.bot.permdb.imply
        plist = im.get(perm, [])
        for p in args:
            if p in plist: plist.remove(p)
        im[perm] = plist
        self.bot.permdb._expand()
        self.bot.permdb._stash()

    #_profile_cperm = ['or', ':(channel is None) and (not sargs)', 'manager']
    _profile_cperm = 1
    def profile(self, cmd):
        """print a user's profile
        auth.profile [<userid(s)>]"""
        userlist = cmd.asplit()
        calling_user = self.bot.ircdb.get_user(cmd.nick)
        if calling_user: com_perms = calling_user.get_perms()
        else: return cmd.reply("I don't know you")
        calling_userid = calling_user.userid
        if not userlist: userlist = [calling_userid]

        if not userlist == [calling_userid]:
            context = {'bot':self.bot, 'cmd':cmd, 'channel':cmd.channel}
            uperms = calling_user.get_perms()
            cperm = cpString('manager')
            if not cperm.trycheck(uperms, context):
                return cmd.reply("you need 'manager' perms to profile other users")
            
        for userid in userlist:
            if userid in ['default', 'unknown']:
                self._profile_special(cmd, userid)
                continue
            nm = self.bot.ircdb.get_nickmask(userid=userid)
            user = self.bot.ircdb.get_user(userid=userid)
            nick = self.bot.ircdb.get_nick(userid=userid)
            if not user: cmd.reply("I don't know %s" % userid)
            else:
                cmd.reply("%s -> %s" % (userid, nm))
                perms = ' '.join(user.get_raw_perms())
                cmd.reply("  perms: %s" % perms)
                i = 0
                for mask in user.get_masks():
                    cmd.reply("   %i: %s" % (i, mask))
                    i += 1

    def _profile_special(self, cmd, special_user):
        perms = getattr(self.bot.permdb, special_user+'_perms')
        if not perms: perms = ['(none)']
        cmd.reply('%s perms: %s' % (special_user, ' '.join(perms)))

    _whois_cperm = 'manager'
    def whois(self, cmd):
        """print a user's userid by nick
        auth.whois [<nick(s)>]
        """
        userlist = cmd.asplit()
        for nick in userlist:
            self.bot.ircdb.rescan(nick)
            nm = self.bot.ircdb.get_nickmask(nick)
            userid = self.bot.ircdb.get_userid(nick)
            if not nm:       cmd.reply("there's no %s here" % nick)
            elif not userid: cmd.reply("I don't know %s" % nick)
            else:            cmd.reply("%s -> %s" % (nick, userid))

    _users_cperm = 'manager'
    def users(self, cmd):
        """list known users
        auth.users
        """
        users = self.bot.ircdb.known.keys()
        users.sort()
        cmd.reply(' '.join(users))

    _authpass_cperm = 1
    def authpass(self, cmd):
        """authenticate via password
        auth.authpass <userid> <password>
        """
        try:
            userid, password = cmd.asplit(1)
        except:
            return cmd.reply('syntax: authpass <userid> <password>')

        user = self.bot.ircdb.get_user(userid=userid)
        if user is None:
            return cmd.reply('no such user: %s' % userid)
        if user.check_password(password) == 1:
            self.bot.ircdb.users[cmd.nick].userid = userid
            cmd.reply('authentication succeeded')
            event = Event('int_auth_pass', userid, cmd.nick,
                          ['authpass'], None)
            self.bot.handle_event(self.bot.conn, event)
        else:
            cmd.reply('authentication failed')

    _setpass_cperm = 1
    def setpass(self, cmd):
        """set your password
        auth.setpass <new password>
        """
        user = self.bot.ircdb.get_user(nick=cmd.nick)
        if user is None:
            return cmd.reply("I don't recognize you")
        user.set_password(cmd.args)
        self.bot.ircdb.save()
        if cmd.args:
            cmd.reply('password set for %s' % user.userid)
        else:
            cmd.reply('password unset for %s' % user.userid)


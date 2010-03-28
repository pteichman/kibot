import fnmatch

from .irclib import is_channel

class UserPerm:
    default_channel_list = ['*']
    def __init__(self, string_perm):
        chunks = string_perm.split(':')
        self.perm = chunks.pop(0)

        if chunks:
            self.channels = chunks.pop(0).split(',')
        else:
            self.channels = self.default_channel_list

        self.misc = []
        while chunks:
            self.misc.append(chunks.pop(0).split(','))

class UPermCache:
    def __init__(self, userperms):
        self.uperms = {}
        self.upermlist = []
        for string_up in userperms:
            up = UserPerm(string_up)
            self.uperms[up.perm] = up
            self.upermlist.append(up.perm)

    def __getitem__(self, key):
        if type(key) == type(''): return self.uperms[key]
        elif type(key) == type(0): return self.uperms[self.upermlist[key]]
        else: raise KeyError(key)

    def __contains__(self, key):
        return self.uperms.has_key(key)

    def keys(self):
        return list(self.upermlist)

    def get(self, key, notfound=None):
        try: return self.uperms[key]
        except KeyError: return notfound

class PermError(Exception):
    pass

class CPerm:
    def check_globlist(self, globlist, test):
        gl = list(globlist)
        gl.reverse()
        for glob in gl:
            if glob[0] == '!':
                return_on_match = 0
                glob = glob[1:]
            else:
                return_on_match = 1

            if fnmatch.fnmatchcase(test, glob):
                return return_on_match
        return 0

    def trycheck(self, userperms, context):
        try:
            ret = self.check(userperms, context)
        except PermError:
            ret = 0
        return ret

class cpNoPerm(CPerm):
    def check(self, userperms, context):
        return 1
    def format(self, depth=0):
        return '(none)'

class cpForbidden(CPerm):
    def check(self, userperms, context):
        raise PermError('command is forbidden')
    def format(self, depth=0):
        return '(forbidden)'

class cpOr(CPerm):
    _format_join_pattern = ' OR '

    def __init__(self, *args):
        self.sub_perms = args

    def check(self, userperms, context):
        for sub_perm in self.sub_perms:
            try:
                if sub_perm.check(userperms, context): return 1
            except PermError:
                pass
        return 0

    def format(self, depth=0):
        li = []
        for sp in self.sub_perms:
            li.append(sp.format(depth+1))
        s = self._format_join_pattern.join(li)
        if depth: return '(%s)' % s
        else:     return s

class cpAnd(cpOr):
    _format_join_pattern = ' AND '
    def check(self, userperms, context):
        for sub_perm in self.sub_perms:
            if not sub_perm.check(userperms, context): return 0
        return 1

class cpString(CPerm):
    def __init__(self, stringperm):
        try: stringperm, cond = stringperm.split(':', 1)
        except ValueError: cond = ''

        self.sperm = stringperm
        self.condition = cond

    def format(self, depth=0):
        if not self.condition: return repr(self.sperm)
        else: return repr("%s:%s" % (self.sperm, self.condition))

    def check(self, userperms, context):
        if self.sperm:
            best_match = self.best_perm_match(userperms, context)
            if best_match is None:
                raise PermError("you do not have '%s'" % self.sperm)
            if not self.check_channel(userperms, context, best_match):
                raise PermError("you do not have '%s' there" % self.sperm)
            if not self.check_target(userperms, context, best_match):
                raise PermError("you do not have '%s' for that target" % \
                                self.sperm)
        else:
            best_match = None

        if self.condition:
            ret = self.check_condition(userperms, context, best_match)
            if not ret:
                raise PermError("condition failed: %s" % repr(self.condition))

        return 1

    def best_perm_match(self, userperms, context):
        if self.sperm in userperms: return self.sperm
        permdb = context['bot'].permdb
        winner = None
        winner_depth = -1
        for name in userperms.keys():
            depth = permdb.imply_depth(name, self.sperm)
            if (not depth is None) and \
               (winner is None or depth <= winner_depth):
                winner = name
                winner_depth = depth
        return winner

    def check_channel(self, userperms, context, best_match=None):
        if context.has_key('channel'): channel = context['channel']
        elif context.has_key('cmd'): channel = context['cmd'].channel
        else: channel = None
        if channel == 'NONE': return 1
        if channel is None: channel = 'PRIV'
        uperm = userperms[best_match]
        return self.check_globlist(uperm.channels, channel)

    def check_target(self, userperms, context, best_match=None):
        return 1

    def check_condition(self, userperms, context, best_match=None):
        tmp = {}
        tmp['userid']  = context.get('userid')
        if context.has_key('cmd'):
            cmd = context['cmd']
            tmp['channel'] = cmd.channel
            tmp['nick']    = cmd.nick
            tmp['sargs']   = cmd.args
            tmp['args']    = cmd.asplit()
        else:
            tmp['channel'] = context.get('channel')
            tmp['nick']    = context.get('nick')
            tmp['sargs']   = context.get('sargs', '')
            tmp['args']    = context.get('args', [])

        if best_match:
            uperm = userperms[best_match]
            tmp['uperm']    = uperm.perm
            tmp['channels'] = uperm.channels
            tmp['misc']     = uperm.misc

        try: return eval(self.condition, tmp)
        except: return 0

class cpTargetChannel(cpString):
    def check_target(self, userperms, context, best_match):
        try: target = context['target']
        except KeyError:
            if context.has_key('cmd'):
                args = context['cmd'].asplit()
                channel = context['cmd'].channel
                if args and is_channel(args[0]): target = args[0]
                else: target = channel
            else:
                target = None
        if not target: return 0
        if target == 'NONE': return 1
        uperm = userperms[best_match]
        try: checklist = uperm.misc[0]
        except IndexError: checklist = uperm.channels
        return self.check_globlist(checklist, target)

    def format(self, depth=0):
        return '(%s for target channel)' % cpString.format(self)

def translate_cperm(cperm_obj):
    if isinstance(cperm_obj, CPerm):
        return cperm_obj

    t = type(cperm_obj)
    if t == type(''):
        return cpString(cperm_obj)
    elif t == type(0):
        if cperm_obj: return cpNoPerm()
        else: return cpForbidden()
    elif t == type(()):
        contents = [ translate_cperm(obj) for obj in cperm_obj ]
        return cpOr(*contents)
    elif t == type([]):
        if cperm_obj[0] in ['or', 'and']:
            op = cperm_obj[0]
            contents = cperm_obj[1:]
        else:
            op = 'and'
            contents = cperm_obj
        contents = [ translate_cperm(obj) for obj in contents ]
        if op == 'or': return cpOr(*contents)
        else:          return cpAnd(*contents)
    elif cperm_obj is None:
        return cpForbidden()
    else:
        return cpForbidden()


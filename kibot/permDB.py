import os.path
from . import BaseModule
from .PermObjects import UPermCache
class CommandNotFoundError(Exception): pass

default_imply = {
    'owner': ['manager'],
    'manager': ['op', 'kick', 'introduce', 'load']
    }
default_grant = {
    'owner': ['owner', 'manager', 'load'],
    'manager': ['op', 'kick', 'introduce', 'ignore']
    }

class permDB(BaseModule.BaseModule):
    def __init__(self, bot):
        self.bot = bot
        self._load()

    _stash_attrs = ['imply', 'grant', 'aliases',
                    'unknown_perms', 'default_perms']
    _stash_format = 'repr'
    def _load(self):
        self.imply = default_imply
        self.grant = default_grant
        self.aliases = {}
        self.unknown_perms = []
        self.default_perms = []
        self._unstash()

        self._expand()

        ## get override perms
        override_file = self.bot.op.files.override_file
        tmpspace = {}
        if os.path.exists(override_file):
            execfile(override_file, tmpspace)
            self.override_perms = tmpspace['override']
        else:
            self.override_perms = {}

    def _expand(self):
        self._imply = self._expand_tree(self.imply)
        self._grant = self._expand_tree(self.grant)

    def _expand_tree(self, tree):
        newtree = {}
        for p in tree.keys():
            newtree[p] = self._recur_get_perm(p, tree)
        return newtree

    def _recur_get_perm(self, perm, tree, pmap=None, depth=1):
        if pmap is None: pmap = {}
        try: l = tree[perm]
        except KeyError, msg: return pmap
        for p in l:
            if not p in pmap: pmap[p] = depth
            if p == perm: continue
            self._recur_get_perm(p, tree, pmap, depth+1)
        return pmap

    ##############################################################
    def expand_alias(self, command):
        try: return self.aliases[command]
        except KeyError, msg: return command

    def set_unknown_perms(self, newperms):
        self._cached_unknown_perms = None
        self.unknown_perms = newperms
        self._stash()

    def get_unknown_perms(self):
        up = getattr(self, '_cached_unknown_perms', None)
        if up is None:
            up = UPermCache(self.unknown_perms)
            self._cached_unknown_perms = up
        return up

    def can_execute(self, command_name, obj, cperm, cmd):
        user = self.bot.ircdb.get_user(nickmask=cmd.nickmask)
        if user: uperms = user.get_perms()
        else:    uperms = self.get_unknown_perms()
        if 'god' in uperms.keys(): return 1

        override = self.override_perms.get(command_name, None)
        if override: cperm = override

        if cperm is None: return 0

        context = {'bot':  self.bot,
                   'cmd':  cmd,
                   'user': user,
                   'userid': (user and user.userid)}

        return cperm.check(uperms, context)

    def can_grant_perm(self, perm, userperms):
        if 'god' in userperms: return 1
        for up in userperms:
            if perm in self.grants(up.perm): return 1
        return 0

    def implies(self, perm):
        return self._imply.get(perm, {}).keys()

    def grants(self, perm):
        return self._grant.get(perm, {}).keys()

    def imply_depth(self, base_perm, implied_perm):
        try: return self._imply[base_perm][implied_perm]
        except KeyError, e: return None

    def grant_depth(self, base_perm, granted_perm):
        try: return self._grant[base_perm][granted_perm]
        except KeyError, e: return None

    def implied_by(self, perm):
        imp = []
        for p, l in self._imply.items():
            if perm in l: imp.append(p)
        return imp

    def granted_by(self, perm):
        gra = []
        for p, l in self._grant.items():
            if perm in l: gra.append(p)
        return gra

if __name__ == '__main__':
    pass

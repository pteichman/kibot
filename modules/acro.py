import urllib2
import re
import time

import kibot.BaseModule

class acro(kibot.BaseModule.BaseModule):
    """look up acronyms"""
    _stash_format = 'repr'
    _stash_attrs = ['cache', 'local', 'failcache']
    def __init__(self, bot):
        self.bot = bot
        self.expire_time = 3600 * 24 * 7 # a week
        self.cache = {}
        self.local = {}
        self.failcache = {}
        self._unstash()
        
    def _unload(self):
        self._stash()

    _cperm = 1
    def __call__(self, cmd):
        """look up an acronym
        acro <acronym>"""
        a = self._clean_acronym(cmd.args)
        if self.local.has_key(a):
            cmd.reply('%s (local)' % self.local[a])
        elif self.cache.has_key(a):
            cmd.reply('%s (cached)' % self.cache[a])
        elif self.failcache.has_key(a) and \
             self.failcache[a] > (time.time() - self.expire_time):
            cmd.reply('Not found (cached).  Set it with ' + \
                      '"acro.set %s [definition]"' %a)
        else:
            lookup = self._web_lookup(a)
            if not lookup:
                self.failcache[a] = time.time()
                cmd.reply('Not found. Set it with ' + \
                          '"acro.set %s [definition]"' % a)
            else:
                self.cache[a] = lookup
                cmd.reply('%s' % lookup)
        
    _set_cperm = 1
    def set(self, cmd):
        """set (or forget) an acronym definition
        set <acronym> [definition]"""
        try: acro, definition = cmd.args.split(' ', 1)
        except: acro, definition = cmd.args, None
        a = self._clean_acronym(acro)
        if not a:
            cmd.reply('huh?')
        elif not definition:
            if self.local.has_key(a): del self.local[a]
            if self.cache.has_key(a): del self.cache[a]
            if self.failcache.has_key(a): del self.failcache[a]
            cmd.reply('forgetting %s' % a)
            self._stash()
        else:
            self.local[a] = definition
            if self.failcache.has_key(a): del self.failcache[a]
            self._stash()
            cmd.reply('done')

    ###################################################################
    # support functions
    def _web_lookup(self, acronym):
        #url = 'http://www.ucc.ie/cgi-bin/acronym?%s' % acronym)
        url = 'http://www.chemie.fu-berlin.de/cgi-bin/acronym?%s' % acronym
        try:
            fo = urllib2.urlopen(url)
            data = fo.read()
            fo.close()
        except Exception, e:
            self.bot.log(2, 'ACRO: lookup raised exception: %s' % str(e))

        for line in data.split('\n'):
            if line.startswith(acronym):
                a, result = line.split('-', 1)
                return result.strip()
        return None


    def _clean_acronym(self, acronym):
        acronym = acronym.upper()
        acronym = re.sub(r'[^A-Z0-9]', '', acronym)
        return acronym

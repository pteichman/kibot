#!/usr/bin/python2
"""Use of this module requires a google key, which you can get by
going to http://www.google.com/apis/.  Once you have your key, put
it in your config file like this:

[mod_google]
license_key = TL5EA/9qLp9NotARealKey0AMackfxeM
"""

import re
import sys
import time

import pygoogle
import SOAP

import kibot.BaseModule

class google(kibot.BaseModule.BaseModule):
    """do google searching"""
    _stash_format = 'repr'
    _stash_attrs = ['counter', 'since', 'last_hit']
    def __init__(self, bot):
        self.bot = bot
        self._unstash(None)
        try: key = self.bot.op.mod_google.license_key
        except AttributeError: key = ''
        if key:
            self.bot.log(4, 'GOOGLE: using key: %s' % key)
            pygoogle.setLicense(key)

    def _unload(self):
        self._stash()

    def _count(self):
        now = list(time.localtime())
        now[3] = 0 # set hour to 0
        now[4] = 0 # set minute to 0
        now[5] = 0 # set seconds to 0
        this_morning = time.mktime(now)
        if not self.last_hit:
            self.counter = 0
            self.since = time.time()
        elif self.last_hit < this_morning:
            self.counter = 0
            self.since = this_morning
        self.counter += 1
        self.last_hit = time.time()

        self._stash()
        
    _cperm = 1
    def __call__(self, cmd):
        """(shortcut for search)"""
        args = cmd.asplit()
        try:
            num = int(args[0])
            args.pop(0)
            if num > 5: num = 5
            if num < 1: num = 1
        except ValueError:
            num = 1
        self._count()
        try: data = pygoogle.doGoogleSearch(' '.join(args))
        except Exception, e:
            self._google_error(cmd, e)
            raise
        
        if not data.results:
            cmd.reply('(no matches)')
        for r in data.results[0:num]:
            title = re.sub('</?b>', '', r.title)
            msg = '[%s] %s' % (title, r.URL)
            cmd.reply(msg)

    _count_cperm = 1
    def count(self, cmd):
        if self.counter is None:
            cmd.reply('counter not initialized... no count information')
        else:
            if self.counter == 1: s = ''
            else: s = 's'
            cmd.reply('%i hit%s since %s' % (self.counter, s,
                                            time.ctime(self.since)))

    _search_cperm = 1
    def search(self, cmd):
        """do a google search
        search [num_results] search term(s)"""
        self(cmd)
        
    _spell_cperm = 1
    def spell(self, cmd):
        """get a spelling suggestion
        spell <word>"""
        self._count()
        try: sug = pygoogle.doSpellingSuggestion(cmd.args)
        except Exception, e:
            self._google_error(cmd, e)
            raise

        if sug:
            cmd.reply(sug)
        else:
            cmd.reply("%s (no suggestion)" % cmd.args)

    def _google_error(self, cmd, e):
        self.bot.log(2, 'GOOGLE ERROR: %s' % str(e))
        fs = 'Exception from service object: Invalid authorization key:'
        if isinstance(e, pygoogle.NoLicenseKey):
            cmd.reply('You need a license key.  See the google module docs')
        elif isinstance(e, SOAP.faultType) and e.faultstring.startswith(fs):
            cmd.reply('Invalid license key.')
            
        

import urllib2
import re
import time

import kibot.BaseModule
from kibot.irclib import is_channel
from kibot.m_irclib import Timer

class slashdot(kibot.BaseModule.BaseModule):
    """get notified about slashdot stories"""
    _stash_format = 'repr'
    _stash_attrs = ['notify_list']
    def __init__(self, bot):
        self.bot = bot
        self.notify_list = []
        self._unstash()
        self.articles = []
        self.timer = Timer(0, self._timer_func, repeat=60 * 60)
        
        self.bot.set_timer(self.timer)

    def _unload(self):
        self._stash()
        self.bot.tmp['slashdot.notify_list'] = self.notify_list
        self.bot.del_timer(self.timer)

    _list_cperm = 'manager'
    def list(self, cmd):
        """list recipients of notification"""
        if not self.notify_list: cmd.reply('(empty list)')
        else:  cmd.reply(' '.join(self.notify_list))

    _interval_cperm = 'manager'
    def interval(self, cmd):
        """set or get interval to poll slashdot
        interval [seconds]"""
        if cmd.args:
            try:    N = int(cmd.args)
            except: N = None
            if N:
                self.bot.del_timer(self.timer)
                self.timer = Timer(0, self._timer_func, repeat=N)
                self.bot.set_timer(self.timer)
        cmd.reply('Check interval is %s seconds' % self.timer.repeat)


    _cperm = ['or', 'op', ':channel is None']
    def __call__(self, cmd):
        """shortcut for slashdot.last"""
        self.last(cmd)

    _last_cperm = ['or', 'op', ':channel is None']
    def last(self, cmd):
        """print the last N slashdot titles (default N=1)
        last [N]
        """
        if cmd.args:
            try: N = int(cmd.args)
            except:
                cmd.reply("how 'bout an integer?")
                return
        else:
            N = 1

        if (time.time() - self.last_fetch) > (10 * 60):
            # if it's been more than 10 minutes, just do the timer
            # function now
            self._timer_func()

        if N < 0: N = 0
        if N > len(self.articles): N = len(self.articles)
        li = self.articles[-N:]
        for art in li:
            cmd.reply('Slashdot: %s' % art)

    _notify_cperm = ['or', 'op', ':channel is None']
    def notify(self, cmd):
        """request notification of new articles (to channel or privately)
        notify
        """
        if cmd.args:
            cmd.reply('no args, man')
            return
        if cmd.channel: notify = cmd.channel
        else: notify = cmd.nick
        if not notify in self.notify_list:
            self.notify_list.append(notify)
            self._stash()
            cmd.reply('OK, you asked for it!')
        else:
            cmd.reply("Can't get enough, eh?")

    _stop_cperm = ['or', 'op', ':channel is None']
    def stop(self, cmd):
        """stop notification of new entries
        stop
        """
        if cmd.args:
            cmd.reply('no args, man')
            return
        if cmd.channel: notify = cmd.channel
        else: notify = cmd.nick
        if notify in self.notify_list:
            self.notify_list.remove(notify)
            self._stash()
            cmd.reply("I'm surprised you lasted this long")
        else:
            cmd.reply("Relax, you're not on the list")

    def _get_new_articles(self):
        try:
            fo = urllib2.urlopen('http://slashdot.org/slashdot.xml')
            lines = fo.readlines()
            fo.close()
        except Exception, msg:
            self.bot.log(2, 'Slashdot read: %s' % str(msg))
            return 1
        current_articles = self._parse_lines(lines)
        current_articles.reverse()
        new = []
        for art in current_articles:
            if not art in self.articles:
                new.append(art)
        self.articles.extend(new)
        self.last_fetch = time.time()
        return new

    def _timer_func(self):
        if self.articles: notify = 1
        else:             notify = 0 # have mercy on startup :)

        new = self._get_new_articles()
        if notify:
            for target in self.notify_list:
                self._notify(target, new)
        return 1

    _infore = re.compile(r'<(.+)>(.*)</\1>$')
    def _parse_lines(self, lines):
        current_articles = []
        obj = None
        for line in lines:
            line = line.strip()
            #self.bot.log(10, line)
            m = self._infore.match(line)
            if line == '<story>':
                obj = SlashdotStory()
            elif line == '</story>':
                current_articles.append(obj)
                obj = None
            elif m and obj:
                k, v = m.groups()
                setattr(obj, k, v)
        return current_articles

    def _notify(self, target, new):
        if is_channel(target):
            if not target in self.bot.ircdb.channels.keys(): return
        else:
            if not target in self.bot.ircdb.users.keys(): return
        for art in new:
            self.bot.conn.privmsg(target, 'Slashdot: %s' % art)

class SlashdotStory:
    def __eq__(self, other):
        return self.title == other.title
    def __str__(self):
        return "%s %s" % (self.title, self.url)

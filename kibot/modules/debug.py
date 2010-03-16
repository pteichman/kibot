import time
import kibot.BaseModule
from kibot.m_irclib import Timer
from kibot.Settings import Setting

"""
settings:
  notify:
    space-delimited list of nicks/channels to notify when memory
    usage crosses threshold
  threshold: 
    memory usage in kB at which notification/warning should be sent.
"""

class debug(kibot.BaseModule.BaseModule):
    """This module provides various debugging features
    """

    _settings = [
        Setting('notify', '', 'nick(s)/channel(s) to notify of events'),
        Setting('threshold', 10*1024, 'memory warning threshold (in kB)',
                conv_func=int),
        ]
    _stash_attrs = ['notify', 'threshold']
    def __init__(self, bot):
        kibot.BaseModule.BaseModule.__init__(self, bot)
        self.last_notify = 0
        self.notify_every = 3600
        self.timer = Timer(0, self._timer_func, repeat=30) # 30 seconds
        self.bot.set_timer(self.timer)

    def _unload(self):
        self._stash()
        self.bot.del_timer(self.timer)
        
    _memusage_cperm = 1
    def memusage(self, cmd):
        cmd.reply('total: %i kB, rss: %i kB' % self._get_memusage())

    def _timer_func(self):
        total, res = self._get_memusage()
        self.bot.log(4, 'MEMWATCH: %s, %s, %s' % (total, res, time.asctime()))
        
        if total >= int(self.threshold) and \
               (time.time() - self.last_notify > self.notify_every):
            self.last_notify = time.time()
            msg = 'WARNING: %s memory usage (%s kB) exceeds threshold (%s kB)' \
                  % (self.bot.nick, total, self.threshold)
            for n in self.notify.split():
                self.bot.conn.privmsg(n, msg)
        return 1
    
    def _get_memusage(self):
        proc = open('/proc/self/stat')
        procs = proc.read()
        proc.close()
        stats = procs.split()
        total = int(stats[22]) / 1024
        rss   = int(stats[23]) * 4 # 4 kB pages
        return total, rss

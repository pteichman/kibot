#!/usr/bin/python2
import re
import random
import kibot.BaseModule
import time

from kibot.PermObjects import cpTargetChannel
from kibot.m_irclib import is_channel, nm_to_n, Timer
class rand(kibot.BaseModule.BaseModule):
    """spew random (and occasionally humorous) stuff"""
    _stash_format = 'repr'
    _stash_attrs = ['quotes', 'rtopic_list']
    _commands = """quote addquote delquote quotestats""".split()
    def __init__(self, bot):
        self.bot = bot
        self.quotes = {}
        self.rtopic_list = {}
        self.rtopic_timers = {}
        self._unstash()
        if 1: ###### added for version 0.0.6 (29 Mar 2003) - remove some day
            self._convert()
            self._stash()
        self._init_quotestats()
        self._set_handlers()
        self._update_all_channels()

        
    def _convert(self):
        ##### added for version 0.0.6 (29 Mar 2003) - remove some day
        newquotes = {}
        for nick, quotelist in self.quotes.items():
            newlist = []
            for q in quotelist:
                if type(q) == type(''):
                    newlist.append( {'quote':q} )
                else:
                    newlist.append( q )
            newquotes[nick] = newlist
        self.quotes = newquotes
        
    def _unload(self):
        self._stash()
        self._del_handlers()
        for t in self.rtopic_timers.values(): self.bot.del_timer(t)
        
    _quote_cperm = 1
    def quote(self, cmd):
        """get or set a quote
        quote [nick [new quote]]
        if text appears after "nick", then it will be added as a new quote"""
        args = cmd.shsplit(1)
        syntax = 'quote [nick [new quote]]'
        if   len(args) == 0: self._get_quote(cmd, None)
        elif len(args) == 1: self._get_quote(cmd, cmd.args)
        else: # adding a new quote
            self._add(cmd, syntax)

    _addquote_cperm = 1
    def addquote(self, cmd):
        """add a new quote for <nick>
        addquote <nick> <quote>
        ex: addquote joe I really like it here
        ex: addquote <jeff> yeah, me too
        ex: addquote * jack wishes he were elsewhere"""
        args = cmd.shsplit(1)
        syntax = 'addquote <nick> <quote>'
        if not len(args) == 2:
            return cmd.reply('syntax: %s' % syntax)
        else:
            self._add(cmd, syntax)
            
    def _add(self, cmd, syntax):
        nick, quote = self._split_new_quote(cmd)
        if nick is None:
            return cmd.reply('syntax: %s' % syntax)
        quote = self._strip_quote(quote)
        self._add_quote(cmd, nick, quote)
        cmd.reply('done')

    _delquote_cperm = 1
    def delquote(self, cmd):
        """remove a quote
        delquote <nick> <quote>"""
        args = cmd.shsplit(1)
        if not len(args) == 2:
            return cmd.reply('syntax: delquote <nick> <quote>')
        else:
            nick, quote = self._split_new_quote(cmd)
            quote = self._strip_quote(quote)

        if not self.quotes.has_key(nick):
            return cmd.reply("I don't have any quotes by %s" % nick)
        else:
            found = 0
            for q in self.quotes[nick]:
                if q['quote'] == quote:
                    found = 1
                    break
            if not found:
                return cmd.reply("I don't have that quote")

        self.quotes[nick].remove(q)
        self._quotestats['nicks'][nick] -= 1
        self._quotestats['total'] -= 1
        if self._quotestats['nicks'][nick] == 0:
            del self._quotestats['nicks'][nick]
            del self.quotes[nick]
            self._quotestats['numnicks'] -= 1
        self._stash()
        cmd.reply('done')

    _quotestats_cperm = 1
    def quotestats(self, cmd):
        """get stats about available quotes
        quotestats [nick]"""
        nickmap = self._quotestats['nicks']
        if cmd.args.lower() == 'total':
            cmd.reply('TOTAL: %i' % self._quotestats['total'])

        elif cmd.args:
            nicks = cmd.shsplit()
            qs_list = []
            for nick in nicks:
                try: qs_list.append( (nick, nickmap[nick]) )
                except KeyError, e:
                    return cmd.reply("I don't have any quotes from %s" % nick)
            qs_list.sort()

        else:
            qs_list = nickmap.items()
            qs_list.sort()
            qs_list.insert(0, ('TOTAL', self._quotestats['total']) )
        chunks = [ '%s: %i' % (nick, num) for nick, num in qs_list ]
        s = ', '.join(chunks)
        cmd.reply(s)

    def _get_quote(self, cmd, nick=None):
        if nick:
            if not self.quotes.has_key(nick):
                cmd.reply("I don't have any quotes by %s" % nick)
                return

            q = random.choice(self.quotes[nick])
            cmd.reply(self._format_quote(q, nick))
                      
        else:
            try:
                rnum = random.randrange(self._quotestats['total'])
            except ValueError:
                cmd.reply("I have no quotes to give")
                return 

            for nick, numquotes in self._quotestats['nicks'].items():
                if rnum < numquotes:
                    q = self.quotes[nick][rnum]
                    cmd.reply(self._format_quote(q, nick))
                    return
                else:
                    rnum -= numquotes

    def _format_quote(self, quote_dict, nick):
        fquote = '"%s" --%s' % (quote_dict['quote'], nick)
        date = quote_dict.get('date')
        if not date is None:
            #time_format = '%B %d, %Y'
            #time_format = '%x'
            time_format = '%d-%b-%y'
            time_tuple = time.localtime(date)
            ftime = time.strftime(time_format, time_tuple).lower()
            fquote = '%s, %s' % (fquote, ftime)
        return fquote
    
    def _split_new_quote(self, cmd):
        """takes the cmd object and returns (nick, quote).  This is where
        convenience formats like '* michael smirks' are dealt with."""

        if cmd.args.startswith('* '):
            args = cmd.shsplit(2)
            if len(args) < 3: return None, None
            nick = args[1]
            quote = cmd.args
        else:
            args = cmd.shsplit(1)
            if len(args) < 2: return None, None
            nick, quote = args
            if nick[0] == '<' and nick[-1] == '>': nick = nick[1:-1]
        return nick, quote
    
    def _add_quote(self, cmd, nick, quote):
        """add the given quote to the quote database"""
        if not self.quotes.has_key(nick):
            self.quotes[nick] = []
            self._quotestats['numnicks'] += 1
            self._quotestats['nicks'][nick] = 0
        q = {'quote':quote, 'date': time.time()}
        self.quotes[nick].append(q)
        self._quotestats['nicks'][nick] += 1
        self._quotestats['total'] += 1
        self._stash()

    _strip_re = re.compile(r'^([\'\"])(.*)\1$')
    def _strip_quote(self, quote):
        quote = quote.strip()
        # if it's surrounded by quotes (of some type) AND that type doesn't
        # appear internally, strip the outer quotes:
        # 'hello world' -> hello world
        # 'what do you mean by "big"?' -> what do you mean by "big"?
        # "damn," she said, "I'm on fire" -> "damn," she said, "I'm on fire"
        m = self._strip_re.match(quote)
        if m and not re.search(m.group(1), m.group(2)): quote = m.group(2)
        return quote.strip()

    def _init_quotestats(self):
        q = self.quotes
        qs = self._quotestats = {}
        qs['total'] = 0
        qs['numnicks'] = 0
        qs['nicks'] = {}
        for n, v in q.items():
            qs['numnicks'] += 1
            numquotes = len(v)
            qs['total'] += numquotes
            qs['nicks'][n] = numquotes
            

    _rtopic_cperm = cpTargetChannel('op')
    def rtopic(self, cmd):
        '''put a random quote in the topic periodically (if not locked)
        rtopic [channel] <numhours> ["<format>"]
        ex: rtopic #foo 4 "The best of #foo: %s"
        Set <numhours> to 0 to stop.
        '''
        syntax = 'rtopic [channel] <numhours> ["<format>"]'
        args = cmd.shsplit()
        channel = cmd.channel    # default channel
        if args and is_channel(args[0]): channel = args.pop(0)
        if not channel: return cmd.reply("What channel?")

        if args:
            try: period = float(args.pop(0))
            except: return cmd.reply(syntax)
        else:
            cmap = self.rtopic_list.get(channel)
            if cmap is None: return cmd.reply('not setting %s topic' % channel)
            return cmd.reply('setting %s topic every %f hours with format %s' % \
                             (channel, cmap['period'], repr(cmap['format'])))
        if period == 0.0 and self.rtopic_list.has_key(channel):
            if self.rtopic_timers.has_key(channel):
                self.bot.del_timer(self.rtopic_timers[channel])
                del self.rtopic_timers[channel]
            del self.rtopic_list[channel]
            self._stash()
            return cmd.reply('disabling random topics on %s' % channel)
        
        if args: format = args.pop(0)
        else: format = "The best of %s: %%s" % channel

        self.rtopic_list[channel] = {'period': period, 'format': format}
        self._stash()
        self._update_channel(channel)
        cmd.reply('done')
        
    def _update_all_channels(self):
        for channel in self.rtopic_list.keys():
            self._update_channel(channel)

    def _update_channel(self, channel):
        self.bot.log(9, 'RAND: channel update on %s' % channel)
        if self.rtopic_timers.has_key(channel):
            self.bot.del_timer(self.rtopic_timers[channel])
            del self.rtopic_timers[channel]
        
        cmap = self.rtopic_list.get(channel)
        ch   = self.bot.ircdb.channels.get(channel)
        if cmap is None or ch is None:
            self.bot.log(9, 'RAND: not on %s, or not setting topic' % channel)
            return
        if ch.has_topic_lock():
            self.bot.log(9, 'RAND: %s has topic lock' % channel)
            return

        period = cmap['period']
        format = cmap['format']
        ttime = ch.topic_time()
        if ttime is None:
            self.bot.log(9, 'RAND: %s has unknown topic time' % channel)
            return
        if (time.time() - ttime < 3600 * period):
            # this channel if fair game to set the topic for, but
            # it's too early: set a timer to try again later
            newtime = ttime + (period * 3600) + 5
            newtimer = Timer(newtime, self._update_channel,
                             (channel, ), fromnow=0)
            self.rtopic_timers[channel] = newtimer
            self.bot.set_timer(newtimer)
            self.bot.log(9, 'RAND: setting new timer for %s' % channel)
            return

        # set it!
        try: rnum = random.randrange(self._quotestats['total'])
        except ValueError: quote = '[no quotes available]'
        else:
            for nick, numquotes in self._quotestats['nicks'].items():
                if rnum < numquotes:
                    q = self.quotes[nick][rnum]
                    quote = self._format_quote(q, nick)
                    break
                else:
                    rnum -= numquotes
        self.bot.conn.topic(channel, format % quote)

    def _on_mode(self, c, e):
        # this will catch both mode changes and also when the bot
        # joins a channel.  We don't use _on_join because at the time
        # that handler is called, we haven't learned about the channel
        # mode yet, and we wouldn't want to change a topic if the
        # topic is locked.
        channel = e.target
        if self.rtopic_list.has_key(channel):
            self._update_channel(channel)

    def _on_channelmodeis(self, c, e):
        channel = e.args[0]
        if self.rtopic_list.has_key(channel):
            self._update_channel(channel)
        
    def _on_topicinfo(self, c, e):
        channel = e.args[0]
        if self.rtopic_list.has_key(channel):
            self._update_channel(channel)

    def _on_topic(self, c, e):
        channel = e.target
        if self.rtopic_list.has_key(channel):
            self._update_channel(channel)

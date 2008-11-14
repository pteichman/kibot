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
    _commands = """zippy pokey quote addquote delquote quotestats""".split()
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

    _zippy_cperm = 1
    def zippy(self, cmd):
        """quotes from \"zippy the pinhead\""""
        cmd.reply(random.choice(zippy_data))
        
    _pokey_cperm = 1
    def pokey(self, cmd):
        """pokey is just weird"""
        cmd.reply(random.choice(pokey_data))
        
zippy_data = ['A dwarf is passing out somewhere in Detroit!',
 "Actually, what I'd like is a little toy spaceship!!",
 'All of life is a blur of Republicans and meat!',
 'Am I accompanied by a PARENT or GUARDIAN?',
 'Am I elected yet?',
 'Am I in GRADUATE SCHOOL yet?',
 'Am I SHOPLIFTING?',
 'An air of FRENCH FRIES permeates my nostrils!!',
 'An Italian is COMBING his hair in suburban DES MOINES!',
 'And furthermore, my bowling average is unimpeachable!!!',
 'Are the STEWED PRUNES still in the HAIR DRYER?',
 'Are we live or on tape?',
 'Are we on STRIKE yet?',
 'Are we THERE yet?',
 'Are we THERE yet?  My MIND is a SUBMARINE!!',
 'Are you mentally here at Pizza Hut??',
 'As President I have to go vacuum my coin collection!',
 'BARBARA STANWYCK makes me nervous!!',
 'BELA LUGOSI is my co-pilot ...',
 '... bleakness ... desolation ... plastic forks ...',
 'Bo Derek ruined my life!',
 "Boy, am I glad it's only 1971...",
 'But they went to MARS around 1953!!',
 'Can I have an IMPULSE ITEM instead?',
 'Can you MAIL a BEAN CAKE?',
 'Civilization is fun!  Anyway, it keeps me busy!!',
 'Could I have a drug overdose?',
 'Did I do an INCORRECT THING??',
 'Did I say I was a sardine?  Or a bus???',
 'Did I SELL OUT yet??',
 'Did YOU find a DIGITAL WATCH in YOUR box of VELVEETA?',
 'Did you move a lot of KOREAN STEAK KNIVES this trip, Dingy?',
 'DIDI ... is that a MARTIAN name, or, are we in ISRAEL?',
 "Didn't I buy a 1951 Packard from you last March in Cairo?",
 'Do I have a lifestyle yet?',
 'Do you guys know we just passed thru a BLACK HOLE in space?',
 'Do you like "TENDER VITTLES"?',
 'does your DRESSING ROOM have enough ASPARAGUS?',
 "Don't hit me!!  I'm in the Twilight Zone!!!",
 "Don't SANFORIZE me!!",
 'Edwin Meese made me wear CORDOVANS!!',
 'Eisenhower!!  Your mimeograph machine upsets my stomach!!',
 'Either CONFESS now or we go to "PEOPLE\'S COURT"!!',
 'Everybody gets free BORSCHT!',
 'Everywhere I look I see NEGATIVITY and ASPHALT ...',
 'FEELINGS are cascading over me!!!',
 'for ARTIFICIAL FLAVORING!!',
 "FUN is never having to say you're SUSHI!!",
 'Gibble, Gobble, we ACCEPT YOU ...',
 'Go on, EMOTE!  I was RAISED on thought balloons!!',
 'HAIR TONICS, please!!',
 'Half a mind is a terrible thing to waste!',
 'Has everybody got HALVAH spread all over their ANKLES??',
 '... he dominates the DECADENT SUBWAY SCENE.',
 "HELLO, everybody, I'm a HUMAN!!",
 "Hello, GORRY-O!!  I'm a GENIUS from HARVARD!!",
 'Here I am in 53 B.C. and all I want is a dill pickle!!',
 'Here we are in America ... when do we collect unemployment?',
 'Hold the MAYO & pass the COSMIC AWARENESS ...',
 'HOORAY, Ronald!!  Now YOU can marry LINDA RONSTADT too!!',
 'How do I get HOME?',
 "How's it going in those MODULAR LOVE UNITS??",
 "How's the wife?  Is she at home enjoying capitalism?",
 'HUGH BEAUMONT died in 1982!!',
 "I always have fun because I'm out of my mind!!!",
 'I am a jelly donut.  I am a jelly donut.',
 "I am having FUN...  I wonder if it's NET FUN or GROSS FUN?",
 'I am NOT a nut....',
 'I appoint you ambassador to Fantasy Island!!!',
 'I brought my BOWLING BALL -- and some DRUGS!!',
 "I can't decide which WRONG TURN to make first!!",
 'I demand IMPUNITY!',
 "... I don't like FRANK SINATRA or his CHILDREN.",
 "I don't understand the HUMOUR of the THREE STOOGES!!",
 'I feel ... JUGULAR ...',
 'I feel better about world problems now!',
 'I feel like a wet parking meter on Darvon!',
 'I feel partially hydrogenated!',
 "I had a lease on an OEDIPUS COMPLEX back in '81 ...",
 'I had pancake makeup for brunch!',
 'I have a TINY BOWL in my HEAD',
 'I have a very good DENTAL PLAN.  Thank you.',
 'I have accepted Provolone into my life!',
 'I have many CHARTS and DIAGRAMS..',
 '... I have read the INSTRUCTIONS ...',
 '-- I have seen the FUN --',
 'I have seen these EGG EXTENDERS in my Supermarket ...',
 'I hope I bought the right relish ... zzzzzzzzz ...',
 "I hope the ``Eurythmics'' practice birth control ...",
 'I invented skydiving in 1989!',
 'I joined scientology at a garage sale!!',
 'I just forgot my whole philosophy of life!!!',
 'I just had a NOSE JOB!!',
 'I just had my entire INTESTINAL TRACT coated with TEFLON!',
 'I just remembered something about a TOAD!',
 'I Know A Joke',
 'I know how to do SPECIAL EFFECTS!!',
 "I know th'MAMBO!!  I have a TWO-TONE CHEMISTRY SET!!",
 'I left my WALLET in the BATHROOM!!',
 'I like your SNOOPY POSTER!!',
 'I own seven-eighths of all the artists in downtown Burbank!',
 'I represent a sardine!!',
 'I request a weekend in Havana with Phil Silvers!',
 '... I see TOILET SEATS ...',
 'I smell a RANCID CORN DOG!',
 'I smell like a wet reducing clinic on Columbus Day!',
 'I think I am an overnight sensation right now!!',
 'I think my career is ruined!',
 '... I want a COLOR T.V. and a VIBRATING BED!!!',
 'I want a VEGETARIAN BURRITO to go ... with EXTRA MSG!!',
 'I want a WESSON OIL lease!!',
 'I want another RE-WRITE on my CEASAR SALAD!!',
 'I want to perform cranial activities with Tuesday Weld!!',
 'I want to so HAPPY, the VEINS in my neck STAND OUT!!',
 "I was making donuts and now I'm on a bus!",
 'I wonder if BOB GUCCIONE has these problems!',
 'I wonder if I could ever get started in the credit world?',
 'I wonder if I should put myself in ESCROW!!',
 "I wonder if there's anything GOOD on tonight?",
 'I would like to urinate in an OVULAR, porcelain pool --',
 "I'd like MY data-base JULIENNED and stir-fried!",
 "I'd like some JUNK FOOD ... and then I want to be ALONE --",
 "I'll eat ANYTHING that's BRIGHT BLUE!!",
 "I'll show you MY telex number if you show me YOURS ...",
 "I'm a fuschia bowling ball somewhere in Brittany",
 "I'm also against BODY-SURFING!!",
 "I'm also pre-POURED pre-MEDITATED and pre-RAPHAELITE!!",
 "I'm ANN LANDERS!!  I can SHOPLIFT!!",
 "I'm definitely not in Omaha!",
 "I'm EMOTIONAL now because I have MERCHANDISING CLOUT!!",
 "I'm encased in the lining of a pure pork sausage!!",
 "I'm GLAD I remembered to XEROX all my UNDERSHIRTS!!",
 "I'm having a BIG BANG THEORY!!",
 "I'm having a MID-WEEK CRISIS!",
 "I'm having an emotional outburst!!",
 "I'm having fun HITCHHIKING to CINCINNATI or FAR ROCKAWAY!!",
 "I'm in direct contact with many advanced fun CONCEPTS.",
 "I'm into SOFTWARE!",
 "I'm not an Iranian!!  I voted for Dianne Feinstein!!",
 "I'm not available for comment..",
 "I'm rated PG-34!!",
 "I'm receiving a coded message from EUBIE BLAKE!!",
 "I'm shaving!!  I'M SHAVING!!",
 "I'm wearing PAMPERS!!",
 "I'm wet!  I'm wild!",
 "I've got a COUSIN who works in the GARMENT DISTRICT ...",
 "I've read SEVEN MILLION books!!",
 'if it GLISTENS, gobble it!!',
 'If our behavior is strict, we do not need fun!',
 'In Newark the laundromats are open 24 hours a day!',
 "Inside, I'm already SOBBING!",
 'Is it clean in other dimensions?',
 'Is something VIOLENT going to happen to a GARBAGE CAN?',
 'Is this an out-take from the "BRADY BUNCH"?',
 'Is this going to involve RAW human ecstasy?',
 'Is this TERMINAL fun?',
 "Isn't this my STOP?!",
 "It don't mean a THING if you ain't got that SWING!!",
 'It\'s NO USE ... I\'ve gone to "CLUB MED"!!',
 "It's OKAY -- I'm an INTELLECTUAL, too.",
 'Jesuit priests are DATING CAREER DIPLOMATS!!',
 'Jesus is my POSTMASTER GENERAL ...',
 'LBJ, LBJ, how many JOKES did you tell today??!',
 'Let me do my TRIBUTE to FISHNET STOCKINGS ...',
 "Let's send the Russians defective lifestyle accessories!",
 "Life is a POPULARITY CONTEST!  I'm REFRESHINGLY CANDID!!",
 "Loni Anderson's hair should be LEGALIZED!!",
 'Look!  A ladder!  Maybe it leads to heaven, or a sandwich!',
 'Make me look like LINDA RONSTADT again!!',
 'Maybe we could paint GOLDIE HAWN a rich PRUSSIAN BLUE --',
 'MERYL STREEP is my obstetrician!',
 'MMM-MM!!  So THIS is BIO-NEBULATION! ',
 'My EARS are GONE!!',
 'My haircut is totally traditional!',
 'MY income is ALL disposable!',
 'My LESLIE GORE record is BROKEN ...',
 'My life is a patio of fun!',
 'My mind is a potato field ...',
 'My mind is making ashtrays in Dayton ...',
 'My nose feels like a bad Ronald Reagan movie ...',
 'my NOSE is NUMB!',
 'My vaseline is RUNNING...',
 'NANCY!!  Why is everything RED?!',
 'NEWARK has been REZONED!!  DES MOINES has been REZONED!!',
 'Nipples, dimples, knuckles, NICKLES, wrinkles, pimples!!',
 'Now I am depressed ...',
 'Now I understand the meaning of "THE MOD SQUAD"!',
 'Now that I have my "APPLE", I comprehend COST ACCOUNTING!!',
 '... Now, it\'s time to "HAVE A NAGEELA"!!',
 "Now, let's SEND OUT for QUICHE!!",
 'Oh my GOD -- the SUN just fell into YANKEE STADIUM!!',
 'Oh, I get it!!  "The BEACH goes on", huh, SONNY??',
 'One FISHWICH coming up!!',
 'over in west Philadelphia a puppy is vomiting ...',
 'PARDON me, am I speaking ENGLISH?',
 'PIZZA!!',
 'Please come home with me ... I have Tylenol!!',
 'Psychoanalysis??  I thought this was a nude rap session!!!',
 'PUNK ROCK!!  DISCO DUCK!!  BIRTH CONTROL!!',
 'Quick, sing me the BUDAPEST NATIONAL ANTHEM!!',
 'RELATIVES!!',
 'RHAPSODY in Glue!',
 'Should I do my BOBBIE VINTON medley?',
 'Sign my PETITION.',
 'So this is what it feels like to be potato salad',
 'TAILFINS!! ... click ...',
 "Th' MIND is the Pizza Palace of th' SOUL",
 "Thank god!! ... It's HENNY YOUNGMAN!!",
 'The Korean War must have been fun.',
 '... the MYSTERIANS are in here with my CORDUROY SOAP DISH!!',
 "There's enough money here to buy 5000 cans of Noodle-Roni!",
 'These PRESERVES should be FORCE-FED to PENTAGON OFFICIALS!!',
 "This is a NO-FRILLS flight -- hold th' CANADIAN BACON!!",
 "... this must be what it's like to be a COLLEGE GRADUATE!!",
 'This PIZZA symbolizes my COMPLETE EMOTIONAL RECOVERY!!',
 'This PORCUPINE knows his ZIPCODE ... And he has "VISA"!!',
 'TONY RANDALL!  Is YOUR life a PATIO of FUN??',
 'Uh-oh!!  I forgot to submit to COMPULSORY URINALYSIS!',
 "Uh-oh!!  I'm having TOO MUCH FUN!!",
 "UH-OH!!  We're out of AUTOMOBILE PARTS and RUBBER GOODS!",
 'Used staples are good with SOY SAUCE!',
 'VICARIOUSLY experience some reason to LIVE!!',
 "Was my SOY LOAF left out in th'RAIN?  It tastes REAL GOOD!!",
 'We have DIFFERENT amounts of HAIR --',
 'We just joined the civil hair patrol!',
 'Were these parsnips CORRECTLY MARINATED in TACO SAUCE?',
 'What GOOD is a CARDBOARD suitcase ANYWAY?',
 'What I need is a MATURE RELATIONSHIP with a FLOPPY DISK ...',
 'What PROGRAM are they watching?',
 'What UNIVERSE is this, please??',
 "What's the MATTER Sid? ... Is your BEVERAGE unsatisfactory?",
 "When this load is DONE I think I'll wash it AGAIN ...",
 "Where do your SOCKS go when you lose them in th' WASHER?",
 'Where does it go when you flush?',
 "Where's SANDY DUNCAN?",
 "Where's th' DAFFY DUCK EXHIBIT??",
 "Where's the Coke machine?  Tell me a joke!!",
 'WHO sees a BEACH BUNNY sobbing on a SHAG RUG?!',
 'Why are these athletic shoe salesmen following me??',
 'Why is everything made of Lycra Spandex?',
 'Will it improve my CASH FLOW?',
 'Will the third world war keep "Bosom Buddies" off the air?',
 "With YOU, I can be MYSELF ...  We don't NEED Dan Rather ...",
 'World War III?  No thanks!',
 "Wow!  Look!!  A stray meatball!!  Let's interview it!",
 'Xerox your lunch and file it under "sex offenders"!',
 "You can't hurt me!!  I have an ASSUMABLE MORTGAGE!!",
 "You mean you don't want to watch WRESTLING from ATLANTA?",
 "YOU PICKED KARL MALDEN'S NOSE!!",
 "You were s'posed to laugh!",
 'Yow!',
 'Yow!  Am I having fun yet?',
 'Yow!  Am I in Milwaukee?',
 'Yow!  Are we laid back yet?',
 'Yow!  Are we wet yet?',
 'Yow!  Are you the self-frying president?',
 'Yow!  I just went below the poverty line!',
 'Yow!  I threw up on my window!',
 'Yow!  I want my nose in lights!',
 'Yow!  I want to mail a bronzed artichoke to Nicaragua!',
 "Yow!  I'm imagining a surfer van filled with soy sauce!",
 'Yow!  Is my fallout shelter termite proof?',
 'Yow!  Is this sexual intercourse yet??  Is it, huh, is it??',
 "Yow!  It's a hole all the way to downtown Burbank!",
 'Yow!  Now we can become alcoholics!',
 "Yow!  We're going to a new disco!",
 'YOW!!  Everybody out of the GENETIC POOL!',
 "YOW!!  I'm in a very clever and adorable INSANE ASYLUM!!",
 'YOW!!  The land of the rising SONY!!',
 "YOW!!  Up ahead!  It's a DONUT HUT!!",
 'YOW!!!  I am having fun!!!',
 "Zippy's brain cells are straining to bridge synapses ...",
 "Yow!! I'm trying to break Zippy!!"]

pokey_data = ['OH NO!  ITALIANS!  THEY WANT OUR ARCTIC CIRCLE-CANDY WHICH ONLY GROWS IN THE ARCTIC CIRCLE!',
 'IT IS A GOOD THING WE ESCAPED FROM THE OZONE LAYER!!!!!!!',
 'I AM CAJUN CHEF PAUL PRUDHOMME!  YOU BEST TO SAMPLE MY DELECTABLE CRAWFISH!',
 'POKEY I LOVE CRAWFISH!',
 'AND OUR CRAWFISH I MEAN OUR CRAWFISH ARE GONE!!',
 'AND THAT IS HOW POKEY AND HIS PALS DEFEATED THE                    THE END!',
 'SUPERMAN!  YOU SAVED ME!!',
 'THE ENLIGHTENED MAN FEARS DEATH NOT, FOR IN HIM DEATH HAS NO PLACE TO ENTER!',
 'THIS CITY IS NO PLACE FOR LITTLE GIRLS!!',
 'MANGIARE UNA LUMACA PICCOLA!!',
 'POKEY WHY DO WE EAT BROCCOLI?  I DO NOT LIKE BROCCOLI!',
 'NUTS TO YOU AND YOUR BROCCOLI POKEY!!',
 'ACCORDING TO THE LAW OF PRIMOGENITURE THIS MOON-CHEESE IS MINE.  THE UN?  HA!  I SPIT ON THE UN!',
 'THIS MOON-CHEESE WILL MAKE ME VERY RICH!  VERY RICH INDEED!',
 "THERE'S NOTHING QUITE LIKE AN INVIGORATING SPRING TOMATO STORM, EH!",
 'WITH A FEW SMALL MODIFICATIONS ANY CANOE CAN TRAVEL THROUGH TIME!!!',
 'OR, AS THEY SAY IN ANCIENT SCOTLAND, BON VOYAGE!!!',
 'THESE BLANKETS OPEN UP NEW WORLDS OF POSSIBILITY.  SUCH A DECISION CANNOT BE MADE LIGHTLY.  THE OCEAN HELPS ME TO THINK.',
 'HOW ABOUT SOME COTTON CANDY FOR THE CHILD',
 "DON'T WORRY, POKEY!!  SHE WAS JUST A ROBOT!",
 "POKEY IT'S A BOXING GLOVE POSSESSED BY THE DEVIL!",
 'HER NAME, MY YOUNG FRIEND, IS APPARENTLY HEADCHEESE.',
 'MAY GOD HAVE MERCY ON OUR SOULS!',
 'WHERE ARE THE ITALIANS WHEN YOU NEED THEM???',
 'SMASHING!',
 'POKEY IS STUCK IN A GRAVITY WELL!!!',
 'I DO NOT LIKE THIS GRAVITY!',
 'HOORAY!',
 'I AM LEARNING HANDSHAKES FROM AROUND THE WORLD!!!',
 'HOORAY!  I HAVE MEGA-ULTRA PLUS, FOR EASIER FUN!!!',
 "BUT GRAMPA'S DEAD!  HE DISAPPEARED 30 YEARS AGO AND THEY NEVER FOUND HIS BODY!",
 "IT'S PAYBACK TIME, GRAMPA!",
 'YOU WERE RIGHT POKEY!  GLOOMY GLORIA WAS A WITCH!',
 'I TOLD EVERYONE WE SHOULD HAVE A WITCH-HUNT BUT THEY WANTED A GOOD OLD-FASHIONED BOOK BURNING INSTEAD!',
 'SO I SAID "I\'LL SHOW YOU THE LAW OF DIMINISHING RETURNS!',
 'MR NUTTY SAID EATING RICE VERMICELLI WILL MAKE YOUR GARDEN GROW!!!',
 'OOH THAT MR NUTTY!  I WILL EDUCATE HIM',
 'GOOD DAY POKEY!  YOU ARE RIGHT!  ONLY PROPER GARDENING WILL MAKE YOUR GARDEN GROW!',
 'COVER YOUR EYES CHILD!  I WILL EXPLAIN LATER',
 'POKEY WHAT DOES IT MEAN WHEN THE LADY IS NAKED AND THE MAN IS ALSO NAKED AND THEY ARE HUGGING LIKE THAT???',
 'TEE HEE!',
 'IT WAS A TRAP YOU FOOL!!! YOU DO NOT HAVE A BROTHER!',
 'QUICK!  TO THE HYDROFOIL!',
 'THAT IS THE PRICE OF LOVE',
 "THIS ISN'T ORDINARY HAIL!  THESE ARE CALCIUM CHLORIDE NODULES!",
 'WAIT A MINUTE!  POKEYZILLA DOES NOT USE A ROCKET LAUNCHER!  YOU ARE JUST POKEY!',
 'BARBECUE CHOCOLATES!  DO YOU WANT SOME????',
 'SOUNDS TASTY POKEY BUT I WILL FINISH MY ORANGE PESTO MILKSHAKE FIRST!!!',
 'YES',
 'WHO TOLD YOU TO STOP WRITING YOUR RESEARCH PAPER???',
 'WE WERE LUCKY TO GET OUR GROCERIES BEFORE THEY ALSO CAUGHT ON FIRE!!!',
 'TRULY!',
 'YOU WERE YOUNG AND FOOLISH THEN!',
 'POKEY LEVITATION IS FUN!!!',
 'I DO NOT KNOW!  PERHAPS IT MEANS NOTHING, OR PERHAPS EVERYTHING!!!',
 'BARKEEP!  HUEVOS RANCHEROS, POR FAVOR!',
 'WHENCE I CAME, JACKANAPE!!',
 'ORANGES, APPLES, BANANAS, AND PEARS!  THESE ARE THE FRUITS THAT ARE FAVORED BY BEARS!!!  FRESH ROASTED NUTS AND BAKED ALBACORE!  GIVE A BEAR SOME AND HE WILL WANT MORE!!!',
 'WE WISH TO STUDY PLACEMAT DESIGN UNDER MR NUTTY!!!',
 'SILENCE LITTLE GIRL!  MR NUTTY DOES NOT TEACH BASIC INTERMEDIATE OR ADVANCED CLASS!',
 'AND THEN THEY SAID "NO ONE LEAVES THIS COMPOUND ALIVE!!"',
 "TRAGIC!  HEY, WHY DON'T WE LOOK AT YOUR WORK AND I WILL GIVE YOU SOME TIPS!!",
 'POKEY LOOK!  I HAVE WON AN AWARD FOR EXCELLENCE!',
 'WHO HIT ME WITH A JAR OF MUSTARD???',
 'MY NAME IS POKEY THE PENGUIN        I LIKE TO READ BOOKS        EVERY MORNING, I PRACTICE KUNG FU!',
 'WHAT ARE YOU, SOME KIND OF MACHINE?',
 'HELLO POKEY!  HELLO SMALL CHILD!  I HAVE A CHAMOIS ON MY HEAD!',
 'HEADCHEESE YOU AND YOUR FRENCH-CANADIAN TONGUE ARE A BAD INFLUENCE!',
 'HEIRATE MICH!!  THAT MEANS I AM RELAXING IN GERMAN!!!',
 'I PUT MY PANTS ON ONE LEG AT A TIME, JUST LIKE EVERYONE ELSE!',
 'BUT POKEY YOU DO NOT WEAR PANTS!!',
 'POKEY THIS IS OUR BEST TRIP EVER!!  NOTHING CAN GO WRONG!',
 'ONE TURPENTINE FOR THE MAN, COMING RIGHT UP!',
 'POKEY I AM PLAYING HARD-TO-LISTEN-TO SO ALL THE BOYS WILL WANT TO GO OUT WITH ME!!!',
 'THESE WORDS - THEIR ASPECT WAS OBSCURE - I READ INSCRIBED ABOVE A GATEWAY AND I SAID: "MASTER, THEIR MEANING IS DIFFICULT FOR ME."',
 'SO YOU SEE, AMMONIA TRULY IS ITS OWN BEST FRIEND!!!',
 'WE ARE EATING ARCTIC CIRCLE CANDY!!  WE FOUND IT IN A JAR MARKED "FORBIDDEN CANDY"!!  IS IT TASTY POKEY!!!',
 'I AM FINE!  THIS CARPET SALESMAN BROKE MY FALL!',
 'POKEY I WANT TO BUY AN EIGHT FOOT TALL CRIME FIGHTING ROBOT!',
 'YOU CAN NOT BUY AN EIGHT FOOT TALL CRIME FIGHTING ROBOT UNLESS YOU ARE A LAW ENFORCEMENT OFFICER!!!',
 'WUGGA!',
 'I HAVE FOOD POISONING!!!  I AM NOT HAVING ADVENTURES!!!',
 'OUR FIRST ITEM ON THE AGENDA CONCERNS THE CONCEPT OF INFINITY!!  I MOVE TO DECLARE INFINITY EQUAL TO ONE THOUSAND!!!',
 'HEY HEY MR NUTTY!!  WHAT SAY YOU AND I HAVE AN INFINITY OF DRINKS???',
 'BY ITSELF, IT IS A NEUTRAL CONCEPT, MUCH LIKE INFINITY!!!  BUT IN APPLICATION, IT HAS WROUGHT GREAT HARM!!!  ALLOW ME TO DEMONSTRATE!!',
 'AND IN CONCLUSION TECHNOLOGY CHANGES THE FLAVOR OF ARCTIC CIRCLE CANDY AND MAKES MILK GO SOUR!!!',
 'I AM SORRY TO SAY THAT YOU DID NOT INVENT THE LEVER!!!  IT IS ONE OF THE SIX CLASSIC SIMPLE MACHINES!!!',
 "POKEY REGARD!!!  J'AI INVENTE LE CIRCUIT PRINCIPAL DU DRAGON!!!",
 'JE SUIS DESOLE!!  LE CIRCUIT PRINCIPAL DU DRAGON A ETE INVENTE EN CHINE ANTIQUE!!',
 '"DOG ON FIRE" IS MY FAVORITE BOARD GAME!!!',
 'MY GAME CARD SAYS "GAME IS OVER.  YOU WIN."  HOORAY!',
 'MAY I GROW 3005 PLANTS??',
 'MY LAMP WAS DIRTY AND NOW IT IS CLEAN!!!  IT IS MAGIC!!!',
 'WHERE DID YOU GET YOUR NICE FLANNEL POKEY???',
 'I FOUND IT.  LET US NEVER SPEAK OF THIS FLANNEL AGAIN!!!',
 'WHERE IS MY NEW FLANNEL???  SOMEONE HIT ME WITH A ROCK AND NOW IT IS GONE',
 'POKEY I WANT TO VISIT THE PETTING ZOO!!!',
 'POKEY I HAD FUN AT THE PETTING ZOO!!!',
 'EVERY BOWL IS ACTION-PACKED WITH MEGA-CLOT-BUSTING VITA-NUTRIENTS!!!',
 'POKEY THE INGREDIENTS ARE BREAD CRUMBS AND CAFFEINE!!!  YOU DO NOT HAVE CLOT-BUSTING MEGA-POWER!!!',
 'POKEY THEY ARE USING WOOD GLUE AS A PRESERVATIVE!!!',
 'POKEY I AM READING A BOOK CALLED LIFE IN THE ARCTIC CIRCLE!!!  I LIKE MY BOOK',
 'I AM READING A BOOK ABOUT AMORTIZATION IT IS VERY GOOD',
 'HEY HEY!!!  YOU ARE INVITED TO THE GRAND OPENING OF NUTTYLAND!!',
 'YES, FIFTY CENTS!!  JUST GIVE ME YOUR CREDIT CARD AND I WILL TAKE CARE OF EVERYTHING!!!',
 'SORRY TO SAY BUT THERE IS NO BAND!!  WE HAVE FOR YOUR ENJOYMENT A TAPE OF SOOTHING OCEAN NOISES!!!',
 'ANNOUNCEMENT!!  THE PARK IS NOW CLOSED FOR REPAIRS!!  PLEASE COME BACK NEXT YEAR!!!',
 'HELLO MY NAME IS YEKOP!!!  THAT IS THE OPPOSITE OF POKEY!!!',
 'WE ARE THE YIN AND THE YANG!!!',
 'AND I AM FROM THE ARCTIC CIRCLE!!!  THE COSMIC BALANCE IS MADE COMPLETE!!!',
 'SPARE ME THE BORAX POINDEXTER!!!  IT IS TIME TO RETURN TO THE ANTARCTIC CIRCLE!!!',
 'HEY HEY!!  I AM MR YTTUN!!!  YOU LOOK LIKE YOU COULD USE SOME SNAKE OIL!!!',
 'I AM MUCH BETTER LOOKING THAN THAT POKEY CHARACTER FROM THE OTHER UNIVERSE!!!',
 'YOUR PROJECT WAS INDEED DELICIOUS!!',
 'HELLO POKEY I HAVE A SOLIDITY METER!!!',
 'HELLO SMALL CHILD!!!  YOUR METER TELLS YOU THAT I AM SOLID!!!',
 'AND GET HIS WALLET!!  GHOST MONEY HAS A VERY HIGH EXCHANGE RATE!!',
 'POKEY WHY DO YOU DRINK MAPLE SYRUP STRAIGHT FROM THE BOTTLE???',
 'IT HAS A KICK!!!  I LOVE IT!!!  GULP!!!  I LOVE IT!!!',
 'YOU ARE NO LONGER WELCOME HERE RIP VAN POKEY!!!',
 'I HAVE FALLEN ASLEEP AND SOMEONE HAS STOLEN MY FACE!',
 'I AM A HIDEOUS MONSTER!!!',
 'POKEY YOU ARE NOT HIDEOUS!!!  THE WORD IS GHASTLY!!!',
 'A RARE AND PRECIOUS ARTIFACT!!!!',
 'I COULD TELL YOU BUT YOU WOULD NOT UNDERSTAND!!!!!!!!!!',
 'NOW WHO IS KING OF THE PODIUM???',
 'I AM A PIRATE!!  YE BE MINE FAIR LASS!!',
 'YE BE MINE SWORN ENEMY!!!',
 'POKEY I MUST WARN YOU!!!  IT IS TIME FOR A DRINK!!!',
 'POKEY WE WILL CLEAN THEIR CHRONOMETERS!!!',
 'BANG UP JOB OLD BEAN!!!',
 'I MADE YOU A BOARD WITH A NAIL IN IT!!!',
 'PAINT MY FENCE!!!',
 'FENCE PAINTING TIME!!!',
 'THIS BOX CONTAINS ENOUGH THERMITE TO DESTROY US ALL!!!!!!!!!!!!!!',
 'I AM NUTTY RAY CHARLES!!!  WHERE IS THE CANDY???',
 'WHERE IS THE CANDY AND MY PIANO???  I STILL HAVE MY HARMONICA!!!',
 'HARVEST SOME SALSA FOR MY NACHOS!!!',
 'ARE YOU THE DEVIL?????',
 'I DO NOT LIKE THE HAT!!!',
 'POKEY IT IS TIME FOR YOU TO HAND OVER YOUR WALLET!!',
 'CRUD!!!',
 'I AM MASTERING THE POSSIBILITIES!!!',
 'YES!!!!',
 'HERE WE ARE!!!  UNDER THE SEA JUST LIKE I PROMISED!!!',
 '"TAKE IT!!" SAYS POKEY!  "TAKE IT!!!"',
 'TWO BITS TO SEE THE HEAD!!!  TWO BITS!!!',
 'I WILL TELL YOU A JOKE!!!        DID YOU EVER NOTICE HOW MEN LEAVE THE REFRIDGERATOR DOOR OPEN???        THAT IS THE JOKE!!!',
 'VIOLATORS MUST BE PROSECUTED!!!',
 'THIS CONSUMER PRODUCT IS NOT INTENDED FOR USERS PRONE TO VIOLENT FITS OF RAGE!!!',
 'WE TAKE HARMFUL NATURALLY OCCURING PETROCHEMICALS AND CONVERT THEM INTO USEFUL INDUSTRIAL LUBRICANTS!!!',
 'THE ONLY BYPRODUCT IS A HARMLESS BLUE POLYMER WHICH GIVES THE OCEAN ITS DISTINCTIVE COLOR AND ODOR!!!!!',
 'I SHALL ENJOY THIS PIECE OF PRIMITIVE ARCTIC CIRCLE CANDY!!!',
 'OH NO!!!  ITALIANS!!!',
 'I AM POKEY THE PENGUIN!!!  I NEED THREE SERVINGS OF LOVE A DAY!!!',
 'POKEY WHY DOES LOVE LOOK LIKE GRAVY????',
 'I AM DIOGENES!!!  GIVE ME A WHISKEY!!!',
 'NO ID MEANS NO WHISKEY!!!',
 'THE GRAPPLING HOOK IS PREPARED!!!!',
 'POKEY YOU REALIZE WE CAN NEVER RETURN TO THE ARCTIC CIRCLE!!!!!',
 'WHEN WILL POKEY RETURN???  HE TOLD ME HE WAS TAKING MY GRAPPLING HOOK TO HAVE IT CLEANED AND SHARPENED!!!',
 "I MUST RETURN THE LITTLE GIRL'S GRAPPLING HOOK!!!  I MADE A PROMISE!!!",
 'LET US ENJOY THE SCONES WHICH WE HAVE LIBERATED!!!!!',
 'VIVA FREEDOM!!  WE WILL DIVIDE THE GEAR EQUALLY!!!',
 'DEAR NUTTY I AM AFRAID YOU WERE GIVEN DISINFORMATION!!!!',
 'HELLO LITTLE GIRL!!!  MY JETPACK IS READY FOR ACTION!!!!',
 'SLACK-JAWED NINNY!!!',
 "LET'S HAVE A DRINK!!!!",
 'AFTER YEARS OF LABOR OUR GIANT FOAM NOVELTY CAN OF SODA IS DONE!!',
 'I HAVE CREATED A REPLICA OF YOU, SUPERIOR IN EVERY WAY TO THE ORIGINAL POKEY!!!',
 'ROBOT POKEY FULFILL YOUR TASK!!!!',
 "ROBOT POKEY LET'S BE FRIENDS!!!",
 'ALL THAT REMAINS IS HIS MAGICAL HAT!!!        HOORAY!!!',
 'I AM POKEY THE PENGUIN!!!',
 'THE WORLD IS IN DANGER!!!  I HAVE RETURNED TO FIND AN APPRENTICE!!!',
 'I LOVE YOUR CAPE!!!!!',
 'IF YOU JOIN ME SIR POKEY YOUR LIFE WILL BE FRAUGHT WITH STRIFE AND RISK!!!!',
 'SHALL WE DINE AT YOUR PALACE OF MY SORCERY-HUT???',
 'LET US DINE TOGETHER GOOD WIZARD!!!!',
 'I AM HAPPY THAT WE DISCOVERED THE MOUNTAIN OF FUN!!!',
 'POKEY I LOVE THE MOUNTAIN OF FUN!!!',
 'LET US DELIGHT IN THE FINAL GIFT OF THE MOUNTAIN!!!       THIS WACKY STRING!!!!',
 'POKEY THE LADY WHO RUNS THE GLASSWARE SHOP HAS LEFT TO PURCHASE LUNCH SO I AM SHOOTING AT HER PRODUCTS!!!',
 'I GOT RINGS!!!',
 'DO YOU WANT SOME PARMESAN CHEESE TOO???  HA HA!!',
 'I HAVE AN EXTRA SANDWICH AND YOU MAY HAVE IT!!!  BUT ONLY IF YOU PROMISE NOT TO WEAR IT, TOO!!!',
 'I WILL FIX THEIR WAGONS',
 'POKEY THE SHOW IS OVER!!  COME OUT WITH YOUR HANDS UP!!!',
 'POKEY WE ARE SHUTTING YOU DOWN!!!',
 'HA HA!!  NO, WE JUST NEED TO PICK UP A GAUGIN FOR THE OFFICE!!!',
 'SMASHING OPERATION, OLD BEAN!!!!',
 'I AM POWERED BY THE SUN!!!',
 'ITS SUBTERRANEAN HOME HAS MADE IT DELICIOUS!!!',
 'POKEY THE SECRET OF THE CAVES IS SAFE WITH ME!!!',
 "DON'T THANK ME!!!  THANK THE RAG!!!",
 'I WANT A RAG OF MY OWN!!!',
 'THIS RAG WAS A SHIRT WITH A PICTURE OF ME ON IT!!!',
 "LET'S HAVE A GLASS OF OIL!!!!",
 'NOW I AM A REAL TEXAN!!!!',
 'MY NAME IS MR NUTTY AND I AM A STUPID HEAD!!!!',
 'FANTASTIC SHOW POKEY!',
 'IT NEEDS WORK...',
 'SABOTAGE!  THE ITALIANS ARE TO BLAME!!!',
 'TIME TO SELL MY POETRY HAT!!!',
 'POKEY I LOVE DEVILED EGGS',
 'I AM STARRING IN A TELEVISION PROGRAM ABOUT A DETECTIVE WITH A BROKEN ARM!!!  IT IS CALLED "SLING"!!',
 'SLING!',
 'THE SPACE JELLYFISH DRIFTED AWAY!!!       BACK TO MY WHISKEY!!!',
 'I AM KING OF THE MOTORCYCLE!!!',
 "BLACKJACK - THE GENTLEMAN'S GAME!!",
 'I LOVE MY LIFE SIZE TALKING CARDBOARD CUT OUT!!!!',
 'I AM POKEY HOOD!!',
 'LOOK!!  RENOWNED COSMOLOGIST STEPHEN HAWKING!  GET HIM',
 'HELLO.. STEPHEN HAWKING',
 'TIME FOR A CUP OF BREAKFAST SLURRY!',
 'MY SLURRY HAS CANDY IN IT!',
 'POKEY ALWAYS WEAR YOUR SEAT BELT!!!!!!!!!!!',
 "DON'T WORRY, LITTLE GIRL!!  HIS SEATBELT WILL SAVE HIM!",
 'POKEY DO YOU LIKE THE FLAVOR OF THE WAFFLES??  I ADDED EXTRA FERTILIZER FOR TASTE!!!',
 'EXCELLENT',
 'I SUFFER FROM ACUTE BOOGIEMANIA!!!',
 'I MUST BOOGIE!!!!!',
 "I'M AFRAID THERE'S NOTHING WE CAN DO FOR HIM...        EXCEPT BOOGIE!!",
 'YES!  ACUTE BOOGIEMANIA IS HIGHLY CONTAGIOUS!',
 'LOOK!  PRIMITIVE ARTIC CIRCLE LIFE FORMS!        AND THEY HAVE MASTERED TIME TRAVEL!',
 "LET'S VISIT A FUTURE TAVERN!!",
 'SO HE SAYS TO THE BARTENDER "WHAT DO YOU THINK I HAVE DOWN HERE, A DUCK?"',
 'POKEY I LOVE THE FUTURE!!!!',
 'SMEAT WILL DO THAT TO YOU',
 'EUREKA!        THAT MEANS "HOORAY!"',
 'YRHRSSR!!',
 'ZTKKRZKZ',
 'I HAVE A NEW BOOK        IT IS AN OBSESSIVE COMPULSIVE CHOOSE-YOUR-ADVENTURE BOOK!',
 'IT SAYS "YOU ARE IN A BATHROOM.  TO WASH YOUR HANDS, TURN TO PAGE 2."',
 'TO WASH YOUR HANDS AGAIN, REREAD PAGE 2.        I MUST GET THEM CLEAN!',
 'TO CHECK IF YOUR CAR IS LOCKED, TURN TO PAGE 5.        BUT MY HANDS ARE NOT CLEAN!!!',
 'YOU ARE HAVING AN ANXIETY ATTACK.  COUNT TO TEN AND READ THIS PAGE AGAIN.',
 'I HATE MY LIFE!',
 'PORN',
 'I HAVE MANY SECRETS!!',
 'POKEY I DID NOT KNOW YOU WERE SO BOUYANT!!!',
 'WELCOME TO RUM ISLAND!!',
 'HERE ON RUM ISLAND WE DO NOT BELIEVE IN RUM!',
 'NOT ON RUM ISLAND!!        TEE HEE',
 'CHECKMATE, OLD BEAN!',
 'I SET MY WHIMSY RAY TO STUN!',
 'LA LA LA!!',
 "IT'S A RUM THING, POKEY...  THE SMOKE DETECTORS SAID THE CONSERVATORY WAS ON FIRE!        AND THEN I FIND YOU HERE!!",
 'EH, POKEY, IS THAT A MOLOTOV COCKTAIL IN YOUR HANDS?',
 'YES!  TO WASH DOWN MY STEAKS!  AH, REFRESHING GASOLINE!  THAT HITS THE SPOT.',
 'I AM EDWARD THE CONFESSOR!!',
 'I HATE WHALE BUSINESS!!!!',
 'THE CUTTHROAT BUSINESS OF WHALE MERCHANDISE IS NOT FOR THE WEAK!  HA HA!',
 'HOORAY FOR FRIENDSHIP',
 'I MADE POPCORN        NONE OF THE KERNELS POPPED BUT WE CAN STILL ENJOY IT',
 'MAY WE VISIT THE PARISIAN DESERT!!',
 "SPARE A QUARTER, S'IL VOUS PLAIT?",
 'DIRTY FRENCHMAN!',
 'POKEY THE PENGUIN, YOU TRULY ARE THE KING OF KINGS!',
 "THEIR VACANT STARES!!  I CAN'T TAKE IT ANYMORE!        AHH!!!",
 "THAT'S JUST THE LIQUOR TALKING!",
 'DO NOT WORRY LITTLE GIRL!  I TOOK OUR MONEY OUT OF THE BANK IN CASE THIS WOULD HAPPEN!',
 'POKEY THAT IS AN EMPTY SARDINE CAN!!!',
 'I LOVE CARD TRICKS!!!!',
 'MY MISTAKE!  IT WAS THE SIX OF HEARTS!',
 'MAMA MIA!!  A CLIFF!',
 'GRR!!  ITALIANS!',
 'YOUR CHINESE WEAPONS ARE INFERIOR!!!',
 'HOORAY!  I HAVE STRUCK HOT PANTS!',
 'NOTHING RIDES YOU LIKE A GOOD PAID OF HOT PANTS!',
 'HEY LADIES!!!!  THE PANTS HAVE A MIND OF THEIR OWN!!!',
 'MUST... FIGHT... HOT PANTS...',
 'SO... CONSTRICTIVE...',
 'CANNOT... RESIST... PANTS',
 'I AM POKEY THE PENGUIN!!!  I OWN A STEEL FACTORY!!!        I MAKE HATS!!!!',
 'GREASE IS A TRIPARTITE ASSEMBLAGE OF BUSINESS PRINCIPLES FOR SUCCESS',
 'TELL ME MORE ABOUT GREASE!',
 'GENERATE REVENUE!  EMBEZZLE ASSETS!  SUDDEN EXIT!  GREASE!',
 'WILL I WORK HARD?',
 "THAT'S THE POWER OF GREASE, LITTLE GIRL!!  YOU DON'T WORK FOR GREASE!  GREASE WORKS FOR YOU!!!",
 'YOU ALREADY HAVE, LITTLE GIRL!!',
 'BRILLIANT JOB, CHUM!!!!!',
 'HOORAY FOR MR NUTTY!!',
 'I AM A RAP MUSICIAN!!  I AM RAPPING ABOUT WORLD HISTORY!!!',
 'POKEY YOU ARE A TRUE FRIEND',
 'SKEPTOPOTAMUS I LOVE YOUR RAP MUSIC!!!',
 'YAH!!!',
 "I AM POKEY THE PENGUIN LET'S PLAY A GAME!",
 'POKEY THE FRUIT MAKE PIES!!!',
 "LET'S BOOGIE",
 'VISIT AGAIN!!  WE WILL MISS YOUR WACKY, ROTUND ANTICS!!',
 'POKEY I CAN JUMP VERY HIGH ON THE MOON!!!',
 'THE MOON IS MADE OF SPRINGS!!!',
 'WHEE',
 "LET'S EAT FISH",
 'POKEY I LOVE YOU TOO!!!',
 'TIME FOR FUN',
 'SKEPTOPOTAMUS MAY I USE YOUR COMFORT TUBE?????',
 "LET'S DRINK SPIRITS!!",
 'HELLO MR NUTTY I AM A SUGAR PLUM FAIRY!!!',
 'WHEN DO WE GIVE TOYS TO ALL THE CHILDREN',
 'MR NUTTY WHAT ARE YOU DOING BEHIND THAT DOORFRAME',
 'HOW ABOUT A ROUSING GAME OF "PIN THE TAIL ON THE DINOSAUR"!!!',
 'I AM VICTORIOUS!',
 'THE END']

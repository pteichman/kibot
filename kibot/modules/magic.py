import random
import socket
import time
import string
import re
import kibot.BaseModule
import magicdata
import TextFilter
import time
from AccessTree import AccessTree
from kibot.irclib import nm_to_n
from kibot.logger import Logger

# format switches: (see also formats.txt)
# B = bot's nick
# n = random name from channel
# N = name of user addressing the bot
# i = random integer
# d = random date
# D = today's date
# w = random word
# H = current host

def get_format_switches():
    return {"botnick" : 'B',
            "randomnick" : 'n',
            "speakernick" : 'N',
            "randomint" : 'i',
            "randomdate" : 'd',
            "today" : 'D',
            "randomword" : 'w',
            "bothost" : 'H'}



# a simple string normalization function
def normalize_string(str):
    return string.join(string.split(str),' ')


class magic(kibot.BaseModule.BaseModule):
    """The Magic3PiBall: 3 times pi is greater than 8."""

    _command_groups = (
        ('base',   ('q', 'say', 'choose', 'speak', 'expect')),
        ('config', ('new', 'delete', 'learn')),
        ('info',   ('example', 'contexts', 'matches', 'total', 'using',
                    'languages', 'filters', 'formats')),
        ('admin',  ('unlearn', 'delcontext', 'newfilter', 'delfilter',
                    'threshold', 'qprefix')),
        ('misc',   ('use', 'core', 'log')),
        )
    _stash_format = 'pickle'
    _stash_attrs = ['MD','load_check']
    def __init__(self, bot):
        self.bot = bot
        self.MD = None
        self.load_check = None
        self._unstash()
        if self.load_check == None:
            self._load_default_magic_data()
            self.load_check = 1
        else:
            self.log(4,"loaded magic settings from stash")
        self.settings = self.MD.status.settings
        self.bothost = socket.gethostname()
        self._build_channel_list()
        self._build_format_switch_data()
        self._set_handlers(15)

# log wrapper
#-----------------------------------------------------------------------------
    def log(self, level, msg):
        self.bot.log(level, "[MAGIC] %s: %s" % \
                     (time.strftime('%m/%d/%y %H:%M:%S ',
                                    time.localtime(time.time())),
                      msg))
        return
    
# initialization helpers
#------------------------------------------------------------------------------
    def _load_default_magic_data(self):
        self.log(4,"loading magic settings for the first time")
        self.MD = magicdata.CreateMagicData()
        return

    def _build_channel_list(self):
        self.log(6,"building channel list")        
        for channel in self.bot.ircdb.channels.keys():
            if not channel in self.MD.status.channels:
                self._add_channel(channel)
            else:
                self.log(4,"_build_channel_list: %s already linked" % (channel))
                
    def _build_format_switch_data(self):
        self.switches = get_format_switches()
        re_string = ''
        for s in self.switches.values():
            re_string += s
        self.format_switch_re = re.compile("%%(?P<switch>[%s])" % (re_string))
        return

# channel/language association utilities
#------------------------------------------------------------------------------
    def _add_channel(self, channel):
        self.log(6, "_add_channel(%s)" % (channel))
        try:
            magicdata.CreateChannelTree(self.MD, channel)
        except:
            self.log(4,"Unable to link %s channel tree" % (channel))

    def _delete_all_channels(self):
        self.log(6,"_delete_all_channels()")
        for channel in self.MD.status.channels.dir():
            try:
                self.MD.status.channels.unlink(channel)
            except:
                self.log(4,"Unable to unlink %s channel tree" % (channel))

    def _delete_channel(self, channel):
        self.log(6,"_delete_channel(%s)" % (channel))
        if channel in self.MD.status.channels:
            try:
                self.MD.status.channels.unlink(channel)
            except:
                self.log(4,"Unable to unlink %s channel tree" % (channel))
        else:
            self.log(4,"Illegal request to unlink %s channel tree (no such channel tree)" % (channel))
            
    def _get_spoken_language(self, channel):
        self.log(6,"_get_spoken_language(%s)" % (channel))
        if not channel in self.MD.status.channels:
            self.log(4,"_spoken_language(): channel %s not found, returning None" % (channel))
            self.log(4, str(self.MD.status.channels))
            return None
        spoken = self.MD.status.channels[channel]["spoken"]
        if spoken == None:
            self.log(4,"_get_spoken_language(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return spoken

    def _set_spoken_language(self, channel, language):
        self.log(6,"_set_spoken_language(%s,%s)" % (channel, language))
        try:
            self.MD.status.channels[channel]["spoken"] = language
        except:
            self.log(4,"Unable to set spoken language on channel %s" % (channel))
            self.log(4, str(self.MD.status.channels))
        spoken = self.MD.status.channels[channel]["spoken"]
        if spoken == None:
            self.log(4,"_spoken_language(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return spoken

    def _get_expected_language(self, channel):
        self.log(6,"_get_expected_language(%s)" % (channel))
        if not channel in self.MD.status.channels:
            self.log(4,"_expected_language(): channel %s not found, returning None" % (channel))
            self.log(4, str(self.MD.status.channels))
            return None
        expected = self.MD.status.channels[channel]["expected"]
        if expected == None:
            self.log(4,"_get_expected_language(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return expected

    def _set_expected_language(self, channel, language):
        self.log(6,"_set_expected_language(%s,%s)" % (channel, language))
        try:
            self.MD.status.channels[channel]["expected"] = language
        except:
            self.log(4,"Unable to set expected language on channel %s" % (channel))
            self.log(4, str(self.MD.status.channels))
        expected = self.MD.status.channels[channel]["expected"]
        if expected == None:
            self.log(4,"_set_expected_language(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return expected

    def _get_text_filter(self, channel):
        self.log(6,"_get_text_filter(%s)" % (channel))
        if not channel in self.MD.status.channels:
            self.log(4,"_get_text_filter(): channel %s not found, returning None" % (channel))
            self.log(4, str(self.MD.status.channels))
            return None
        obj = self.MD.status.channels[channel]["text_filter"]
        if obj == None:
            self.log(4,"_get_text_filter(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return obj

    def _set_text_filter(self, channel, filterobj):
        self.log(6,"_set_text_filter(%s,%s)" % (channel, filterobj))
        try:
            self.MD.status.channels[channel]["text_filter"] = filterobj
        except:
            self.log(4,"Unable to set text filter object on channel %s" % (channel))
            self.log(4, str(self.MD.status.channels))
        obj = self.MD.status.channels[channel]["text_filter"]
        if obj == None:
            self.log(4,"_set_text_filter(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return obj

    def _get_text_filter_name(self, channel):
        self.log(6,"_get_text_filter_name(%s)" % (channel))
        if not channel in self.MD.status.channels:
            self.log(4,"_text_filter_name(): channel %s not found, returning None" % (channel))
            self.log(4, str(self.MD.status.channels))
            return None
        name = self.MD.status.channels[channel]["text_filter_name"]
        if name == None:
            self.log(4,"_get_text_filter_name(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return name

    def _set_text_filter_name(self, channel, filtername):
        self.log(6,"_set_text_filter_name(%s,%s)" % (channel, filtername))
        try:
            self.MD.status.channels[channel]["text_filter_name"] = filtername
        except:
            self.log(4,"Unable to set text filter (%s) on channel %s" % (filtername, channel))
            self.log(4, str(self.MD.status.channels))
        name = self.MD.status.channels[channel]["text_filter_name"]
        if name == None:
            self.log(4,"_set_text_filter_name(): return value is None!")
            self.log(4, str(self.MD.status.channels))
        return name

# bot event handlers
#------------------------------------------------------------------------------
    def _on_join(self, c, e):
        channel = e.target
        nick = nm_to_n(e.source)
        if nick == self.bot.nick:
            self.log(6,"_on_join(...)")
            if not channel in self.MD.status.channels:
                self._add_channel(channel)
            else:
                self.log(4,"_on_join(): %s channel tree already exists" % (channel))
                self.log(4, str(self.MD.status.channels))
                
    def _on_part(self, c, e):
        channel = e.target
        nick = nm_to_n(e.source)
        if nick == self.bot.nick:
            self.log(6,"_on_part(...)")
            self._delete_channel(channel)
            
    def _on_pubmsg(self, c, e):
        args = string.split(e.args[0])
        if args[0] == "%s:" % (self.bot.nick):
            return
        channel = e.target
        speaker = nm_to_n(e.source)
        if (args[0] == self.settings["qprefix"]):
            self.log(6,"_on_pubmsg(...): analyzing %s's question" % (speaker))
            question = string.join(args[1:])
            self._handle_question(c, channel, speaker, question)
        elif random.random() > self.settings["global_match_threshold"]:
            self.log(6,"_on_pubmsg(...): analyzing %s's message" % (speaker))
            self._handle_match(c, channel, speaker, e.args[0])
        return

    def _on_permission_denied(self, c, e):
        if not e.raw.channel == None:
            channel = e.raw.channel
            speaker = nm_to_n(e.source)
            language = self._get_spoken_language(channel)
            if language == None or not language in self.MD.languages:
                self.log(4,"_on_permission_denied(): bad spoken language %s -- aborting" % (language))
                return
            context = \
                    self.MD.languages[language].answers.special.permission_denied
            if len(context) > 0:
                answer = self._format_text(channel, speaker, random.choice(context.dir()))
                c.privmsg(channel, answer)
            else:
                c.privmsg(current, "No can do.")
        else:
            e.raw.reply("[Magic3PiBall] Address me on the channel.")
        return "NO MORE"
    
    def _on_command_not_found(self, c, e):
        if not e.raw.channel == None:
            channel = e.raw.channel
            speaker = nm_to_n(e.source)
            question = e.raw.cmd + " " + e.raw.args
            self._handle_question(c, channel, speaker, question)
        else:
            e.raw.reply("[Magic3PiBall] Address me on the channel.")
        return "NO MORE"

# lowlevel handler utilities
#------------------------------------------------------------------------------
    def _handle_question(self, c, channel, speaker, question):
        response = self._get_question_response(channel, speaker, question)
        for line in response:
            c.privmsg(channel, line)
        return 

    def _handle_match(self, c, channel, speaker, phrase):
        response = self._get_match_response(channel, speaker, phrase)
        if not response == None:
            for line in response:
                c.privmsg(channel, line)
        return
    
# text formatting 
#------------------------------------------------------------------------------
    def _format_text(self, channel, speaker, text):
        spoken = self._get_spoken_language(channel)
        rwords = self.MD.languages[spoken].answers.special.random_words.dir()
        try:
            users = self.bot.ircdb.channels[channel].users()
            users.remove(self.bot.nick)
        except:
            self.log(4,"_format_text(): self.bot.ircdb.channels[%s].users() failed." % (channel))
        m = self.format_switch_re.findall(text)
        if len(users) == 0:
            users = ["(nobody)"]
        if len(rwords) == 0:
            rwords = ["(QUACK!)"]
        for i in range(m.count(self.switches["randomword"])):
            text = re.sub("%%%s" % (self.switches["randomword"]),\
                          random.choice(rwords),text,1)
        for i in range(m.count(self.switches["randomnick"])):
            text = re.sub("%%%s" % (self.switches["randomnick"]),\
                         random.choice(users),text,1)
        for i in range(m.count(self.switches["randomdate"])):
            t = pow(2,30)*random.random()+time.time()/4.0
            text = re.sub("%%%s" % (self.switches["randomdate"]),\
                          time.ctime(t),text,1)
        for i in range(m.count(self.switches["randomint"])):
            text = re.sub("%%%s" % (self.switches["randomint"]),\
                          "%d" % (random.randint(0,256)),text,1)
        text = re.sub("%%%s" % (self.switches["botnick"]), self.bot.nick, text)
        text = re.sub("%%%s" % (self.switches["today"]), time.ctime(), text)
        text = re.sub("%%%s" % (self.switches["speakernick"]), speaker, text)
        text = re.sub("%%%s" % (self.switches["bothost"]), self.bothost, text)
        return text

    def _build_reply(self, channel, speaker, string):
        reply = self._format_text(channel, speaker, string)
        if reply[0] == '#':
            return [reply[1:]]
        return self._get_text_filter(channel).Translate([reply])

# detailed question handling utilities
#------------------------------------------------------------------------------
    def _get_question_context(self, channel, speaker, question):
        if not question[-1] == '?':
            return "bad_question"
        expected = self._get_expected_language(channel)
        question = string.lower(question)
        question = normalize_string(question)
        questiontree = self.MD.languages[expected].questions
        for context in questiontree.phrases.dir():
            for phrase in questiontree.phrases[context].dir():
                if question[0:len(phrase)] == phrase:
                    return context
        for context in questiontree.words.dir():
            for word in questiontree.words[context].dir():
                if question[0:len(word)] == word:
                    return context
        return "no_context"

    def _retrieve_answer(self,channel, speaker, context):
        spoken = self._get_spoken_language(channel)
        answertree = self.MD.languages[spoken].answers
        if context == "bad_question":
            if len(answertree.special.bad_question) > 0:
                answer = random.choice(answertree.special.bad_question.dir())
            else:
                answer = "woof!"
        elif random.random() >= self.settings["global_random_threshold"]:
            if len(answertree.special.random) > 0:
                answer = random.choice(answertree.special.random.dir())
            else:
                answer = "quack!"
            context = "random"
        elif not context in answertree.generic:
            if len(answertree.special.unanswerable) > 0:
                answer = random.choice(answertree.special.unanswerable.dir())
            else:
                answer = "moo!"
            context = "unanswerable"
        else:
            if len(answertree.generic[context]):
                answer = random.choice(answertree.generic[context].dir())
            else:
                answer = "oink!"
        return (answer, context)

    def _get_question_response(self, channel, speaker, question):
        context = self._get_question_context(channel, speaker, question)
        (answer, context) = self._retrieve_answer(channel, speaker, context)
        return self._build_reply(channel, speaker, answer)

# detailed match handling utilities
#------------------------------------------------------------------------------
    def _get_match_context(self, channel, speaker, phrase):
        expected = self._get_expected_language(channel)
        matchtree = self.MD.languages[expected].matches
        for context in matchtree.dir():
            for regexp in matchtree[context].dir():
                formatted_text = self._format_text(channel, speaker, regexp)
                r = re.search(formatted_text, phrase)
                if not r == None:
                    return context
        return None

    def _retrieve_matchresponse(self, channel, speaker, context):
        spoken = self._get_spoken_language(channel)
        matchresponsetree = self.MD.languages[spoken].matchresponses
        if not context in matchresponsetree:
            return None
        if len(matchresponsetree[context]) == 0:
            return None
        else:
            return random.choice(matchresponsetree[context].dir())
    
    def _get_match_response(self, channel, speaker, phrase):
        context = self._get_match_context(channel, speaker, phrase)
        if context == None:
            return None
        response = self._retrieve_matchresponse(channel, speaker, context)
        if response == None:
            return None
        else:
            return self._build_reply(channel, speaker, response)
    
# q command
#------------------------------------------------------------------------------
    _q_cperm = 1
    def q(self, cmd):
        """Ask a question.
        q <question>
        """
        if cmd.channel == None:
            cmd.reply("[Magic3PiBall] Address me on the channel")
            return
        channel = cmd.channel
        speaker = cmd.nick
        response = self._get_question_response(channel, speaker, cmd.args)
        for line in response:
            cmd.reply(line)
        return

# learn and unlearn commands
#------------------------------------------------------------------------------
    _learn_cperm = 1
    def learn(self, cmd):
        """Add a new language.
        learn <language>"""
        args = cmd.asplit()
        if len(args) == 0:
            cmd.reply("Usage: learn <language>")
            return
        try:
            if magicdata.CreateLanguageTree(self.MD, args[0]) == 0:
                cmd.reply("I already know %s." % (args[0]))
                return
        except:
            cmd.reply("Couldn't add language.  Sorry.")
            return
        cmd.reply("I can now learn %s." % (args[0]))
        return

    _unlearn_cperm = "manager"
    def unlearn(self, cmd):
        """Remove a language.  (Manager access required.)
        unlearn <language>"""
        args = cmd.asplit()
        if len(args) == 0:
            cmd.reply('Usage: forget <language>')
            return
        if not args[0] in self.MD.languages:
            cmd.reply("I never learned %s." % (args[0]))
            return
        try:
            self.MD.languages.unlink(args[0])
        except:
            cmd.reply("Couldn't remove language.  Sorry.")
            return
        cmd.reply("I no longer know %s." % (args[0]))
        for channel in self.MD.status.channels.dir():
            if args[0] == self._get_spoken_language(channel):
                self._set_spoken_language(channel, "english")
                cmd.reply(channel,"%s unlearned.  Speaking english" % (args[0]))
            if args[0] == self._get_expected_language(channel):
                self._set_expected_language(channel, "english")
                cmd.reply(channel,"%s unlearned.  Expecting english" % (args[0]))
        return

# speak utilities
#------------------------------------------------------------------------------
    def _guess_filter(self, name):
        if name[0:len("gibber")] == "gibber":
            try:
                return TextFilter.GibberFilter(name)
            except:
                return None
        elif name in self.MD.status.shell_filters:
            try:
                name = self.MD.status.shell_filters[name]
                return TextFilter.ShellFilter(name)
            except:
                return None
        return None

    def _split_speak_argument(self, arg):
        result = string.split(arg,'+')
        if len(result) == 1:
            result.append(None)
        elif result[0] == '':
            result[0] = None
        return result

# use, expect, and speak commands
#------------------------------------------------------------------------------
    _use_cperm = 1
    def use(self, cmd):
        """Set both the expected language and the spoken language (no filter).
        use <language>
        """
        args = cmd.asplit()
        channel = cmd.channel
        speaker = cmd.nick
        if len(args) == 0:
            cmd.reply('Usage: use <language>')
            return
        language = args[0]
        if not language in self.MD.languages:
            cmd.reply("I can't use %s yet." % (language))
            return
        self._set_expected_language(channel, language)
        self._set_spoken_language(channel, language)
        if not self._get_text_filter_name(channel) == '':
            self._set_text_filter(channel, TextFilter.Filter("empty"))
            self._set_text_filter_name(channel, '')
        cmd.reply("I'm now using %s." % (language))
        return
    
    _expect_cperm = 1
    def expect(self, cmd):
        """Set the expected language.
        expect <language>"""
        args = cmd.asplit()
        channel = cmd.channel
        speaker = cmd.nick
        if len(args) == 0:
            cmd.reply('Usage: expect <language>')
            return
        language = args[0]
        if not language in self.MD.languages:
            cmd.reply("I can't understand %s yet." % (language))
            return
        self._set_expected_language(channel, language)
        cmd.reply("I now expect %s." % language)
        return

    _speak_cperm = 1
    def speak(self, cmd):
        """Set the spoken language.
        speak <language[+filter]>"""
        args = cmd.asplit()
        channel = cmd.channel
        speaker = cmd.nick
        if len(args) == 0:
            cmd.reply('Usage: speak <language[+filter]>')
            return
        (language, filtername) = self._split_speak_argument(args[0])
        if not language == None:
            if not language in self.MD.languages:
                cmd.reply("I can't speak %s yet." % (language))
                return
            self._set_spoken_language(channel, language)
            result_name = language
        else:
            result_name = self._get_spoken_language(channel)
        if not filtername == None:
            filter_obj = self._guess_filter(filtername)
            if filter_obj == None:
                cmd.reply("Bad filter name: %s (ignoring)" % filtername)
                if not self._get_text_filter_name(channel) == '':
                    result_name += "+%s" % (self._get_text_filter_name(channel))
            else:
                self._set_text_filter(channel,filter_obj)
                self._set_text_filter_name(channel, filtername)
                result_name += "+%s" % (filtername)
        else:
            self._set_text_filter(channel,TextFilter.Filter("empty"))
            self._set_text_filter_name(channel,'')
        cmd.reply("I now speak %s." % result_name)
        return

# newfilter and delfilter commands
#------------------------------------------------------------------------------
    _newfilter_cperm = "manager"
    def newfilter(self, cmd):
        """Add a new text filter.  (Manager access required.)
        newfilter <name> <fullpath>"""
        args = cmd.asplit()
        if len(args) < 2:
            cmd.reply("Usage: newfilter <name> <fullpath>")
            return
        if args[0] in self.MD.status.shell_filters:
            cmd.reply("I already have a %s filter." % (args[0]))
            return
        try:
            self.MD.status.shell_filters[args[0]] = args[1]
            cmd.reply("%s filter is now available." % (args[0]))
        except:
            cmd.reply("Ack! I couldn't add %s as a filter." % (args[0]))
        return

    _delfilter_cperm = "manager"
    def delfilter(self, cmd):
        """Delete a text filter.  (Manager access required.)
        delfilter <name>"""
        args = cmd.asplit()
        if len(args) == 0:
            cmd.reply("Usage: delfilter <name>")
            return
        if not args[0] in self.MD.status.shell_filters:
            cmd.reply("No such filter: %s." % (args[0]))
            return
        try:
            self.MD.status.shell_filters.unlink(args[0])
            cmd.reply("Filter %s removed." % (args[0]))
        except:
            cmd.reply("Couldn't delete the %s filter.  Sorry." % (args[0]))
        return

# delete context utilities
#------------------------------------------------------------------------------
    def _delete_question_context(self, language, context):
        zapped = 0
        questiontree = self.MD.languages[language].questions
        if context in questiontree.words:
            questiontree.words.unlink(context)
            zapped = 1
        if context in questiontree.phrases:
            questiontree.phrases.unlink(context)
            zapped = 1
        return zapped

    def _delete_context(self, searchtree, context):
        if context in searchtree:
            searchtree.unlink(context)
            return 1
        return 0
    
    _delete_answer_context = \
          lambda self, l, c: \
          self._delete_context(self.MD.languages[l].answers.generic, c)

    _delete_match_context = \
          lambda self, l, c: \
          self._delete_context(self.MD.languages[l].matches, c)

    _delete_matchresponse_context = \
          lambda self, l, c: \
          self._delete_context(self.MD.languages[l].matchresponses, c)
    
# delcontext command
#------------------------------------------------------------------------------
    _delcontext_cperm = "manager"
    def delcontext(self, cmd):
        """Delete a question/answer/match/matchresponse context for a given language.  (Manager access required.)
        delcontext <language> question|answer|match|response <context>"""
        args = cmd.asplit()
        if not len(args) == 3:
            cmd.reply("Usage: delcontext <language> question|answer|match|matchresponse <context>")
            return
        language = args[0]
        category = args[1]
        context = args[2]
        special_nodes = self.MD.fixed_values.special_nodes.dir()
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language))
            return
        if context in special_nodes:
            cmd.reply("%s is a special context only." % (context));
            return
        delcontexthandlers = {'question' : self._delete_question_context,
                              'answer' : self._delete_answer_context,
                              'match' : self._delete_match_context,
                              'matchresponse' : self._delete_matchresponse_context}
        if delcontexthandlers.has_key(category):
            try:
                if delcontexthandlers[category](language, context) == 0:
                    cmd.reply("No such %s context: %s." % \
                              (category, context))
                    return
            except:
                cmd.reply("Couldn't delete %s context: %s.  Sorry." % \
                              (category, context))
                return
            cmd.reply("Okay.  Deleted %s context: %s." % \
                          (category, context))
        else:
            cmd.reply("Bad category.  See help info.")
        return
            
# new/delete utilities
#------------------------------------------------------------------------------
    def _add_question(self, language, context, args):
        questiontree = self.MD.languages[language].questions
        if len(args) > 1:
            qnode = "phrases"
            question = string.join(args,' ')
        else:
            qnode = "words"
            question = args[0] 
        if not context in questiontree[qnode].dir():
            questiontree[qnode].add(context)
        if not question in questiontree[qnode][context]:
            questiontree[qnode][context].add(question)
            return 1
        return 0

    def _add_thing(self, searchtree, context, args):
        thing = string.join(args,' ')
        if not context in searchtree:
            searchtree.add(context)
        if not thing in searchtree[context]:
            searchtree[context].add(thing)
            return 1
        return 0
    
    _add_answer = \
      lambda self, l, c, args: \
      self._add_thing(self.MD.languages[l].answers.generic, c, args)

    def _add_special(self, language, context, args):
        answertree = self.MD.languages[language].answers
        if context == "random_words":
            answer = args[0]
        else:
            answer = string.join(args,' ')
        if not answer in answertree.special[context]:
            answertree.special[context].add(answer)
            return 1
        return 0

    _add_match = \
       lambda self, l, c, args: \
       self._add_thing(self.MD.languages[l].matches, c, args)
    
    _add_matchresponse = \
       lambda self, l, c, args: \
       self._add_thing(self.MD.languages[l].matchresponses, c, args)
    
    def _delete_question(self, language, context, args):
        questiontree = self.MD.languages[language].questions
        if len(args) > 1:
            qnode = "phrases"
            question = string.join(args,' ')
        else:
            qnode = "words"
            question = args[0] 
        if not context in questiontree[qnode].dir():
            return 0
        if question in questiontree[qnode][context]:
            questiontree[qnode][context].unlink(question)
            if len(questiontree[qnode][context]) == 0:
                questiontree[qnode].unlink(context)
            return 1
        return 0

    def _delete_thing(self, searchtree, context, args):
        thing = string.join(args,' ')
        if not context in searchtree:
            return 0
        if thing in searchtree[context]:
            searchtree[context].unlink(thing)
            if len(searchtree[context]) == 0:
                searchtree.unlink(context)
            return 1
        return 0
    
    _delete_answer = \
          lambda self, l, c, args: \
          self._delete_thing(self.MD.languages[l].answers.generic, c, args)

    def _delete_special(self, language, context, args):
        answertree = self.MD.languages[language].answers
        if context == "random_words":
            answer = args[0]
        else:
            answer = string.join(args,' ')
        if answer in answertree.special[context]:
            answertree.special[context].unlink(answer)
            return 1
        return 0

    _delete_match = \
          lambda self, l, c, args: \
          self._delete_thing(self.MD.languages[l].matches, c, args)

    _delete_matchresponse = \
          lambda self, l, c, args: \
          self._delete_thing(self.MD.languages[l].matchresponses, c, args)
    
# new and delete commands
#------------------------------------------------------------------------------
    _new_cperm = 1
    def new(self, cmd):
        """Add a new question, match or response for a given language.
        new <language> question|answer|special|match|matchresponse <context> <text>"""
        args = cmd.asplit()
        if len(args) < 4:
            cmd.reply('Usage: new <language> question|answer|special|match|matchresponse <context> <text>');
            return
        language = args[0]
        category = args[1]
        context = args[2]
        special_nodes = self.MD.fixed_values.special_nodes.dir()
        if context in special_nodes and not category == "special":
            cmd.reply("%s is a special context only." % (context));
            return
        if category == "special" and not context in special_nodes:
            cmd.reply("special context must be one of %s" % (special_nodes))
            return
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language));
            return
        newhandlers = {'question' : self._add_question,
                       'answer' : self._add_answer,
                       'special' : self._add_special,
                       'match' : self._add_match,
                       'matchresponse' : self._add_matchresponse}
        if newhandlers.has_key(category):
            try:
                if newhandlers[category](language, context, args[3:]) == 0:
                    cmd.reply("Sorry, %s item previously added." % (category))
                    return
            except:
                cmd.reply("Couldn't add %s item.  Sorry." % (category))
                return
            cmd.reply("Okay.  Added %s item." % (category))
        else:
            cmd.reply("Bad category.  See help info.")
        return

    _delete_cperm = 1
    def delete(self, cmd):
        """Remove a question or response for a given language.
        delete <language> question|answer|special|match|matchresponse <context> <text>"""
        args = cmd.asplit()
        if len(args) < 4:
            cmd.reply('Usage: delete <language> question|answer|special|match|matchresponse <context> <text>')
            return
        language = args[0]
        category = args[1]
        context = args[2]
        special_nodes = self.MD.fixed_values.special_nodes.dir()
        if context in special_nodes and not category == "special":
            cmd.reply("%s is a special context only." % (context));
            return
        if category == "special" and not context in special_nodes:
            cmd.reply("special context must be one of %s" % (special_nodes))
            return
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language));
            return
        delhandlers = {'question' : self._delete_question,
                       'answer' : self._delete_answer,
                       'special' : self._delete_special,
                       'match' : self._delete_match,
                       'matchresponse' : self._delete_matchresponse}
        if delhandlers.has_key(category):
            try:
                if delhandlers[category](language, context, args[3:]) == 0:
                    cmd.reply("No such %s item found." % (category))
                    return
            except:
                cmd.reply("Couldn't delete %s item.  Sorry." % (category))
                return
            cmd.reply("Okay.  Deleted %s item." % (category))
        else:
            cmd.reply("Bad category.  See help info.")
        return

# example, contexts, and matches commands
#------------------------------------------------------------------------------
    _example_cperm = 1
    def example(self, cmd):
        """Show an example question or response for a given language.
        example <language> question|answer|special|match|matchresponse <context>"""
        args = cmd.asplit()
        if len(args) < 3:
            cmd.reply('Usage: example <language> question|answer|special|match|matchresponse <context>')
            return
        language = args[0]
        category = args[1]
        context = args[2]
        special_nodes = self.MD.fixed_values.special_nodes.dir()
        if context in special_nodes and not category == "special":
            cmd.reply("%s is a special context only." % (context));
            return
        if category == "special" and not context in special_nodes:
            cmd.reply("special context must be one of %s" % (special_nodes))
            return
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language));
            return
        resultlist = []
        if category == "question":
            questiontree = self.MD.languages[language].questions
            if context in questiontree.words:
                resultlist += questiontree.words[context].dir()
            if context in questiontree.phrases:
                resultlist += questiontree.phrases[context].dir()
        elif category == "answer":
            answertree = self.MD.languages[language].answers
            if context in answertree.generic.dir():
                resultlist += answertree.generic[context].dir()
        elif category == "special":
            answertree = self.MD.languages[language].answers
            resultlist += answertree.special[context].dir()
        elif category == "match":
            matchtree = self.MD.languages[language].matches
            if context in matchtree:
                resultlist += matchtree[context].dir()
        elif category == "matchresponse":
            matchresponsetree = self.MD.languages[language].matchresponses
            if context in matchresponsetree:
                resultlist += matchresponsetree[context].dir()
        else:
            cmd.reply("Bad category.  See help info.")
            return
        if len(resultlist) == 0:
            cmd.reply("No examples of context %s." % (context))
            return
        cmd.reply("Example: %s" % (random.choice(resultlist)))

    _contexts_cperm = 1
    def contexts(self, cmd):
        """List the known question/answer/match/matchresponse contexts in a given language.
        contexts <language> question|answer|special|match|matchresponse
        """
        args = cmd.asplit()
        if len(args) < 2:
            cmd.reply('Usage: contexts <language> question|answer|special|match|matchresponse')
            return
        language = args[0]
        category = args[1]
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language))
            return
        if category == "question":
            contexts = self.MD.languages[language].questions.words.dir()
            for c in self.MD.languages[language].questions.phrases.dir():
                if not c in contexts:
                    contexts.append(c)
        elif category == "answer":
            contexts = self.MD.languages[language].answers.generic.dir()
        elif category == "special":
            contexts = self.MD.languages[language].answers.special.dir()
        elif category == "match":
            contexts = self.MD.languages[language].matches.dir()
        elif category == "matchresponse":
            contexts = self.MD.languages[language].matchresponses.dir()
        else:
            cmd.reply("Bad category.  See help info.")
            return
        cmd.reply("Known %s %s contexts: %s" % (language, category, contexts))
        return

    _matches_cperm = 1
    def matches(self, cmd):
        """List the known match items for a given language.
        matches <language> <context>"""
        args = cmd.asplit()
        if len(args) < 2:
            cmd.reply("Usage: matches <language> <context>")
            return
        language = args[0]
        context = args[1]
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language))
            return
        if not context in self.MD.languages[language].matches:
            cmd.reply("No such match context: %s." % (context))
            return
        matches = self.MD.languages[language].matches[context].dir()
        cmd.reply("Known %s %s matches: %s" % (language, context, matches))
        return

# utilities for total command
#------------------------------------------------------------------------------
    def _total_questions(self, language, context=None):
        questiontree = self.MD.languages[language].questions
        length = 0
        if context == None:
            contexts = questiontree.words.dir()
            for c in questiontree.phrases.dir():
                if not c in contexts:
                    contexts.append(c)
            length = len(c)
        else:
            found = 0
            if context in questiontree.words:
                length += len(questiontree.words[context])
                found = 1
            if context in questiontree.phrases:
                length += len(questiontree.phrases[context])
                found = 1
            if not found == 1:
                length = -1
        return length

    def _total_thing(self, searchtree, context=None):
        if context == None:
            return len(searchtree)
        if not context in searchtree:
            return -1
        return len(searchtree[context])
    
    _total_answers = \
         lambda self, l, c=None:\
         self._total_thing(self.MD.languages[l].answers.generic, c)

    _total_special = \
         lambda self, l, c=None:\
         self._total_thing(self.MD.languages[l].answers.special, c)

    _total_matches = \
         lambda self, l, c=None:\
         self._total_thing(self.MD.languages[l].matches, c)
 
    _total_matchresponses = \
         lambda self, l, c=None:\
         self._total_thing(self.MD.languages[l].matchresponses, c)


# total command
#------------------------------------------------------------------------------
    _total_cperm = 1
    def total(self, cmd):
        """Count the number of items for a given language+category+context.
        total <language> questions|answers|special|matches|matchresponses [<context>]"""
        args = cmd.asplit()
        if len(args) < 2:
            cmd.reply("Usage: total <language> questions|answers|special|matches|matchresponses [<context>]")
            return
        language = args[0]
        category = args[1]
        if len(args) > 2:
            context = args[2]
        else:
            context = None
        special_nodes = self.MD.fixed_values.special_nodes.dir()
        if not language in self.MD.languages:
            cmd.reply("I don't know %s yet." % (language))
            return
        totalhandlers = {'questions' : self._total_questions,
                         'answers' : self._total_answers,
                         'special' : self._total_special, 
                         'matches' : self._total_matches,
                         'matchresponses' : self._total_matchresponses}
        if totalhandlers.has_key(category):
            total = totalhandlers[category](language, context)
            if total == -1:
                cmd.reply("No such %s context: %s." % (category, context))
                return
            c = 's'
            if total == 1:
                c = ''
            cmd.reply("Total: %d item%s." % (total, c))
        else:
            cmd.reply("Bad category.  See help info.")
        return
    
# threshold and qprefix commands
#------------------------------------------------------------------------------
    _threshold_cperm = "manager"
    def threshold(self, cmd):
        """Set one of the (two) global random value thresholds.  (Manager access required.)
        threshold random|match <value in [0,1]>"""
        args = cmd.asplit()
        if len(args) == 0:
            cmd.reply("random threshold set to %.2f" % (self.settings["global_random_threshold"]))
            cmd.reply("match threshold set to %.2f" % (self.settings["global_match_threshold"]))
            return
        if len(args) < 2 or not args[0] in ("random", "match"):
            cmd.reply("Usage: threshold random|match <value>")
            return
        context = "%s_threshold" % (args[0])
        self.settings[context] = float(args[1])
        cmd.reply("OK: %s threshold set to %.2f" % (args[0], float(args[1])))
        return

    _qprefix_cperm = "manager"
    def qprefix(self, cmd):
        """Set the question prefix.  (Manager access required.)
        qprefix <prefix>"""
        args = cmd.asplit()
        if len(args) == 0:
            cmd.reply("The question prefix is %s" % (self.settings["question_prefix"]))
            return
        self.settings["question_prefix"] = args[0]
        cmd.reply("OK: %s is the new question prefix." % (args[0]))
        return
    
# commands for reporting state: using, languages, filters, formats
#------------------------------------------------------------------------------
    _using_cperm = 1
    def using(self, cmd):
        """Report what languages the bot is using on which channels."""
        for channel in self.MD.status.channels.dir():
            spoken = self._get_spoken_language(channel)
            expected = self._get_expected_language(channel)
            filtername = self._get_text_filter_name(channel)
            if filtername == '':
                full_spoken_name = spoken
            else:
                full_spoken_name = "%s+%s" % (spoken, filtername)
            cmd.reply("I speak %s and expect %s on channel %s." \
                      % (full_spoken_name, expected, channel))
        return

    _languages_cperm = 1
    def languages(self, cmd):
        """Report the names of the known languages.""" 
        result = 'Known languages: '
        result += string.join(self.MD.languages.dir(),' ')
        cmd.reply(result)
        return

    _filters_cperm = 1
    def filters(self, cmd):
        """Report the names of the known text filters."""
        result = 'Available filters: gibber '
        result += string.join(self.MD.status.shell_filters.dir(),' ')
        cmd.reply(result)
        return
        
    _formats_cperm = 1
    def formats(self, cmd):
        """Describe the format switches."""
        result = ''
        for s in self.switches.keys():
            result += "%%%s=%s " % (self.switches[s], s)
        cmd.reply("Defined format switches: %s" % (result))
        return

# miscellaneous commands: say and choose
#------------------------------------------------------------------------------
    _say_cperm = 1
    def say(self, cmd):
        """Echo a message (may contain format switches).
        say <text>
        """
        if cmd.channel == None:
            cmd.reply("[Magic3PiBall] Address me on the channel.")
            return
        if len(cmd.asplit()) == 0:
            cmd.reply('Usage: say <text>')
            return
        channel = cmd.channel
        speaker = cmd.nick
        reply = self._build_reply(channel, speaker, cmd.args)
        for line in reply:
            cmd.reply(line)
        return

    _choose_cperm = 1
    def choose(self, cmd):
        """Choose a random person from the channel by default or from a list if given
        choose [<list>]"""
        if cmd.channel == None:
            cmd.reply("[Magic3PiBall] Address me on the channel.")
            return
        args = cmd.asplit()
        if len(args) == 0:
            users = self.bot.ircdb.channels[cmd.channel].users()
            users.remove(self.bot.nick)
            result = random.choice(users)
        else:
            result = random.choice(args)
        cmd.reply("%s" % (result))
        return

    _core_cperm = "manager"
    def core(self, cmd):
        """Write the entire MagicTree to log.  (Manager access requied.)
        core"""
        self.log(0,str(self.MD))
        cmd.reply("Done.")
        return
    
# unload procedure
#------------------------------------------------------------------------------
    def _unload(self):
        self.log(4,"unloading magic")
        self._del_handlers()
        self._delete_all_channels()
        self._stash()




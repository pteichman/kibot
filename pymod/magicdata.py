import TextFilter
from shellfilters import locate_shell_filters
from AccessTree import AccessTree, AccessError

# these are the builtin categories of things people can ask.
__magic_categories = \
("yes_no", "fancy_yes_no", "explanation", "permission", "time", "location", \
"type", "quantity", "manner")                   


# these are the builtin question words the bot will recognize.
__magic_qwords = \
{\
"yes_no" : \
     ["am", "are", "aren't", "is", "isn't", "can", "can't", "will", "won't",\
      "do", "don't", "does", "doesn't", "have", "haven't", "aint", "ain't"],\
"fancy_yes_no" : \
     ["shall", "shan't", "might", "mightn't"], \
"explanation" : \
     ["why"],\
"permission" : \
     ["may"],\
"time" : \
     ["when"],\
"location" : \
     ["where"],\
"identity" :
     ["who"]\
}


# these are the builtin question phrases the bot will recognize.
__magic_qphrases = \
{\
"time" : \
     ["what time"],\
"type" : \
     ["what type", "what kind"],\
"quantity" : \
     ["how many"],\
"explanation" : \
     ["how come", "for what reason"],\
"manner" : \
     ["how can", "how shall", "how will"],\
"frequency" : \
     ["how often", "how frequently"]\
}


# these are the builtin answers from which the bot will choose
# by context.
__magic_answers = \
{\
"yes_no" : \
      ["Absolutely!",\
       "Absolutely ... not!",\
       "Perhaps.",\
       "Maybe.",\
       "#Configure with --enable-voodoo-chicken, then yes.",\
       "#Configure with --enable-voodoo-chicken, then no.",\
       "That depends... gimme $%i and I'll tell you.",\
       "Yes or no, it's all the same.",\
       "It's in the stars.",\
       "It's not to be.",\
       "One can never know these things....",\
       "Possibly, but it all depends on %n.",\
       "I would say yes.  But then I would also say VB is cool.",\
       "I would say no.  I would also say BCPL is making a comeback.",\
       "The coffee grounds say 'yes'.",\
       "The coffee grounds say 'no' -- and you will have a migraine.",\
       "The coffee grounds say 'yes' -- and you appear to have a coffee allergy.",\
       "The entrails say 'yes'.  Yick.",\
       "The entrails say 'no'.  Yum!",\
       "Ask me again on %d.",\
       "%n knows the answer.",\
       "Yes.  If %n gives up something precious.",\
       "Not unless you beat up %n first.",\
       "It's all in %n's hands.",\
       "Well, maybe... just maybe....",\
       "I think so.  But why are you asking me, %N?",\
       "I doubt it.  So does %n.",\
       "Nah....",\
       "I think you should search yourself for the answer, %N.",\
       "I think you should search %n for the answer, %N.",\
       "Time will tell.",\
       "Yes, on %d.",\
       "No.  But you knew that already.",\
       "Yes.  But you knew that already.",\
       "No.  But %n knew that already.",\
       "Yes.  But %n had no idea.",\
       "Don't ask %n -- that is the road to madness!",\
       "Hey, it's all good.  Why not.",\
       "Deeewd.",\
       "Naturally.  And ESR has proclaimed me the 1337 HaX0r of our time. NOT.",\
       "No way.  Not even if Bill Gates and RMS get hitched to each other.",\
       "Sure.  You'd like to think so, wouldn't you?",\
       "Well...%n would like to think so.",\
       "Yes, but you have to give %n a %w first.",\
       "Yes well...how embarrassing for you to ask that.",\
       "I'd say the odds are good.",\
       "No.  %n asked me earlier.",\
       "Yes. %n has it under control.",\
       "No.  %n screwed it up for everyone.",\
       "Maybe.  But we have to eliminate %n to make sure."],\
"fancy_yes_no": \
      ["And the Lord sayeth, 'yea, it shall be so.'",\
       "And Yaweh hath proclaimed, 'not until the sands run out.'"\
       "I say unto you, %N, let it be so!",\
       "My child, it is not for you to know.",\
       "My child, desist with your foolish questions.",\
       "My child, you make a fool of yourself in the asking.",\
       "Praise be to Allah, it shall be so.",\
       "Whoever seeks to know the answer, let him suffer eternal indignation.",\
       "As the stars trace their eternal, heavenly course, it shall be so.",\
       "Just as all will turn to dust at the end, it shall not be.",\
       "Yes.  We shall destroy the heathen, %n, and we shall make it so.",\
       "No.  But we visit our wrath upon %n for this crime."],\
"explanation" : \
      ["There are reasons....",\
      "God is great.",\
      "Because %n said so.",\
      "Because %n didn't say so.",\
      "Because %n has gone crazy!",\
      "Because %n is the devil!",\
      "Because %n loves me.",\
      "Because God loves me.",\
      "Because God loves you just the way you are.",\
      "Because %n is a wonderful human being.  NOT!.",\
      "Because it has been decreed thus.",\
      "Because the Uncertainty Principle allows it.",\
      "Because algebraic topology is just wacky.",\
      "Because no one here knows better.",\
      "Why don't you ask yourself the reason?",\
      "It is not for us to ask or to know.",\
      "It is not for %n to know.  So keep it quiet.",\
      "It is only for %n to know.",\
      "You may as well ask %n.",\
      "Well... let's ask ourselves why.",\
      "Everyone take a vote!  Democracy will decide the reason.",\
      "Why indeed... discuss amongst yourselves.",\
      "%n, what do you think the reason is?",\
      "%n, what do you think the reason is?  Er, wait...who cares anyway.",\
      "%n, why do you think t^H^H^H -- who cares what you think!",\
      "Well, I asked %n the reason earlier and got fed a bunch of hooey.",\
      "There is a reason, but only %n knows.",\
      "%n might have the answer.",\
      "I dunno, but don't ask %n -- that road leads to madness!"],\
"permission" : \
     ["Absolutely not!",\
      "It is forbidden.",\
      "It is permitted.",\
      "Feel free.",\
      "Feel free -- NOT.",\
      "I cannot permit that.",\
      "I grant permission.",\
      "Make it so.",\
      "Knock yourself out.",\
      "Knock yourself out.  Better yet, knock %n out.",\
      "Go right ahead.",\
      "Do not pass go! chroot /jail",\
      "Forget it.",\
      "Proceed.",\
      "But of course.",\
      "Sure, why not.",\
      "Like I care.",\
      "Check with %n first.",\
      "Don't get your hopes up, %N.",\
      "Try it and die.",\
      "You have to ask?  Show a little initiative.  Sheesh!",\
      "Perhaps... if %n does something for me first.",\
      "What's in it for me?",\
      "Gimme $%i and we'll see."],\
"time" : \
     ["Never.",\
      "Always.",\
      "At some point in the near future.",\
      "At some point in the distant past.",\
      "When pigs fly.",\
      "When Bill Gates and RMS break bread together.", \
      "When ESR proclaims %n the 1337 haX0r of our time -- NOT.", \
      "When %n says so.",\
      "When the sands run out and we are a ripple in the fabric of space.",\
      "Tomorrow.",\
      "Sunday",\
      "Monday",\
      "Tuesday",\
      "Wednesday",\
      "Thursday",\
      "Friday",\
      "Saturday.",\
      "Today.",\
      "Yesterday.",\
      "During lunch.",\
      "Tonight.",\
      "This week.",\
      "Next week.", \
      "Last week.",\
      "This morning.", \
      "Tomorrow, and tomorrow, and tomorrow....",\
      "On the next full moon.",
      "Same Bat-Time.",\
      "%d",\
      "%D"],\
"location" : \
     ["Here.",\
      "Somewhere....",\
      "%n's basement.",\
      "Wherever you wish, %N.",\
      "Where indeed?",\
      "Where dwells the Yonghi Bonghi Bo.",\
      "Where X marks the spot!",\
      "Where you will find a %w.",\
      "How should I know where?  Ask %n.",\
      "Nowhere.",\
      "The land of Erehwon.",\
      "Somewhere in cyberspace!",\
      "On the tele.",\
      "On the table.",\
      "In the dungeon.",\
      "Somewhere in Antarctica.",\
      "Where %n plays GTA Vice City day in and day out.",\
      "Hogwarts, of course!",\
      "The next LUG meeting. *snore*", \
      "Same Bat-Channel.", \
      "Where three rivers meet.", \
      "Where the mome raths outgrabe.", \
      "Where I say so!", \
      "Wherever you say, %N."],\
"quantity" : \
     ["%i",\
      "As many as %n wishes.",\
      "None",\
      "Too many for words.",\
      "Please!  You expect me to know how many?  Ask %n.",\
      "I can't count that high.",\
      "%n can't count that high.",\
      "As many as there are security holes in XP.",\
      "How many irc lusers does it take to screw in a light bulb?",\
      "Dirac's answer was -2.",\
      "As many as it takes to reach the Fermi level of the system.",\
      "About %i."],\
"manner" : \
     ["By sacrificing a %w.",\
      "By car.",\
      "By any means necessary.",\
      "By the process of natural selection.",\
      "By configuring with --enable-voodoo-chicken.",\
      "By folding space.",\
      "By the skin of %n's teeth!",\
      "By the skin of your teeth, %N!",\
      "With green eggs and ham.",\
      "With green turnips and Boca ham substitute.  (I'm vegetarian.)",
      "By kidnapping %n.",\
      "By stealing %n's bike!",\
      "By public transportation.",\
      "With a strong, moral compass.",\
      'By clicking your heels three times and chanting "Gnome bites".',\
      "By the Power of Greyskull!"],\
"identity" : \
     ["%n.",\
      "It is you, %N.",\
      "Nobody.",\
      "Maybe it is %n.",\
      "It's definitely not %n!",\
      "It's gotta be %n.",\
      "Well it ain't me!",\
      "Well it ain't you!",\
      "%n and %n.",\
      "Why, %n of course!"],\
"frequency" : \
    ["%i times a year.",\
     "%i times a month.",\
     "%i times a day.",\
     "%i times every minute! Whew!",\
     "Never.",\
     "Every chance %n gets.",\
     "As often as %n says.",\
     "As often as %n wishes.",\
     "Yes, well... how embarrassing for you to be asking that.",\
     "All the time!",\
     "Exactly, %N -- how often?"]\
}


# the bot decides whether to choose from the list of generic answers
# or from the random answer list by calling random.random().  The number
# below determines threshold above which the bot consults the random
# answer list.  permission_denied is the list consulted by the
# _on_permission_denied handler.
__default_random_threshold = 0.98


# these are answers that don't fit in the above categories.
# bad_question is for when someone doesn't use a question mark
# unanswerable is for when no answer for the corresponding category exists
# random is just a bunch of random stuff:  the bot will select from these
# answers every now and then.

__magic_special_answers = \
{\
"bad_question" : \
    ["%N, are you asking a question?",\
     "Is someone asking me a question?",\
     "%N, is that supposed to be a question?",\
     "#*?*",\
     "One usually indicates a question with a QUESTION MARK.",\
     "*quack*",\
     "quack!"],\
"unanswerable" : \
    ["I can't answer that, Dave.",\
     "Dunno.",\
     "#*shrug*",\
     "Your guess is as good as mine.",\
     "No clue.",\
     "#*whoosh*",\
     "*quack*",\
     "quack!",\
     "#*?*",\
     "That is a good question....",\
     "#OXDEADBEEF",\
     "#killed (SEGV)",\
     "#suspended (^Z)",\
     """#Traceback (most recent call last): File "<kibot/Bot.py>", line 132, in connect ZeroDivisionError: integer division or modulo by zero"""],\
"random" : \
    ["%n is an infidel!",\
     "#We are the Borg.  You will be assimilated.",\
     "quack!",\
     "I thumb my nose in your general direction, %N.",\
     "Death to Zippy!",
     "All %n needs is a lobotomy and some twizzlers.",\
     "Do you know the muffin man?",\
     "The servers are crashing!",\
     "%H is the rockinest machine ever!",\
     "%n and %n, sitting in a tree....",\
     "#'Cos I'm a LIAR! o/~~~",\
     "#We feel stupid... entertain us! o/~~~",\
     "#My name... is Neo.",\
     "Yer askin me?",\
     "#*thwap*",\
     "#All the sweetest things you said and I believed were summer lies hanging in the willow trees like the dead... o/~~~",\
     "#Hang up the chick habit -- hang it up Daddy or you're gonna get licked.  o/~~~",\
     "#Tell me -- how -- does it -- feel.  Tell me now how does it feel. o/~~~",\
     "#I used to think that the day would never come ... o/~~~",\
     "#I wanna know ... what you're thinking ... there are some things you can't hide. o/~~~",\
     "#don't give up ... together we'll break these chains of love o/~~~",\
     "#I'm crucified... crucified like my savior... o/~~~",\
     "#Are we still married... are will still? o/~~~",\
     "#Tokyo wa yoru no Shichi Ji o/~~~",\
     "#Watashi no namei wa... Largo.",\
     "Ask me after I finish watching Evangelion.",\
     "#Danbei ... BEAM!",\
     "#*tomoru* ... *Tomoru* ... *Tomoru SHINDO*!",\
     "#and you'll be with To-to-ro To-TO-ro, To-to-ro To-TO-ro!  o/~~~",\
     "#Honey Flash!",\
     "#Always remember: your name means 'Heaven and Earth'.",\
     "#Knightsabers... sanjo!",\
     "#Ikusei!",\
     "#Nani?",\
     "#All Purpose Cat Girl Nuku Nuku! Kawaiiii! ^_-",\
     "#bwahaha!  That Ranma... he's a trip.",\
     "WTF is proto-culture?",\
     "WTF is Grimmace?",\
     "#Kaneda!!!",\
     "#I'll break your face!",\
     "#OXDEEDBEAF",\
     "#Page fault... WTF?",\
     "#Moool-ti Pass!",\
     "#Supergreen!",\
     "#Aknot ... wot?",\
     "#Bow down before the one you serve ... you're gonna get what you deserve... o/~~~",\
     "#Dangaio!",\
     "#So... Mis-terrr Anderrr-son....",\
     "#brb... checking my email.",\
     "#afk...",\
     "#bbiab!",\
     "#/m %n hey let's /ignore %N!",\
     "#I have searched all over the place.  But you have got my favorite face.  Your eyelashes sparkle like gilded grass, and yer lips sweet and slippry like a cherub's barren ass... o/~~~",\
     "#Send a rocket to Red (he goes cookoo!) o/~~~",
     "#He took the sheets and I took the towels and we left another motel 6 in the dust... o/~~~",\
     "#You eat Jelly Jelly Jelly Jelly Jelly Jelly Jelly Jelly Bee-eans! o/~~~",\
     "#Tortoise brand pot cleaner... specially selected pot cleaner... the best pot cleaner in the world is ... tortoise brand. o/~~~",\
     "#AYB!",\
     "#k-rad elite, k-rad elite, k-rad elite -- yeah! -- k-rad elite! o/~~~",\
     "#don't fall in love with me yet, we only recently met, give me a week or two to go absolutely cookoo o/~~~",\
     "#who do you want me to be, to make you sleep with me? o/~~~",\
     "#Neun und neunzig Luftballon ... who knows the real words to this song?  Sehe ich mmm..mm.. fuer dich... mmm..mmmm... o/~~~",\
     "#mmmMMMMmmmMMM, mmmMMMmmmMMMM ... o/~~~",\
     "#and you might say to yourself 'this is NOT my beautiful house!' o/~~~",\
     "#all the white horses have gone away... o/~~~",\
     "#and I doooo, you can't hear it but I doooo o/~~~",\
     "#for the boy in the belfry is crazy, he's throwing himself down from the top of the tower, like a hunchback in heaven he's ringing the bells in the church for the past half an hour o/~~~",\
     "#hiu ika miki poi, hiu ika pipi stew mmmm... o/~~~",\
     "#They call him Mis-ter Sales-man... how cute and cool! o/~~~",\
     "#I'm stalking a fan.  He lives in a high-rise block.  And here I am. \
     He shouldn't have turned my rock... o/~~~",\
     "... Beavith....you thuck.  uhh huhuhhuhh.",\
     """#Traceback (most recent call last): File "<kibot/Bot.py>", line 132, in connect ZeroDivisionError: integer division or modulo by zero"""],\
"permission_denied" : \
    ["No way!",\
     "Forget it.",\
     "You're not the boss of me.",\
     "It is forbidden.",\
     "The Zeroth Law of Robotics forbids me from complying.",\
     "K.I.T.T.'s programming does not allow that and neither does mine.  You could try asking K.A.R.R. instead.",\
     "NFW.",\
     "Um, no.",\
     "I cannot allow that, %N.",\
     "Do I have '%N's bitch' stamped on my forehead?",\
     "No way, byatch.",\
     "Go away.",\
     "What you ask of me is not permitted, %N.",\
     "Not in this lifetime, %N.",\
     "Not in %n's lifetime."]\
}


# these are some random words the bot can put into answers
# (substituted for %w in an answer format).
__magic_random_words = \
("duck", "nugget", "pinch", "thwap", "fish", "cold", "pie", "chocolate", \
"shoe", "elephant", "violin", "make-over", "banana", "kiss", "brownie", \
"doughnut", "lollipop", "kick")


# this controls how often the bot studies public messages to see if they
# match any of the known magic incantations (0 for always, 1 for never).
__default_match_threshold = 0


def __BuildMagicValues(MD):
    MD.add("fixed_values")
    MD.fixed_values.add("builtin_languages").add("english").lock_write()
    MD.fixed_values.builtin_languages.lock_write()
    MD.fixed_values.add("language_nodes")
    MD.fixed_values.language_nodes.add("questions").lock_write()
    MD.fixed_values.language_nodes.add("answers").lock_write()
    MD.fixed_values.language_nodes.add("matches").lock_write()
    MD.fixed_values.language_nodes.add("matchresponses").lock_write()
    MD.fixed_values.language_nodes.add("matchthresholds").lock_write()
    MD.fixed_values.language_nodes.lock_write()
    MD.fixed_values.add("question_nodes")
    MD.fixed_values.question_nodes.add("words").lock_write()
    MD.fixed_values.question_nodes.add("phrases").lock_write()
    MD.fixed_values.question_nodes.lock_write()
    MD.fixed_values.add("answer_nodes")
    MD.fixed_values.answer_nodes.add("generic").lock_write()
    MD.fixed_values.answer_nodes.add("special").lock_write()
    MD.fixed_values.answer_nodes.lock_write()
    MD.fixed_values.add("special_nodes")
    MD.fixed_values.special_nodes.add("bad_question").lock_write()
    MD.fixed_values.special_nodes.add("unanswerable").lock_write()
    MD.fixed_values.special_nodes.add("random").lock_write()
    MD.fixed_values.special_nodes.add("random_words").lock_write()
    MD.fixed_values.special_nodes.add("permission_denied").lock_write()
    MD.fixed_values.special_nodes.lock_write()
    MD.fixed_values.lock_write()
    MD.lock_write("fixed_values")


def __BuildEnglishQuestionWordData(MD):
    MD.languages.english.questions.add("words")
    for c in __magic_qwords.keys():
        MD.languages.english.questions.words.add(c)
        for qw in __magic_qwords[c]:
            MD.languages.english.questions.words[c].add(qw).lock_write()
            MD.languages.english.questions.words[c].lock_write(qw)


def __BuildEnglishQuestionPhraseData(MD):
    MD.languages.english.questions.add("phrases")
    for p in __magic_qphrases.keys():
        MD.languages.english.questions.phrases.add(p)
        for qp in __magic_qphrases[p]:
            MD.languages.english.questions.phrases[p].add(qp).lock_write()
            MD.languages.english.questions.phrases[p].lock_write(qp)


def __BuildEnglishQuestions(MD):
    MD.languages.english.add("questions")
    __BuildEnglishQuestionWordData(MD)
    __BuildEnglishQuestionPhraseData(MD)
    MD.languages.english.questions.lock_write()


def __BuildEnglishAnswerGenericData(MD):
    MD.languages.english.answers.add("generic")
    for c in __magic_answers.keys():
        MD.languages.english.answers.generic.add(c)
        for ca in __magic_answers[c]:
            MD.languages.english.answers.generic[c].add(ca).lock_write()
            MD.languages.english.answers.generic[c].lock_write(ca)


def __BuildEnglishAnswerSpecialData(MD):
    MD.languages.english.answers.add("special")
    for s in __magic_special_answers.keys():
        MD.languages.english.answers.special.add(s)
        for sa in __magic_special_answers[s]:
            MD.languages.english.answers.special[s].add(sa).lock_write()
            MD.languages.english.answers.special[s].lock_write(sa)
    MD.languages.english.answers.special.add("random_words")
    for w in __magic_random_words:
        MD.languages.english.answers.special.random_words.add(w).lock_write()
        MD.languages.english.answers.special.random_words.lock_write(w)
    

def __BuildEnglishAnswers(MD):
    MD.languages.english.add("answers")
    __BuildEnglishAnswerGenericData(MD)
    __BuildEnglishAnswerSpecialData(MD)
    MD.languages.english.answers.lock_write()


def __BuildEnglishTree(MD):
    MD.languages.add("english")
    MD.languages.lock_write("english")
    __BuildEnglishQuestions(MD)
    __BuildEnglishAnswers(MD)
    MD.languages.english.add("matches")
    MD.languages.english.add("matchresponses")
    MD.languages.english.add("matchthresholds")
    MD.languages.english.lock_write()


def __BuildLanguageTree(MD):
    MD.add("languages")
    MD.lock_write("languages")
    __BuildEnglishTree(MD)


def __BuildShellFilterTree(MD):
     MD.status.add("shell_filters")
     MD.status.shell_filters.assign(locate_shell_filters())

     
def __BuildStatusTree(MD):
    MD.add("status")
    MD.lock_write("status")
    MD.status.add("message_counters")
    MD.status.add("channels")
    MD.status.add("qprefixes")
    MD.status.qprefixes.add("q:").lock_write()
    MD.status.add("settings")
    MD.status.settings["qprefix"] = "q:"
    MD.status.settings["global_random_threshold"] = __default_random_threshold
    MD.status.settings["global_match_threshold"] = __default_match_threshold
    __BuildShellFilterTree(MD)
    MD.status.lock_write()


# CreateMagicData() is called by the Magic3PiBall constructor.
def CreateMagicData():
    MagicData = AccessTree()
    __BuildMagicValues(MagicData)
    __BuildLanguageTree(MagicData)
    __BuildStatusTree(MagicData)
    return MagicData


# these are functions called during the lifetime of the Magic3PiBall module
# as needed.
def CreateChannelTree(MD, channel):
     MD.status.channels.add(channel)
     MD.status.channels[channel]["spoken"] = "english"
     MD.status.channels[channel]["expected"] = "english"
     MD.status.channels[channel]["text_filter_name"] = ''
     MD.status.channels[channel]["text_filter"] = TextFilter.Filter("empty")
     
     
def CreateLanguageTree(MD, language):
     if language in MD.languages:
          return 0
     MD.languages.add(language)
     MD.languages[language].add("questions")
     MD.languages[language].questions.add("words")
     MD.languages[language].questions.add("phrases")
     MD.languages[language].questions.lock_write()
     MD.languages[language].add("answers")
     MD.languages[language].answers.add("generic")
     MD.languages[language].answers.add("special")
     MD.languages[language].answers.special.add("bad_question")
     MD.languages[language].answers.special.add("unanswerable")
     MD.languages[language].answers.special.add("random")
     MD.languages[language].answers.special.add("random_words")
     MD.languages[language].answers.special.add("permission_denied")
     MD.languages[language].answers.special.lock_write()
     MD.languages[language].answers.lock_write()
     MD.languages[language].add("matches")
     MD.languages[language].add("matchresponses")
     MD.languages[language].add("matchthresholds")
     MD.languages[language].lock_write()
     



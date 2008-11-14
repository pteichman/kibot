import string

vowels = "aeiouAEIOU"
exceptions = "yY"
gibbercharacters = string.letters

def IsVowel(ch, nextch):
    """
    IsVowel(char, nextchar): uses the vowel and exception constants to figure
    out if char is a vowel.  Exceptions are simple-minded: suppose
    'y' is an exception (which it is by default), then it is a vowel if not
    followed by a vowel.  This scheme works for "yes" (not vowel),
    "yttrium" (vowel), "tiny" (vowel), etc.  It does not work for "dye",
    "shying", etc.  So sue me -- you're lucky even to have IsVowel. :-)
    """
    if ch in vowels:
        return 1
    if not nextch in vowels and (ch in exceptions):
        return 1

def IsConsonant(ch, nextch):
    """
    IsConsonant(char, nextchar): returns the "complement" of IsVowel.
    """
    return (ch in gibbercharacters) and (not IsVowel(ch,nextch))

def GibberWord(word,gibber,startc,finalc):
    """
    GibberWord(word, gibber, startconsonant, finalconsonant).
    Transform a single word (no punctuation) into gibber speak.
    If you are dealing with strings of words and punctuation or
    whitespace, call GibberString instead.
    """
    wordlen = len(word)
    if wordlen == 0:
        return ''
    copy = word + ' '
    result = ''
    i = 0
    while i < wordlen:
        while i < wordlen and IsVowel(copy[i],copy[i+1]):
            result += copy[i]
            i += 1
        if i == wordlen:
            result += startc + gibber
            break
        while i < wordlen and IsConsonant(copy[i],copy[i+1]):
            result += copy[i]
            i += 1
        result += gibber
        if i < wordlen:
            result += finalc
    return result

def GibberString(string,gibber,startc,finalc):
    """
    GibberString(string, gibber, startconsonant, finalconsonant).
    The startconsonant and finalconsonant are provided for "euphony",
    so a consonant is always between a word vowel and the initial
    gibber vowel.  This will turn a string of words into gibber speak.
    """
    stringlen = len(string)
    result = ''
    i = 0
    while i < stringlen:
        wordbuf = ''
        while i < stringlen and not string[i] in gibbercharacters:
            result += string[i]
            i += 1
        while i < stringlen and string[i] in gibbercharacters:
            wordbuf += string[i]
            i += 1
        result += GibberWord(wordbuf,gibber,startc,finalc)
    return result


